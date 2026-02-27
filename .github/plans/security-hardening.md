# Plan: Security Hardening

> **Status**: Complete
> Findings documented in `.github/architecture.md` (Security Model section).

## P0 — Critical

- [x] Remove `DEBUG_PRINT_CREDS` — never log secrets
- [x] Use `hmac.compare_digest()` for all token/secret comparisons
- [x] Move ingest token from query param (`?token=`) to `X-Ingest-Token` header
- [x] Add authentication to `/debug/env` (require valid ingest token) or remove it

## P1 — High

- [x] Add request body size limit (default 1 MB)
- [x] Add `USER appuser` to Dockerfile (non-root container)
- [x] Fail fast on startup if `INGEST_TOKEN` is not set
- [x] Cache S3 client instead of creating one per request
- [x] Add `/health` endpoint + Docker healthcheck

## P2 — Medium

- [x] Document reverse-proxy / TLS requirement
- [x] Use atomic writes for filesystem backend
- [x] Migrate from deprecated `on_event("startup")` to `lifespan` context manager

## P3 — Low

- [x] Add `.dockerignore`
- [x] Remove dead code (`s3 = None`)
- [x] Separate imports per PEP 8
- [x] Separate JSON parse errors from validation errors
