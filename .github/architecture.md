# OverlandListener Architecture

## Overview

OverlandListener is a lightweight FastAPI service that receives GPS location data
from the [Overland iOS/Android app](https://overland.p3k.app/) and persists it to
either the local filesystem or an S3-compatible object store.

## Components

```
┌──────────────┐        HTTPS        ┌─────────────────────┐
│  Overland App │ ──────────────────▶ │  OverlandListener   │
└──────────────┘   POST /api/input   │  (FastAPI + Uvicorn)│
                                      └────────┬────────────┘
                                               │
                              ┌────────────────┼────────────────┐
                              ▼                                 ▼
                     ┌────────────────┐               ┌─────────────────┐
                     │  Filesystem    │               │  S3 / MinIO     │
                     │  /data/requests│               │  bucket/prefix  │
                     └────────────────┘               └─────────────────┘
```

### Single-file application (`src/app.py`)

| Concern | Implementation |
|---------|---------------|
| **HTTP framework** | FastAPI with Uvicorn ASGI server |
| **Authentication** | Token via `X-Ingest-Token` header, `Authorization: Bearer` header, or `?token=` query parameter |
| **Storage** | Pluggable: local filesystem (`/data/requests/`) or S3 via boto3 |
| **Naming** | `{epoch_ms}-{sha256_prefix}.json` — collision-resistant, chronologically sortable |
| **Health** | `GET /health` returns 200 when the service can write to the configured backend |
| **Observability** | Structured logging via Python `logging` module (JSON when desired) |

## Data Flow

1. Overland POSTs a JSON payload containing a `locations` array.
2. The service authenticates the request (header, bearer, or query param token).
3. The payload is validated (must be a dict with `locations` key).
4. The full request body is written as a compact JSON file.
5. The service responds `{"result": "ok"}` — the exact format Overland expects.

## Configuration (Environment Variables)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INGEST_TOKEN` | **yes** | — | Shared secret for authenticating requests |
| `STORAGE_BACKEND` | no | `filesystem` | `filesystem` or `s3` |
| `LOG_DIR` | no | `/data` | Base directory for filesystem storage |
| `S3_BUCKET` | if s3 | — | Target S3 bucket |
| `S3_PREFIX` | no | `""` | Optional key prefix in the bucket |
| `AWS_REGION` | no | — | AWS region (boto3 also reads env/role) |
| `AWS_ENDPOINT_URL` | no | — | Custom S3 endpoint (e.g. MinIO) |
| `AWS_ACCESS_KEY_ID` | if s3 | — | AWS credentials (or use IAM role) |
| `AWS_SECRET_ACCESS_KEY` | if s3 | — | AWS credentials (or use IAM role) |
| `DEBUG` | no | `0` | Enable debug logging and `/debug/env` endpoint |
| `MAX_BODY_BYTES` | no | `1048576` | Maximum request body size in bytes |

## Deployment

- **Container image**: `python:3.12-slim` base, non-root `appuser`
- **Port**: 8000 (HTTP) — should be fronted by a TLS-terminating reverse proxy
- **Docker Compose**: included for local development / self-hosting
- **Health check**: `GET /health` used by Docker/orchestrator health probes

## Security Model

- All token comparisons use constant-time `hmac.compare_digest()`
- Tokens are accepted via header, bearer, or query parameter (priority: X-Ingest-Token > Bearer > ?token=)
- Request bodies are size-limited to prevent resource exhaustion
- Container runs as non-root user
- No credentials are ever logged (the `DEBUG_PRINT_CREDS` footgun has been removed)
- Filesystem writes use atomic rename to prevent data corruption
