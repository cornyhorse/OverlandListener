# Copilot Instructions for OverlandListener

## Project Overview

OverlandListener is a FastAPI service that receives GPS location data from the
[Overland](https://overland.p3k.app/) mobile app and stores it on the local
filesystem or in S3-compatible object storage.

## Key Documentation

- **Architecture**: `.github/architecture.md` — system design, data flow,
  configuration reference, security model, deployment notes.
- **Plans** (work-in-progress tracking): `.github/plans/` — files here track
  in-flight work. Once a plan is finished its content is merged into the
  architecture doc or README and the plan file is marked complete.
- **README**: `README.md` — user-facing setup, usage, and development guide.
- **Deployment Guide**: `docs/deployment.md` — Docker, S3, TLS, Overland app
  setup, security checklist (operator audience).
- **Development Guide**: `docs/development.md` — local setup, testing,
  formatting, CI, versioning, releases (contributor audience).

## Code Layout

```
src/app.py              — entire application (single-file FastAPI app)
tests/                  — pytest test suite
scripts/bump_version.py — version bump helper
Dockerfile              — production container image
docker-compose.yaml     — local / self-hosted deployment
requirements.txt        — pinned runtime dependencies
requirements-dev.txt    — dev/test dependencies
CHANGELOG.md            — release history (Keep a Changelog format)
.github/workflows/      — CI and nightly dependency update workflows
```

## Coding Conventions

- **Python 3.12+**, type hints encouraged on all public functions.
- **Formatting**: `black` (run `scripts/lint.sh --fix` to auto-format).
- One import per line (PEP 8).
- Use `logging` module — never bare `print()` for observability.
- Secrets are **never** logged, even partially masked.
- All secret comparisons must use `hmac.compare_digest()`.
- Filesystem writes should be atomic (write to temp file, then `os.rename()`).
- Keep `src/app.py` as a single file unless complexity warrants splitting.
- PRs must pass lint + tests before merging to `main`. Direct pushes to `main` are not allowed.

## Testing

- Test runner: `pytest`
- HTTP tests: FastAPI `TestClient` (from `httpx`)
- S3 mocking: `unittest.mock.patch`
- Run: `pytest tests/ -v --cov=src --cov-report=term-missing`
- Target: 100% line coverage on `src/app.py`

## Versioning

- Semantic Versioning (semver). Canonical version in `src/app.py` `__version__`.
- `scripts/bump_version.py` updates version across `src/app.py`, `Dockerfile`, `docker-compose.yaml`.
- Nightly GitHub Actions workflow bumps deps, runs tests, auto-releases minor if changed.
- All releases documented in `CHANGELOG.md`.

## Security Principles

- Tokens in headers, never in query parameters.
- Request body size is capped (`MAX_BODY_BYTES`, default 1 MB).
- Container runs as non-root (`appuser`).
- Debug endpoints require authentication.
- No credential logging of any kind.
