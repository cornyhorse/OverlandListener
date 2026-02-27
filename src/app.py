"""OverlandListener — receive and store GPS data from the Overland app."""

__version__ = "1.0.0"

import hashlib
import hmac
import json
import logging
import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

# ---- Logging ----
logger = logging.getLogger("overland")
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "0").strip().lower() in ("1", "true", "yes", "y", "on") else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# ---- Config ----
STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "filesystem").strip().lower()
LOG_DIR: Path = Path(os.getenv("LOG_DIR", "/data"))
TOKEN: str | None = os.getenv("INGEST_TOKEN")
AUTH_SECRET: str | None = os.getenv("AUTH_SECRET")

S3_BUCKET: str | None = os.getenv("S3_BUCKET")
S3_PREFIX: str = os.getenv("S3_PREFIX", "").strip().strip("/")
AWS_REGION: str | None = os.getenv("AWS_REGION")
AWS_ENDPOINT_URL: str | None = os.getenv("AWS_ENDPOINT_URL")
DEBUG: str = os.getenv("DEBUG", "0")
MAX_BODY_BYTES: int = int(os.getenv("MAX_BODY_BYTES", "1048576"))

# Cached S3 client — created once at startup when needed
_s3_client = None


# ---- Helpers ----
def _truthy(v: object) -> bool:
    """Return True for common truthy environment-variable values."""
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")


def _safe_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def log_config() -> None:
    """Log non-secret configuration at startup (DEBUG only)."""
    logger.debug("STORAGE_BACKEND=%s", STORAGE_BACKEND)
    if STORAGE_BACKEND == "filesystem":
        logger.debug("LOG_DIR=%s", LOG_DIR)
    else:
        logger.debug("S3_BUCKET=%s", S3_BUCKET)
        logger.debug("S3_PREFIX=%s", S3_PREFIX)
        logger.debug("AWS_REGION=%s", AWS_REGION)
        logger.debug("AWS_ENDPOINT_URL=%s", AWS_ENDPOINT_URL)
        logger.debug("AWS_ACCESS_KEY_ID=%s", "(set)" if os.getenv("AWS_ACCESS_KEY_ID") else "(unset)")
        logger.debug("AWS_SECRET_ACCESS_KEY=%s", "(set)" if os.getenv("AWS_SECRET_ACCESS_KEY") else "(unset)")


def compact_json(d: dict) -> str:
    """Serialise a dict to compact JSON (no whitespace)."""
    return json.dumps(d, separators=(",", ":"), ensure_ascii=False)


def make_name(payload: dict) -> str:
    """Generate a collision-resistant, chronologically sortable filename."""
    now_ms = int(time.time() * 1000)
    h = hashlib.sha256(compact_json(payload).encode("utf-8")).hexdigest()[:8]
    return f"{now_ms}-{h}.json"


def fs_write_request(payload: dict) -> None:
    """Atomically write a request payload to the filesystem."""
    req_dir = LOG_DIR / "requests"
    req_dir.mkdir(parents=True, exist_ok=True)
    name = make_name(payload)
    target = req_dir / name
    # Atomic write: write to temp file then rename
    fd, tmp_path = tempfile.mkstemp(dir=req_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(compact_json(payload))
        os.rename(tmp_path, target)
    except BaseException:
        # Clean up the temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    logger.info("Saved request to %s", target)


def s3_key_for(name: str) -> str:
    """Build an S3 object key from a filename."""
    base = "requests/" + name
    return f"{S3_PREFIX}/{base}" if S3_PREFIX else base


def get_s3_client():
    """Return the cached S3 client, creating it on first call."""
    global _s3_client
    if _s3_client is None:
        import boto3

        params: dict = {}
        if AWS_REGION:
            params["region_name"] = AWS_REGION
        if AWS_ENDPOINT_URL:
            params["endpoint_url"] = AWS_ENDPOINT_URL
        _s3_client = boto3.client("s3", **params)
    return _s3_client


def s3_write_request(payload: dict) -> None:
    """Write a request payload to S3."""
    client = get_s3_client()
    name = make_name(payload)
    key = s3_key_for(name)
    client.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=compact_json(payload).encode("utf-8"),
        ContentType="application/json",
    )
    logger.info("Uploaded request to s3://%s/%s", S3_BUCKET, key)


