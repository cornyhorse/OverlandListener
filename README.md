# OverlandListener

A lightweight [FastAPI](https://fastapi.tiangolo.com/) service that receives GPS
location data from the [Overland](https://overland.p3k.app/) mobile app and
persists it to the local filesystem or an S3-compatible object store.

## Quick Start

```bash
cp .env.example .env       # set INGEST_TOKEN at minimum
docker compose up -d
curl http://localhost:8000/health
```

Then point the Overland app at `https://your-host:8000/api/input` with your
`INGEST_TOKEN` as the Access Token.

## Configuration

All configuration is via environment variables — see
[`.env.example`](.env.example) for the full list.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INGEST_TOKEN` | **yes** | — | Shared secret for authenticating requests |
| `STORAGE_BACKEND` | no | `filesystem` | `filesystem` or `s3` |
| `LOG_DIR` | no | `/data` | Base directory for filesystem storage |
| `S3_BUCKET` | if s3 | — | Target S3 bucket |
| `S3_PREFIX` | no | `""` | Optional key prefix in the bucket |
| `AWS_REGION` | no | — | AWS region |
| `AWS_ENDPOINT_URL` | no | — | Custom S3 endpoint (MinIO, B2, etc.) |
| `DEBUG` | no | `0` | Enable debug logging and `/debug/env` |
| `MAX_BODY_BYTES` | no | `1048576` | Max request body size (bytes) |

For detailed S3 setup, reverse proxy configuration, and the full security
checklist, see the **[Deployment Guide](docs/deployment.md)**.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/input` | `X-Ingest-Token` / `Bearer` / `?token=` | Receive Overland location payload |
| `GET` | `/health` | none | Liveness probe — returns `{"status":"ok"}` |
| `GET` | `/debug/env` | `X-Ingest-Token` + `DEBUG=1` | Non-secret config dump |

## Security

- Tokens in headers — query parameter fallback available for constrained clients
- Constant-time `hmac.compare_digest()` for all secret comparisons
- Request bodies size-limited (default 1 MB)
- Atomic filesystem writes (temp file + rename)
- Container runs as non-root (`appuser`)
- No credentials are ever logged
- Debug endpoints require authentication

See [`.github/architecture.md`](.github/architecture.md) for the full security
model.

## Documentation

| Document | Audience | Contents |
|----------|----------|----------|
| **[Deployment Guide](docs/deployment.md)** | Operators | Docker, S3, TLS, Overland app setup, security checklist |
| **[Development Guide](docs/development.md)** | Contributors | Local setup, testing, formatting, CI, versioning, releases |
| **[Architecture](.github/architecture.md)** | Contributors | System design, data flow, security model |
| **[Changelog](CHANGELOG.md)** | Everyone | Release history |

## License

See [LICENSE](LICENSE).