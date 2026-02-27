# Development Guide

This document covers contributing to OverlandListener — local setup, testing,
formatting, CI, versioning, and release process.

## Prerequisites

- Python 3.12+
- A virtual environment is recommended

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Running Locally

```bash
export INGEST_TOKEN=dev-token
export STORAGE_BACKEND=filesystem
export LOG_DIR=./data
uvicorn src.app:app --reload --port 8000
```

## Testing

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

Current coverage: **98%** (51 tests). The only uncovered lines are defensive
branches for race conditions that cannot be reliably triggered in tests.

CI enforces a **95% minimum** coverage threshold.

## Formatting

This project uses [black](https://black.readthedocs.io/) with a 120-char line
limit (configured in `pyproject.toml`).

```bash
scripts/lint.sh          # check only (CI mode)
scripts/lint.sh --fix    # auto-format in place
```

## Branch Protection & Pull Requests

The `main` branch requires a pull request with passing CI (lint + tests) before
merging. Direct pushes to `main` are not allowed.

To configure branch protection in GitHub:

1. Go to **Settings → Branches → Branch protection rules**
2. Add rule for `main`
3. Enable:
   - **Require a pull request before merging**
   - **Require status checks to pass before merging** — select `lint` and `test`
   - **Require branches to be up to date before merging**

## CI Workflows

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| **CI** (`.github/workflows/ci.yml`) | Push / PR to `main` | Lint check (`black`), then run tests with coverage |
| **Nightly Deps** (`.github/workflows/nightly-deps.yml`) | 04:00 UTC daily / manual | Bump all pinned deps to latest, run tests, auto-release minor if changed |

## Versioning & Releases

This project uses [Semantic Versioning](https://semver.org/).

- The canonical version lives in `src/app.py` (`__version__`) and is mirrored
  in the Dockerfile labels and docker-compose image tag.
- **Nightly auto-releases**: The nightly workflow bumps all pinned dependencies,
  runs the test suite, and if everything passes and something changed, creates a
  new **minor** release automatically.
- **Manual releases**: Use the bump script then tag:
  ```bash
  python scripts/bump_version.py minor   # or: patch, major, 1.2.3
  # update CHANGELOG.md
  git add -A && git commit -m "release: vX.Y.Z"
  git tag vX.Y.Z && git push origin main --tags
  ```
- All releases are documented in [`CHANGELOG.md`](../CHANGELOG.md).

## Project Structure

```
src/app.py              — entire application (single-file FastAPI app)
tests/test_app.py       — pytest test suite
scripts/
  bump_version.py       — version bump helper
  lint.sh               — black formatter wrapper
Dockerfile              — production container image
docker-compose.yaml     — local / self-hosted deployment
requirements.txt        — pinned runtime dependencies
requirements-dev.txt    — dev/test dependencies
CHANGELOG.md            — release history (Keep a Changelog format)
docs/
  development.md        — this file
  deployment.md         — Docker & S3 setup guide
.github/
  architecture.md       — system design, data flow, security model
  copilot-instructions.md — AI assistant coding context
  plans/                — work-in-progress tracking
  workflows/ci.yml      — lint + test on push/PR
  workflows/nightly-deps.yml — nightly dependency update + auto-release
```