def write_request(payload: dict) -> None:
    """Route a request payload to the configured storage backend."""
    if STORAGE_BACKEND == "s3":
        if not S3_BUCKET:
            raise RuntimeError("S3_BUCKET not set")
        s3_write_request(payload)
    else:
        fs_write_request(payload)


def startup_write_check() -> None:
    """Verify write access to the configured storage backend."""
    test_content = b"ok\n"
    if STORAGE_BACKEND == "s3":
        if not S3_BUCKET:
            raise RuntimeError("S3_BUCKET not set for s3 backend")
        key = s3_key_for("healthcheck.txt")
        client = get_s3_client()
        try:
            client.put_object(Bucket=S3_BUCKET, Key=key, Body=test_content, ContentType="text/plain")
            client.delete_object(Bucket=S3_BUCKET, Key=key)
            logger.info("S3 write/delete ok at s3://%s/%s", S3_BUCKET, key)
        except Exception as e:
            logger.error("S3 write-check failed: %s", e)
            logger.error("Endpoint=%s Bucket=%s Key=%s", AWS_ENDPOINT_URL, S3_BUCKET, key)
            raise
    else:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        hc = LOG_DIR / "healthcheck.txt"
        hc.write_bytes(test_content)
        try:
            hc.unlink()
        except FileNotFoundError:
            pass
        logger.info("Filesystem write ok at %s", LOG_DIR)


# ---- FastAPI lifecycle ----
@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup / shutdown lifecycle hook."""
    if not TOKEN:
        raise RuntimeError("INGEST_TOKEN environment variable must be set")
    if _truthy(DEBUG):
        log_config()
    startup_write_check()
    yield


app = FastAPI(lifespan=lifespan)


# ---- Endpoints ----


@app.get("/health")
def health():
    """Lightweight liveness probe — always returns 200."""
    return {"status": "ok", "version": __version__}


@app.get("/debug/env")
def debug_env(request: Request):
    """Return non-secret config. Requires DEBUG=1 and a valid ingest token."""
    if not _truthy(DEBUG):
        raise HTTPException(status_code=404, detail="not found")

    # Require authentication
    req_token = (request.headers.get("x-ingest-token") or "").strip()
    if not TOKEN or not req_token or not _safe_compare(req_token, TOKEN):
        raise HTTPException(status_code=401, detail="bad token")

    return {
        "storage_backend": STORAGE_BACKEND,
        "log_dir": str(LOG_DIR),
        "s3_bucket": S3_BUCKET,
        "s3_prefix": S3_PREFIX,
        "aws_region": AWS_REGION,
        "aws_endpoint_url": AWS_ENDPOINT_URL,
        "debug": _truthy(DEBUG),
        "max_body_bytes": MAX_BODY_BYTES,
    }


@app.post("/api/input")
async def input_endpoint(request: Request):
    """Receive a location payload from the Overland app."""
    # --- Auth: token via header ---
    req_token = (request.headers.get("x-ingest-token") or "").strip()
    if not TOKEN or not req_token or not _safe_compare(req_token, TOKEN):
        raise HTTPException(status_code=401, detail="bad token")

    if AUTH_SECRET:
        auth = (request.headers.get("authorization") or "").strip()
        expected_bearer = f"Bearer {AUTH_SECRET}"
        if not auth or not _safe_compare(auth, expected_bearer):
            raise HTTPException(status_code=401, detail="bad authorization")

    # --- Body size guard ---
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > MAX_BODY_BYTES:
                raise HTTPException(status_code=413, detail="payload too large")
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid content-length")

    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="payload too large")

    # --- Parse & validate ---
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="invalid JSON")

    if not isinstance(payload, dict) or "locations" not in payload:
        raise HTTPException(status_code=400, detail="missing locations")

    # --- Persist ---
    write_request(payload)

    # Overland expects this exact response:
    return JSONResponse({"result": "ok"})
