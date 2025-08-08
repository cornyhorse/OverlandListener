import os, json, time
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

LOG_DIR = Path(os.getenv("LOG_DIR", "/data"))
LOG_FILE = LOG_DIR / "overland.ndjson"
TOKEN = os.getenv("INGEST_TOKEN")  # required via query param ?token=...
AUTH_SECRET = os.getenv("AUTH_SECRET")  # optional: compare against Authorization header

app = FastAPI()

@app.post("/api/input")
async def input_endpoint(request: Request):
    # auth: query token
    token = request.query_params.get("token")
    if not TOKEN or token != TOKEN:
        raise HTTPException(status_code=401, detail="bad token")

    # optional: header auth check (e.g., "Bearer xyz")
    if AUTH_SECRET:
        auth = request.headers.get("authorization", "")
        if AUTH_SECRET not in auth:
            raise HTTPException(status_code=401, detail="bad authorization")

    try:
        payload = await request.json()
        if not isinstance(payload, dict) or "locations" not in payload:
            raise ValueError("missing locations")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        record = {
            "ts": int(time.time()),
            "ip": request.client.host if request.client else None,
            "ua": request.headers.get("user-agent"),
            "payload": payload,
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return JSONResponse({"ok": True})