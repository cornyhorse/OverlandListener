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

app = FastAPI()
s3 = None


# ---- Helpers ----
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
        client.put_object(Bucket=S3_BUCKET, Key=key, Body=test_content, ContentType="text/plain")
        # optional cleanup; comment out if you want it to stay
        client.delete_object(Bucket=S3_BUCKET, Key=key)
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
    startup_write_check()


# ---- Endpoint ----
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
