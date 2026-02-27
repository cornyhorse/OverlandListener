# Plan: Testing

> **Status**: Complete
> Test instructions documented in the project README.

## Goals

- Unit test coverage for all helper functions
- Integration tests for the `/api/input` and `/health` endpoints
- Test both filesystem and (mocked) S3 storage backends
- Test all auth scenarios (valid, invalid, missing)
- Test body size limits

## Test Stack

- `pytest` as test runner
- `httpx` + FastAPI `TestClient` for endpoint tests
- `unittest.mock` / `pytest-mock` for S3 mocking
- `pytest-cov` for coverage reporting

## Test Matrix

### Unit Tests
- [x] `_truthy()` — various inputs
- [x] `compact_json()` — deterministic output
- [x] `make_name()` — format, uniqueness
- [x] `s3_key_for()` — with and without prefix
- [x] `_safe_compare()` — constant-time wrapper

### Endpoint Tests
- [x] `POST /api/input` — valid request (filesystem)
- [x] `POST /api/input` — valid request (S3 mock)
- [x] `POST /api/input` — missing token → 401
- [x] `POST /api/input` — bad token → 401
- [x] `POST /api/input` — bad auth header → 401
- [x] `POST /api/input` — invalid JSON → 400
- [x] `POST /api/input` — missing `locations` key → 400
- [x] `POST /api/input` — body too large → 413
- [x] `GET /health` — returns 200
- [x] `GET /debug/env` — requires auth + DEBUG flag

### Integration Tests
- [x] Filesystem write produces correct file content
- [x] Startup check creates and cleans up healthcheck file
