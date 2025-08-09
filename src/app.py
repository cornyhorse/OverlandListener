import os, json, time
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import PlainTextResponse

LOG_DIR = Path(os.getenv("LOG_DIR", "/data"))
LOG_FILE = LOG_DIR / "overland.ndjson"
TOKEN = os.getenv("INGEST_TOKEN")  # required via query param ?token=...
AUTH_SECRET = os.getenv("AUTH_SECRET")  # optional: compare against Authorization header

app = FastAPI()

@app.post("/api/input")
async def input_endpoint(request: Request):
    token = (request.query_params.get("token") or "").strip()
    if not TOKEN or token != TOKEN:
        raise HTTPException(status_code=401, detail="bad token")

    if AUTH_SECRET:
        auth = (request.headers.get("authorization") or "").strip()
        if auth != AUTH_SECRET and auth != f"Bearer {AUTH_SECRET}":
            raise HTTPException(status_code=401, detail="bad authorization")

    payload = await request.json()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        record = {
            "ts": int(time.time()),
            "ip": request.client.host if request.client else None,
            "ua": request.headers.get("user-agent"),
            "payload": payload,
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {"success": True}  # plain dict => JSON
