"""Tests for OverlandListener (src/app.py)."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures — set required env vars before importing the app module
# ---------------------------------------------------------------------------

# We need INGEST_TOKEN set at import time because the module reads os.getenv
# at top level. We patch the environment before every test module load.

TEST_TOKEN = "test-token-abc123"


@pytest.fixture(autouse=True)
def _clean_s3_cache():
    """Reset the cached S3 client between tests."""
    import src.app as app_module

    app_module._s3_client = None
    yield
    app_module._s3_client = None


@pytest.fixture()
def tmp_data_dir(tmp_path: Path):
    """Provide a temporary data directory for filesystem tests."""
    return tmp_path


@pytest.fixture()
def fs_env(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """Set env vars for filesystem-backed tests."""
    monkeypatch.setenv("INGEST_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.setenv("LOG_DIR", str(tmp_data_dir))
    monkeypatch.setenv("DEBUG", "0")
    monkeypatch.delenv("S3_BUCKET", raising=False)
    # Reload config values in the module
    _reload_config(monkeypatch)


@pytest.fixture()
def fs_env_debug(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """Set env vars for filesystem-backed tests with DEBUG=1."""
    monkeypatch.setenv("INGEST_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.setenv("LOG_DIR", str(tmp_data_dir))
    monkeypatch.setenv("DEBUG", "1")
    monkeypatch.delenv("S3_BUCKET", raising=False)
    _reload_config(monkeypatch)



@pytest.fixture()
def s3_env(monkeypatch: pytest.MonkeyPatch):
    """Set env vars for S3-backed tests."""
    monkeypatch.setenv("INGEST_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("S3_PREFIX", "gps")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("DEBUG", "0")
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    _reload_config(monkeypatch)


def _reload_config(monkeypatch: pytest.MonkeyPatch):
    """Patch module-level config values to match current env."""
    import src.app as app_module

    monkeypatch.setattr(app_module, "STORAGE_BACKEND", os.getenv("STORAGE_BACKEND", "filesystem").strip().lower())
    monkeypatch.setattr(app_module, "LOG_DIR", Path(os.getenv("LOG_DIR", "/data")))
    monkeypatch.setattr(app_module, "TOKEN", os.getenv("INGEST_TOKEN"))
    monkeypatch.setattr(app_module, "S3_BUCKET", os.getenv("S3_BUCKET"))
    monkeypatch.setattr(app_module, "S3_PREFIX", os.getenv("S3_PREFIX", "").strip().strip("/"))
    monkeypatch.setattr(app_module, "AWS_REGION", os.getenv("AWS_REGION"))
    monkeypatch.setattr(app_module, "AWS_ENDPOINT_URL", os.getenv("AWS_ENDPOINT_URL"))
    monkeypatch.setattr(app_module, "DEBUG", os.getenv("DEBUG", "0"))
    monkeypatch.setattr(app_module, "MAX_BODY_BYTES", int(os.getenv("MAX_BODY_BYTES", "1048576")))


def _make_client() -> TestClient:
    """Build a TestClient that skips the lifespan (we test startup separately)."""
    from src.app import app

    return TestClient(app, raise_server_exceptions=False)


def _valid_payload() -> dict:
    return {"locations": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [-122.0, 37.0]}}]}


# ===========================================================================
# Unit tests — pure helper functions
# ===========================================================================


class TestTruthy:
    def test_truthy_values(self):
        from src.app import _truthy

        for v in ("1", "true", "True", "TRUE", "yes", "YES", "y", "Y", "on", "ON"):
            assert _truthy(v) is True, f"Expected True for {v!r}"

    def test_falsy_values(self):
        from src.app import _truthy

        for v in ("0", "false", "no", "n", "off", "", "random"):
            assert _truthy(v) is False, f"Expected False for {v!r}"

    def test_non_string(self):
        from src.app import _truthy

        assert _truthy(1) is True
        assert _truthy(0) is False
        assert _truthy(None) is False


class TestSafeCompare:
    def test_equal(self):
        from src.app import _safe_compare

        assert _safe_compare("abc", "abc") is True

    def test_not_equal(self):
        from src.app import _safe_compare

        assert _safe_compare("abc", "xyz") is False

    def test_empty_strings(self):
        from src.app import _safe_compare

        assert _safe_compare("", "") is True

    def test_unicode(self):
        from src.app import _safe_compare

        assert _safe_compare("héllo", "héllo") is True
        assert _safe_compare("héllo", "hello") is False


class TestCompactJson:
    def test_no_whitespace(self):
        from src.app import compact_json

        result = compact_json({"a": 1, "b": [2, 3]})
        assert " " not in result
        assert json.loads(result) == {"a": 1, "b": [2, 3]}

    def test_unicode_preserved(self):
        from src.app import compact_json

        result = compact_json({"name": "café"})
        assert "café" in result


class TestMakeName:
    def test_format(self):
        from src.app import make_name

        name = make_name({"locations": []})
        parts = name.split("-")
        assert len(parts) == 2
        assert parts[1].endswith(".json")
        # Timestamp part is numeric
        assert parts[0].isdigit()

    def test_deterministic_hash(self):
        from src.app import make_name

        # Same payload within same millisecond should share the hash part
        payload = {"locations": [{"x": 1}]}
        n1 = make_name(payload)
        n2 = make_name(payload)
        assert n1.split("-")[1] == n2.split("-")[1]  # hash portion identical


class TestS3KeyFor:
    def test_with_prefix(self):
        from src.app import s3_key_for
        import src.app as app_module

        original = app_module.S3_PREFIX
        try:
            app_module.S3_PREFIX = "gps"
            assert s3_key_for("file.json") == "gps/requests/file.json"
        finally:
            app_module.S3_PREFIX = original

    def test_without_prefix(self):
        from src.app import s3_key_for
        import src.app as app_module

        original = app_module.S3_PREFIX
        try:
            app_module.S3_PREFIX = ""
            assert s3_key_for("file.json") == "requests/file.json"
        finally:
            app_module.S3_PREFIX = original


# ===========================================================================
# Filesystem storage tests
# ===========================================================================


class TestFsWriteRequest:
    def test_creates_file(self, fs_env, tmp_data_dir: Path):
        from src.app import fs_write_request

        payload = _valid_payload()
        fs_write_request(payload)
        req_dir = tmp_data_dir / "requests"
        files = list(req_dir.glob("*.json"))
        assert len(files) == 1
        content = json.loads(files[0].read_text("utf-8"))
        assert content == payload

    def test_atomic_write_no_temp_files(self, fs_env, tmp_data_dir: Path):
        from src.app import fs_write_request

        fs_write_request(_valid_payload())
        req_dir = tmp_data_dir / "requests"
        # No leftover .tmp files
        assert list(req_dir.glob("*.tmp")) == []


class TestStartupWriteCheckFs:
    def test_creates_and_removes_healthcheck(self, fs_env, tmp_data_dir: Path):
        from src.app import startup_write_check

        startup_write_check()
        assert tmp_data_dir.exists()
        # healthcheck.txt should be cleaned up
        assert not (tmp_data_dir / "healthcheck.txt").exists()


# ===========================================================================
# S3 storage tests (mocked)
# ===========================================================================


class TestS3WriteRequest:
    def test_puts_object(self, s3_env):
        mock_client = MagicMock()
        with patch("src.app.get_s3_client", return_value=mock_client):
            from src.app import s3_write_request

            payload = _valid_payload()
            s3_write_request(payload)
            mock_client.put_object.assert_called_once()
            call_kwargs = mock_client.put_object.call_args[1]
            assert call_kwargs["Bucket"] == "test-bucket"
            assert call_kwargs["Key"].startswith("gps/requests/")
            assert call_kwargs["ContentType"] == "application/json"


class TestStartupWriteCheckS3:
    def test_s3_write_and_delete(self, s3_env):
        mock_client = MagicMock()
        with patch("src.app.get_s3_client", return_value=mock_client):
            from src.app import startup_write_check

            startup_write_check()
            assert mock_client.put_object.call_count == 1
            assert mock_client.delete_object.call_count == 1

    def test_s3_no_bucket_raises(self, s3_env, monkeypatch: pytest.MonkeyPatch):
        import src.app as app_module

        monkeypatch.setattr(app_module, "S3_BUCKET", None)
        from src.app import startup_write_check

        with pytest.raises(RuntimeError, match="S3_BUCKET not set"):
            startup_write_check()

    def test_s3_write_failure_raises(self, s3_env):
        mock_client = MagicMock()
        mock_client.put_object.side_effect = Exception("connection refused")
        with patch("src.app.get_s3_client", return_value=mock_client):
            from src.app import startup_write_check

            with pytest.raises(Exception, match="connection refused"):
                startup_write_check()


class TestGetS3Client:
    def test_caches_client(self, s3_env):
        import src.app as app_module

        app_module._s3_client = None
        with patch("boto3.client") as mock_boto:
            mock_boto.return_value = MagicMock()
            c1 = app_module.get_s3_client()
            c2 = app_module.get_s3_client()
            assert c1 is c2
            mock_boto.assert_called_once()

    def test_passes_region_and_endpoint(self, s3_env, monkeypatch: pytest.MonkeyPatch):
        import src.app as app_module

        app_module._s3_client = None
        monkeypatch.setattr(app_module, "AWS_REGION", "eu-west-1")
        monkeypatch.setattr(app_module, "AWS_ENDPOINT_URL", "http://minio:9000")
        with patch("boto3.client") as mock_boto:
            mock_boto.return_value = MagicMock()
            app_module.get_s3_client()
            mock_boto.assert_called_once_with("s3", region_name="eu-west-1", endpoint_url="http://minio:9000")


# ===========================================================================
# write_request dispatch tests
# ===========================================================================


class TestWriteRequest:
    def test_filesystem_dispatch(self, fs_env, tmp_data_dir: Path):
        from src.app import write_request

        write_request(_valid_payload())
        assert list((tmp_data_dir / "requests").glob("*.json"))

    def test_s3_dispatch(self, s3_env):
        mock_client = MagicMock()
        with patch("src.app.get_s3_client", return_value=mock_client):
            from src.app import write_request

            write_request(_valid_payload())
            mock_client.put_object.assert_called_once()

    def test_s3_no_bucket_raises(self, s3_env, monkeypatch: pytest.MonkeyPatch):
        import src.app as app_module

        monkeypatch.setattr(app_module, "S3_BUCKET", None)
        from src.app import write_request

        with pytest.raises(RuntimeError, match="S3_BUCKET not set"):
            write_request(_valid_payload())


# ===========================================================================
# log_config tests
# ===========================================================================


class TestLogConfig:
    def test_fs_config(self, fs_env, caplog):
        from src.app import log_config
        import logging

        with caplog.at_level(logging.DEBUG, logger="overland"):
            log_config()
        assert "STORAGE_BACKEND=filesystem" in caplog.text

    def test_s3_config_no_creds_logged(self, s3_env, monkeypatch: pytest.MonkeyPatch, caplog):
        """Ensure AWS credentials are never logged — only (set)/(unset) indicators."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        from src.app import log_config
        import logging

        with caplog.at_level(logging.DEBUG, logger="overland"):
            log_config()
        assert "AKIAIOSFODNN7EXAMPLE" not in caplog.text
        assert "wJalrXUtnFEMI" not in caplog.text
        assert "(set)" in caplog.text


