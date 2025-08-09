import os, json, time, hashlib
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

# ---- Config ----
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "filesystem").strip().lower()  # filesystem | s3
LOG_DIR = Path(os.getenv("LOG_DIR", "/data"))
TOKEN = os.getenv("INGEST_TOKEN")  # required via ?token=
AUTH_SECRET = os.getenv("AUTH_SECRET")  # optional Authorization header

S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX", "").strip().strip("/")  # optional
AWS_REGION = os.getenv("AWS_REGION")  # optional; boto3 will also use env/role/instance profile
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")
DEBUG = os.getenv("DEBUG", "0")
DEBUG_PRINT_CREDS = os.getenv("DEBUG_PRINT_CREDS", "0")

app = FastAPI()
s3 = None


# ---- Helpers ----
def _truthy(v) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

def log_config():
    print(f"[CFG] STORAGE_BACKEND={STORAGE_BACKEND}")
    if STORAGE_BACKEND == "filesystem":
        print(f"[CFG] LOG_DIR={LOG_DIR}")
    else:
        print(f"[CFG] S3_BUCKET={S3_BUCKET}")
        print(f"[CFG] S3_PREFIX={S3_PREFIX}")
        print(f"[CFG] AWS_REGION={AWS_REGION}")
        print(f"[CFG] AWS_ENDPOINT_URL={AWS_ENDPOINT_URL}")
        ak = os.getenv("AWS_ACCESS_KEY_ID")
        sk = os.getenv("AWS_SECRET_ACCESS_KEY")
        if _truthy(DEBUG_PRINT_CREDS):
            print(f"[CFG] AWS_ACCESS_KEY_ID={ak}")
            print(f"[CFG] AWS_SECRET_ACCESS_KEY={sk}")
        else:
            if ak:
                print(f"[CFG] AWS_ACCESS_KEY_ID={ak[:4]}...{ak[-4:]} (masked)")
            else:
                print("[CFG] AWS_ACCESS_KEY_ID=(unset)")
            print("[CFG] AWS_SECRET_ACCESS_KEY=*** (masked)")
def compact_json(d: dict) -> str:
    return json.dumps(d, separators=(",", ":"), ensure_ascii=False)


def make_name(payload: dict) -> str:
    now_ms = int(time.time() * 1000)
    h = hashlib.sha256(compact_json(payload).encode("utf-8")).hexdigest()[:8]
    return f"{now_ms}-{h}.json"


def fs_write_request(payload: dict) -> None:
    req_dir = LOG_DIR / "requests"
    req_dir.mkdir(parents=True, exist_ok=True)
    name = make_name(payload)
    with (req_dir / name).open("w", encoding="utf-8") as f:
        f.write(compact_json(payload))
    print(f"[FS] Saved request to {req_dir / name}")


def s3_key_for(name: str) -> str:
    base = "requests/" + name
    return f"{S3_PREFIX}/{base}" if S3_PREFIX else base


def s3_write_request(payload: dict) -> None:
    client = get_s3_client()
    name = make_name(payload)
    key = s3_key_for(name)
    client.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=compact_json(payload).encode("utf-8"),
        ContentType="application/json",
    )
    print(f"[S3] Uploaded request to s3://{S3_BUCKET}/{key}")


def write_request(payload: dict) -> None:
    if STORAGE_BACKEND == "s3":
        if not S3_BUCKET:
            raise RuntimeError("S3_BUCKET not set")
        s3_write_request(payload)
    else:
        fs_write_request(payload)


def startup_write_check() -> None:
    test_content = b"ok\n"
    if STORAGE_BACKEND == "s3":
        if not S3_BUCKET:
            raise RuntimeError("S3_BUCKET not set for s3 backend")
        key = s3_key_for("healthcheck.txt")
        client = get_s3_client()
        try:
            client.put_object(Bucket=S3_BUCKET, Key=key, Body=test_content, ContentType="text/plain")
            # optional cleanup; comment out if you want it to stay
            client.delete_object(Bucket=S3_BUCKET, Key=key)
            print(f"[HC] S3 write/delete ok at s3://{S3_BUCKET}/{key}")
        except Exception as e:
            print(f"[HC] S3 write-check failed: {e}", flush=True)
            # Print where we tried to write
            print(f"[HC] Endpoint={AWS_ENDPOINT_URL} Bucket={S3_BUCKET} Key={key}", flush=True)
            # Print creds (masked by default; full if DEBUG_PRINT_CREDS truthy)
            ak = os.getenv("AWS_ACCESS_KEY_ID") or ""
            sk = os.getenv("AWS_SECRET_ACCESS_KEY") or ""
            def _mask(s: str) -> str:
                return f"{s[:4]}...{s[-4:]}" if s and len(s) > 8 else ("(unset)" if not s else s)
            if _truthy(DEBUG_PRINT_CREDS):
                print(f"[HC] AWS_ACCESS_KEY_ID={ak}", flush=True)
                print(f"[HC] AWS_SECRET_ACCESS_KEY={sk}", flush=True)
            else:
                print(f"[HC] AWS_ACCESS_KEY_ID={_mask(ak)}", flush=True)
                print(f"[HC] AWS_SECRET_ACCESS_KEY=*** (masked)", flush=True)
            raise
    else:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        hc = LOG_DIR / "healthcheck.txt"
        hc.write_bytes(test_content)
        try:
            hc.unlink()
        except FileNotFoundError:
            pass


def get_s3_client():
    import boto3
    params = {}
    if AWS_REGION:
        params["region_name"] = AWS_REGION
    if AWS_ENDPOINT_URL:
        params["endpoint_url"] = AWS_ENDPOINT_URL
    return boto3.client("s3", **params)


# ---- FastAPI lifecycle ----
@app.on_event("startup")
def on_startup():
    if _truthy(DEBUG):
        log_config()
    startup_write_check()


# ---- Endpoint ----

# Debug endpoint guarded by DEBUG flag
@app.get("/debug/env")
def debug_env():
    if not _truthy(DEBUG):
        raise HTTPException(status_code=404, detail="not found")
    ak = os.getenv("AWS_ACCESS_KEY_ID")
    masked_ak = f"{ak[:4]}...{ak[-4:]}" if ak else None
    return {
        "storage_backend": STORAGE_BACKEND,
        "log_dir": str(LOG_DIR),
        "s3_bucket": S3_BUCKET,
        "s3_prefix": S3_PREFIX,
        "aws_region": AWS_REGION,
        "aws_endpoint_url": AWS_ENDPOINT_URL,
        "aws_access_key_id": masked_ak,
        "debug": _truthy(DEBUG),
        "debug_print_creds": _truthy(DEBUG_PRINT_CREDS),
    }


@app.post("/api/input")
async def input_endpoint(request: Request):
    token = (request.query_params.get("token") or "").strip()
    if not TOKEN or token != TOKEN:
        raise HTTPException(status_code=401, detail="bad token")

    if AUTH_SECRET:
        auth = (request.headers.get("authorization") or "").strip()
        if auth != AUTH_SECRET and auth != f"Bearer {AUTH_SECRET}":
            raise HTTPException(status_code=401, detail="bad authorization")

    try:
        payload = await request.json()
        if not isinstance(payload, dict) or "locations" not in payload:
            raise ValueError("missing locations")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")

    # write one file per request; raise if it fails so client retries
    write_request(payload)

    # Overland wants this exact ack:
    return JSONResponse({"result": "ok"})
