# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-27

### Added
- GPS location ingestion endpoint (`POST /api/input`) for the Overland app.
- Pluggable storage backends: local filesystem and S3-compatible object stores.
- Health check endpoint (`GET /health`) with version reporting.
- Authenticated debug endpoint (`GET /debug/env`) behind `DEBUG` flag.
- Request body size limiting (`MAX_BODY_BYTES`, default 1 MB).
- Docker image with non-root `appuser` and built-in health check.
- Docker Compose configuration for self-hosting.
- Comprehensive test suite (51 tests, 98% coverage).

### Security
- All token comparisons use constant-time `hmac.compare_digest()`.
- Authentication via `X-Ingest-Token` header (never query parameters).
- Optional secondary auth via `Authorization: Bearer` header.
- Atomic filesystem writes (temp file + rename) to prevent corruption.
- No credentials are ever logged.
- Container runs as non-root user.
- Startup fails fast if `INGEST_TOKEN` is not configured.