# ===========================================================================
# Endpoint tests — /health
# ===========================================================================


class TestHealthEndpoint:
    def test_returns_ok(self, fs_env):
        client = _make_client()
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


# ===========================================================================
# Endpoint tests — /debug/env
# ===========================================================================


class TestDebugEnvEndpoint:
    def test_404_when_debug_off(self, fs_env):
        client = _make_client()
        resp = client.get("/debug/env", headers={"x-ingest-token": TEST_TOKEN})
        assert resp.status_code == 404

    def test_401_when_no_token(self, fs_env_debug):
        client = _make_client()
        resp = client.get("/debug/env")
        assert resp.status_code == 401

    def test_401_when_bad_token(self, fs_env_debug):
        client = _make_client()
        resp = client.get("/debug/env", headers={"x-ingest-token": "wrong"})
        assert resp.status_code == 401

    def test_returns_config_when_debug_and_authed(self, fs_env_debug):
        client = _make_client()
        resp = client.get("/debug/env", headers={"x-ingest-token": TEST_TOKEN})
        assert resp.status_code == 200
        data = resp.json()
        assert data["storage_backend"] == "filesystem"
        assert data["debug"] is True
        # Must not contain any AWS key data
        assert "aws_access_key_id" not in data


# ===========================================================================
# Endpoint tests — POST /api/input
# ===========================================================================


