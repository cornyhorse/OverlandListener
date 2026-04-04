# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).



























## [1.27.0] - 2026-04-04

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- uvicorn[standard]==0.42.0
- boto3==1.42.82
+ uvicorn[standard]==0.43.0
+ boto3==1.42.83
```

## [1.26.0] - 2026-04-03

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.81
+ boto3==1.42.82
```

## [1.25.0] - 2026-04-02

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- fastapi==0.135.2
+ fastapi==0.135.3
- boto3==1.42.80
+ boto3==1.42.81
```

## [1.24.0] - 2026-04-01

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.79
+ boto3==1.42.80
```

## [1.23.0] - 2026-03-31

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.78
+ boto3==1.42.79
```

## [1.22.0] - 2026-03-28

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.77
+ boto3==1.42.78
```

## [1.21.0] - 2026-03-27

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.76
+ boto3==1.42.77
```

## [1.20.0] - 2026-03-26

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.75
+ boto3==1.42.76
```

## [1.19.0] - 2026-03-25

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.74
+ boto3==1.42.75
```

## [1.18.0] - 2026-03-24

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- fastapi==0.135.1
+ fastapi==0.135.2
- boto3==1.42.73
+ boto3==1.42.74
```

## [1.17.0] - 2026-03-22

### Changed
- Bumped dependencies to latest compatible versions.

#### Dev
```
- pytest-cov==7.0.0
+ pytest-cov==7.1.0
```

## [1.16.0] - 2026-03-21

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.72
+ boto3==1.42.73
```

## [1.15.0] - 2026-03-20

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.71
+ boto3==1.42.72
```

## [1.14.0] - 2026-03-19

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.70
+ boto3==1.42.71
```

## [1.13.0] - 2026-03-18

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.69
+ boto3==1.42.70
```

## [1.12.0] - 2026-03-17

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- uvicorn[standard]==0.41.0
- boto3==1.42.68
+ uvicorn[standard]==0.42.0
+ boto3==1.42.69
```

## [1.11.0] - 2026-03-14

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.67
+ boto3==1.42.68
```

## [1.10.0] - 2026-03-13

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.65
+ boto3==1.42.67
```

#### Dev
```
- black==26.3.0
+ black==26.3.1
```

## [1.9.0] - 2026-03-11

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.64
+ boto3==1.42.65
```

## [1.8.0] - 2026-03-10

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.63
+ boto3==1.42.64
```

## [1.7.0] - 2026-03-07

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.62
+ boto3==1.42.63
```

#### Dev
```
- black==26.1.0
+ black==26.3.0
```

## [1.6.0] - 2026-03-06

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.61
+ boto3==1.42.62
```

## [1.5.0] - 2026-03-05

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.60
+ boto3==1.42.61
```

## [1.4.0] - 2026-03-04

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- boto3==1.42.59
+ boto3==1.42.60
```

## [1.3.0] - 2026-03-02

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- fastapi==0.134.0
+ fastapi==0.135.1
```

## [1.2.0] - 2026-02-28

### Changed
- **Auth**: Ingest token now accepted via `Authorization: Bearer` header and
  `?token=` query parameter, in addition to `X-Ingest-Token` header.
  Priority: `X-Ingest-Token` > `Bearer` > `?token=`.
- Removed `AUTH_SECRET` configuration — the secondary bearer check was
  incompatible with the Overland app (which can only send URL + Access Token).

### Removed
- `AUTH_SECRET` environment variable and dual-header auth flow.

## [1.1.0] - 2026-02-28

### Changed
- Bumped dependencies to latest compatible versions.

#### Runtime
```
- fastapi==0.115.0
- uvicorn[standard]==0.30.6
- boto3==1.34.158
+ fastapi==0.134.0
+ uvicorn[standard]==0.41.0
+ boto3==1.42.59
```

#### Dev
```
- pytest==8.3.3
- pytest-cov==5.0.0
- httpx==0.27.2
- black==24.10.0
+ pytest==9.0.2
+ pytest-cov==7.0.0
+ httpx==0.28.1
+ black==26.1.0
```

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
