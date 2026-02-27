# OverlandListener

A lightweight [FastAPI](https://fastapi.tiangolo.com/) service that receives GPS
location data from the [Overland](https://overland.p3k.app/) mobile app and
persists it to the local filesystem or an S3-compatible object store.

## Quick Start

### 1. Configure

Copy the example env file and fill in at minimum the `INGEST_TOKEN`:

```bash
cp .env.example .env
# edit .env — INGEST_TOKEN is required
```

### 2. Run with Docker Compose

```bash
docker compose up -d
```

The service listens on port **8000**. In production, front it with a
TLS-terminating reverse proxy (nginx, Caddy, etc.).

### 3. Point Overland at it

In the Overland app, set the **Receiver Endpoint** to:

```
https://your-host:8000/api/input
```

Set the **Token** header name to `X-Ingest-Token` and the value to your
`INGEST_TOKEN`. (Overland supports custom request headers.)

## Configuration

All configuration is via environment variables. See
[`.env.example`](.env.example) for the full list.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INGEST_TOKEN` | **yes** | — | Shared secret for authenticating requests |
| `AUTH_SECRET` | no | — | Optional secondary auth via `Authorization: Bearer` header |
| `STORAGE_BACKEND` | no | `filesystem` | `filesystem` or `s3` |
| `LOG_DIR` | no | `/data` | Base directory for filesystem storage |
| `S3_BUCKET` | if s3 | — | Target S3 bucket |
| `S3_PREFIX` | no | `""` | Optional key prefix in the bucket |
| `AWS_REGION` | no | — | AWS region |
| `AWS_ENDPOINT_URL` | no | — | Custom S3 endpoint (e.g. MinIO) |
| `DEBUG` | no | `0` | Enable debug logging and `/debug/env` |
| `MAX_BODY_BYTES` | no | `1048576` | Max request body size (bytes) |

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/input` | `X-Ingest-Token` | Receive Overland location payload |
| `GET` | `/health` | none | Liveness probe — returns `{"status":"ok"}` |
| `GET` | `/debug/env` | `X-Ingest-Token` + `DEBUG=1` | Non-secret config dump |

## Development

### Prerequisites

- Python 3.12+
- A virtual environment is recommended

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### Running locally

```bash
export INGEST_TOKEN=dev-token
export STORAGE_BACKEND=filesystem
export LOG_DIR=./data
uvicorn src.app:app --reload --port 8000
```

### Testing

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

Current coverage: **98%** (51 tests). The only uncovered lines are defensive
branches for race conditions that cannot be reliably triggered in tests.

### Project Structure

```
src/app.py              — entire application (single-file FastAPI app)
tests/test_app.py       — pytest test suite
scripts/bump_version.py — version bump helper
Dockerfile              — production container image
docker-compose.yaml     — local / self-hosted deployment
requirements.txt        — pinned runtime dependencies
requirements-dev.txt    — dev/test dependencies
CHANGELOG.md            — release history (Keep a Changelog format)
.github/
  architecture.md       — system design, data flow, security model
  copilot-instructions.md — AI assistant coding context
  plans/                — work-in-progress tracking
  workflows/ci.yml      — test on push/PR
  workflows/nightly-deps.yml — nightly dependency update + auto-release
```

## Versioning & Releases

This project uses [Semantic Versioning](https://semver.org/).

- The canonical version lives in `src/app.py` (`__version__`) and is mirrored
  in the Dockerfile labels and docker-compose image tag.
- **Nightly**: A GitHub Actions workflow runs every night at 04:00 UTC. It bumps
  all pinned dependencies to their latest versions, runs the test suite, and if
  everything passes and something changed, it creates a new **minor** release
  automatically.
- **Manual releases**: Use the bump script then tag:
  ```bash
  python scripts/bump_version.py minor   # or: patch, major, 1.2.3
  # update CHANGELOG.md
  git add -A && git commit -m "release: vX.Y.Z"
  git tag vX.Y.Z && git push origin main --tags
  ```
- All releases are documented in [`CHANGELOG.md`](CHANGELOG.md).

## Security

- Tokens are passed in headers — never in query parameters or URLs
- All secret comparisons use constant-time `hmac.compare_digest()`
- Request bodies are size-limited (default 1 MB)
- Filesystem writes are atomic (temp file + rename)
- Container runs as non-root (`appuser`)
- No credentials are ever logged
- Debug endpoints require authentication

See [`.github/architecture.md`](.github/architecture.md) for the full security model.

## License

See [LICENSE](LICENSE).