class TestInputEndpoint:
    def test_valid_request_fs(self, fs_env, tmp_data_dir: Path):
        client = _make_client()
        resp = client.post(
            "/api/input",
            json=_valid_payload(),
            headers={"x-ingest-token": TEST_TOKEN},
        )
        assert resp.status_code == 200
        assert resp.json() == {"result": "ok"}
        # Verify file was written
        files = list((tmp_data_dir / "requests").glob("*.json"))
        assert len(files) == 1

    def test_valid_request_s3(self, s3_env):
        mock_client = MagicMock()
        with patch("src.app.get_s3_client", return_value=mock_client):
            client = _make_client()
            resp = client.post(
                "/api/input",
                json=_valid_payload(),
                headers={"x-ingest-token": TEST_TOKEN},
            )
            assert resp.status_code == 200
            mock_client.put_object.assert_called_once()

    def test_missing_token_401(self, fs_env):
        client = _make_client()
        resp = client.post("/api/input", json=_valid_payload())
        assert resp.status_code == 401

    def test_bad_token_401(self, fs_env):
        client = _make_client()
        resp = client.post(
            "/api/input",
            json=_valid_payload(),
            headers={"x-ingest-token": "wrong-token"},
        )
        assert resp.status_code == 401

    def test_bearer_token_accepted(self, fs_env, tmp_data_dir: Path):
        """Token accepted via Authorization: Bearer header (no X-Ingest-Token)."""
        client = _make_client()
        resp = client.post(
            "/api/input",
            json=_valid_payload(),
            headers={"authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"result": "ok"}
        files = list((tmp_data_dir / "requests").glob("*.json"))
        assert len(files) == 1

    def test_query_param_token_accepted(self, fs_env, tmp_data_dir: Path):
        """Token accepted via ?token= query parameter."""
        client = _make_client()
        resp = client.post(
            f"/api/input?token={TEST_TOKEN}",
            json=_valid_payload(),
        )
        assert resp.status_code == 200
        assert resp.json() == {"result": "ok"}
        files = list((tmp_data_dir / "requests").glob("*.json"))
        assert len(files) == 1

    def test_header_takes_priority_over_bearer(self, fs_env, tmp_data_dir: Path):
        """X-Ingest-Token takes priority when both headers are present."""
        client = _make_client()
        resp = client.post(
            "/api/input",
            json=_valid_payload(),
            headers={
                "x-ingest-token": TEST_TOKEN,
                "authorization": "Bearer wrong-value",
            },
        )
        assert resp.status_code == 200

    def test_wrong_bearer_token_401(self, fs_env):
        """Wrong Bearer token returns 401."""
        client = _make_client()
        resp = client.post(
            "/api/input",
            json=_valid_payload(),
            headers={"authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    def test_wrong_query_param_token_401(self, fs_env):
        """Wrong query param token returns 401."""
        client = _make_client()
        resp = client.post(
            "/api/input?token=wrong-token",
            json=_valid_payload(),
        )
        assert resp.status_code == 401

    def test_no_token_at_all_401(self, fs_env):
        """No token provided at all returns 401."""
        client = _make_client()
        resp = client.post("/api/input", json=_valid_payload())
        assert resp.status_code == 401

    def test_invalid_json_400(self, fs_env):
        client = _make_client()
        resp = client.post(
            "/api/input",
            content=b"not json at all",
            headers={
                "x-ingest-token": TEST_TOKEN,
                "content-type": "application/json",
            },
        )
        assert resp.status_code == 400
        assert "invalid JSON" in resp.json()["detail"]

    def test_missing_locations_400(self, fs_env):
        client = _make_client()
        resp = client.post(
            "/api/input",
            json={"something": "else"},
            headers={"x-ingest-token": TEST_TOKEN},
        )
        assert resp.status_code == 400
        assert "missing locations" in resp.json()["detail"]

    def test_non_dict_payload_400(self, fs_env):
        client = _make_client()
        resp = client.post(
            "/api/input",
            json=[1, 2, 3],
            headers={"x-ingest-token": TEST_TOKEN},
        )
        assert resp.status_code == 400

    def test_body_too_large_413(self, fs_env, monkeypatch: pytest.MonkeyPatch):
        import src.app as app_module

        monkeypatch.setattr(app_module, "MAX_BODY_BYTES", 50)
        client = _make_client()
        big_payload = {"locations": [{"data": "x" * 100}]}
        resp = client.post(
            "/api/input",
            json=big_payload,
            headers={"x-ingest-token": TEST_TOKEN},
        )
        assert resp.status_code == 413

    def test_content_length_too_large_413(self, fs_env, monkeypatch: pytest.MonkeyPatch):
        import src.app as app_module

        monkeypatch.setattr(app_module, "MAX_BODY_BYTES", 50)
        client = _make_client()
        resp = client.post(
            "/api/input",
            content=b'{"locations":[]}',
            headers={
                "x-ingest-token": TEST_TOKEN,
                "content-type": "application/json",
                "content-length": "999999",
            },
        )
        assert resp.status_code == 413


# ===========================================================================
# Lifespan tests
# ===========================================================================


class TestInputEndpointEdgeCases:
    """Cover remaining edge-case branches."""

    def test_invalid_content_length_400(self, fs_env):
        client = _make_client()
        resp = client.post(
            "/api/input",
            content=b'{"locations":[]}',
            headers={
                "x-ingest-token": TEST_TOKEN,
                "content-type": "application/json",
                "content-length": "not-a-number",
            },
        )
        assert resp.status_code == 400
        assert "invalid content-length" in resp.json()["detail"]

    def test_body_exceeds_limit_no_content_length(self, fs_env, monkeypatch: pytest.MonkeyPatch):
        """Body is too large but no Content-Length header is present."""
        import src.app as app_module

        monkeypatch.setattr(app_module, "MAX_BODY_BYTES", 10)
        client = _make_client()
        resp = client.post(
            "/api/input",
            content=b'{"locations":[{"x":1}]}',
            headers={
                "x-ingest-token": TEST_TOKEN,
                "content-type": "application/json",
                "transfer-encoding": "chunked",
            },
        )
        assert resp.status_code == 413


class TestFsWriteRequestErrorPath:
    """Cover the atomic-write failure/cleanup branch."""

    def test_rename_failure_cleans_up_temp(self, fs_env, tmp_data_dir: Path):
        from src.app import fs_write_request

        payload = _valid_payload()
        with patch("os.rename", side_effect=OSError("disk full")):
            with pytest.raises(OSError, match="disk full"):
                fs_write_request(payload)
        # Temp file should be cleaned up
        req_dir = tmp_data_dir / "requests"
        assert list(req_dir.glob("*.tmp")) == []

    def test_cleanup_failure_still_raises(self, fs_env, tmp_data_dir: Path):
        """Even if os.unlink fails during cleanup, the original error propagates."""
        from src.app import fs_write_request

        payload = _valid_payload()
        with patch("os.rename", side_effect=OSError("disk full")):
            with patch("os.unlink", side_effect=OSError("permission denied")):
                with pytest.raises(OSError, match="disk full"):
                    fs_write_request(payload)


class TestLifespan:
    def test_missing_token_raises(self, monkeypatch: pytest.MonkeyPatch):
        import src.app as app_module

        monkeypatch.setattr(app_module, "TOKEN", None)
        monkeypatch.setattr(app_module, "STORAGE_BACKEND", "filesystem")
        monkeypatch.setattr(app_module, "LOG_DIR", Path(tempfile.mkdtemp()))
        from src.app import app

        with pytest.raises(RuntimeError, match="INGEST_TOKEN"):
            with TestClient(app):
                pass

    def test_startup_with_debug(self, fs_env_debug, tmp_data_dir: Path):
        """Lifespan runs log_config and startup_write_check when DEBUG=1."""
        from src.app import app

        with TestClient(app):
            pass  # lifespan runs automatically

    def test_startup_without_debug(self, fs_env, tmp_data_dir: Path):
        """Lifespan runs startup_write_check but skips log_config when DEBUG=0."""
        from src.app import app

        with TestClient(app):
            pass
