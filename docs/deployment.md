# Deployment Guide

This document covers running OverlandListener in production — Docker setup,
storage configuration, security, and health monitoring.

## Docker Compose (Recommended)

### 1. Create your environment file

```bash
cp .env.example .env
```

Edit `.env` and set **at minimum** `INGEST_TOKEN`:

```dotenv
INGEST_TOKEN=your-secret-token-here
```

### 2. Choose a storage backend

#### Filesystem (default)

No extra config needed. Data is written to `/data/requests/` inside the
container (mapped to `./data/` on the host via the volume mount).

```dotenv
STORAGE_BACKEND=filesystem
LOG_DIR=/data
```

#### S3 or S3-compatible (MinIO, Backblaze B2, etc.)

```dotenv
STORAGE_BACKEND=s3
S3_BUCKET=my-gps-bucket
S3_PREFIX=overland              # optional — adds a key prefix
AWS_REGION=us-east-1            # optional if using a custom endpoint
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJal...
```

**Custom endpoint** (MinIO, Backblaze B2, Wasabi, etc.):

```dotenv
AWS_ENDPOINT_URL=https://s3.us-west-002.backblazeb2.com
```

**IAM roles** (EC2, ECS, Lambda): Omit `AWS_ACCESS_KEY_ID` and
`AWS_SECRET_ACCESS_KEY` — boto3 will use the instance/task role automatically.

> **Tip**: The service performs a write + delete health check on startup to
> verify S3 credentials and permissions. If it fails, the container will not
> start — check the logs for details.

### 3. Start the service

```bash
docker compose up -d
```

### 4. Verify it's running

```bash
curl http://localhost:8000/health
# → {"status":"ok","version":"1.0.0"}
```

The Docker container includes a built-in health check that polls `/health`
every 30 seconds.

## TLS / HTTPS

The service listens on **plain HTTP** (port 8000). In production, place it
behind a TLS-terminating reverse proxy:

- **Caddy** (automatic HTTPS):
  ```
  overland.example.com {
      reverse_proxy localhost:8000
  }
  ```
- **nginx**:
  ```nginx
  server {
      listen 443 ssl;
      server_name overland.example.com;
      ssl_certificate     /etc/ssl/cert.pem;
      ssl_certificate_key /etc/ssl/key.pem;
      location / {
          proxy_pass http://127.0.0.1:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      }
  }
  ```

## Overland App Setup

In the Overland app settings:

1. Set the **Receiver Endpoint** to `https://your-host/api/input`
2. Set the **Access Token** to your `INGEST_TOKEN` value

The app sends the token as an `Authorization: Bearer <token>` header, which
OverlandListener accepts automatically. You can also append `?token=<value>` to
the URL as a fallback.

> **Tip**: API clients can alternatively send the token via the `X-Ingest-Token`
> header, which takes priority over the Bearer header and query parameter.

## Request Size Limit

By default, request bodies are capped at **1 MB** (1,048,576 bytes). Adjust
with:

```dotenv
MAX_BODY_BYTES=2097152   # 2 MB
```

## Debug Mode

Set `DEBUG=1` to enable verbose logging and the `/debug/env` endpoint (which
requires a valid `X-Ingest-Token` header). **Do not enable in production.**

```dotenv
DEBUG=1
```

## Monitoring

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness probe — returns `{"status":"ok","version":"..."}`. No auth required. |
| Docker healthcheck | Built-in — polls `/health` every 30s, 3 retries. |

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INGEST_TOKEN` | **yes** | — | Shared secret for authenticating requests |
| `STORAGE_BACKEND` | no | `filesystem` | `filesystem` or `s3` |
| `LOG_DIR` | no | `/data` | Base directory for filesystem storage |
| `S3_BUCKET` | if s3 | — | Target S3 bucket |
| `S3_PREFIX` | no | `""` | Optional key prefix in the bucket |
| `AWS_REGION` | no | — | AWS region |
| `AWS_ACCESS_KEY_ID` | if s3 | — | AWS access key (or use IAM role) |
| `AWS_SECRET_ACCESS_KEY` | if s3 | — | AWS secret key (or use IAM role) |
| `AWS_ENDPOINT_URL` | no | — | Custom S3 endpoint (MinIO, B2, etc.) |
| `DEBUG` | no | `0` | Enable debug logging and `/debug/env` |
| `MAX_BODY_BYTES` | no | `1048576` | Max request body size (bytes) |

## Security Checklist

- [ ] `INGEST_TOKEN` is a strong random string (e.g. `openssl rand -hex 32`)
- [ ] TLS is terminated before the service (reverse proxy or load balancer)
- [ ] `DEBUG` is `0` in production
- [ ] Container runs as non-root (`appuser` — the default Dockerfile handles this)
- [ ] S3 IAM policy is scoped to the minimum required permissions (`s3:PutObject` on the target bucket/prefix)
- [ ] Host volume (`./data`) has appropriate filesystem permissions
