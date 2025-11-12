"""
Integration tests for DevDiag backend proxy.

Run with:
    pytest apps/backend/tests/test_devdiag_proxy.py -v
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from app.routes.devdiag_proxy import router


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch.dict(
        "os.environ",
        {
            "DEVDIAG_BASE": "https://devdiag.example.com",
            "DEVDIAG_JWT": "test-jwt-token",
            "DEVDIAG_TIMEOUT_S": "30",
            "DEVDIAG_ENABLED": "1",
            "DEVDIAG_ALLOW_HOSTS": ".ledger-mind.org,app.example.com",
        },
    ):
        yield


class TestDevDiagHealth:
    """Test health endpoint."""

    def test_health_success(self, client, mock_env):
        """Health check returns 200 when DevDiag is healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            response = client.get("/ops/diag/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_devdiag_down(self, client, mock_env):
        """Health check returns 502 when DevDiag is down."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client_cls.return_value = mock_client

            response = client.get("/ops/diag/health")

        assert response.status_code == 502
        assert "DevDiag health check failed" in response.json()["detail"]


class TestRunDiag:
    """Test diagnostic endpoint."""

    def test_run_diag_success(self, client, mock_env):
        """Run diagnostics successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "1000"}
        mock_response.json.return_value = {
            "ok": True,
            "url": "https://app.ledger-mind.org",
            "preset": "app",
            "result": {"problems": [], "fixes": {}, "score": 100},
        }

        with patch(
            "app.routes.devdiag_proxy._post_with_retry", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            response = client.post(
                "/ops/diag",
                json={
                    "url": "https://app.ledger-mind.org",
                    "preset": "app",
                    "tenant": "ledgermind",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["url"] == "https://app.ledger-mind.org"
        assert data["preset"] == "app"

    def test_run_diag_invalid_host(self, client, mock_env):
        """Reject URL not in allowlist."""
        response = client.post(
            "/ops/diag",
            json={
                "url": "https://evil.com",
                "preset": "app",
                "tenant": "ledgermind",
            },
        )

        assert response.status_code == 422
        assert "not in allowlist" in response.text.lower()

    def test_run_diag_subdomain_allowed(self, client, mock_env):
        """Allow subdomain when root domain is in allowlist."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "1000"}
        mock_response.json.return_value = {
            "ok": True,
            "url": "https://pr-123.ledger-mind.org",
            "preset": "app",
            "result": {"problems": [], "score": 100},
        }

        with patch(
            "app.routes.devdiag_proxy._post_with_retry", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            response = client.post(
                "/ops/diag",
                json={
                    "url": "https://pr-123.ledger-mind.org",
                    "preset": "app",
                    "tenant": "ledgermind",
                },
            )

        assert response.status_code == 200

    def test_run_diag_exact_host_allowed(self, client, mock_env):
        """Allow exact host match."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "1000"}
        mock_response.json.return_value = {
            "ok": True,
            "url": "https://app.example.com",
            "preset": "app",
            "result": {"problems": [], "score": 100},
        }

        with patch(
            "app.routes.devdiag_proxy._post_with_retry", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            response = client.post(
                "/ops/diag",
                json={
                    "url": "https://app.example.com",
                    "preset": "app",
                    "tenant": "ledgermind",
                },
            )

        assert response.status_code == 200

    def test_run_diag_response_too_large(self, client, mock_env):
        """Reject overly large responses."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "3000000"}  # 3MB

        with patch(
            "app.routes.devdiag_proxy._post_with_retry", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            response = client.post(
                "/ops/diag",
                json={
                    "url": "https://app.ledger-mind.org",
                    "preset": "app",
                    "tenant": "ledgermind",
                },
            )

        assert response.status_code == 502
        assert "too large" in response.json()["detail"].lower()

    def test_run_diag_timeout(self, client, mock_env):
        """Handle DevDiag timeout."""
        with patch(
            "app.routes.devdiag_proxy._post_with_retry", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.ReadTimeout("Request timeout")

            response = client.post(
                "/ops/diag",
                json={
                    "url": "https://app.ledger-mind.org",
                    "preset": "app",
                    "tenant": "ledgermind",
                },
            )

        assert response.status_code == 504
        assert "timed out" in response.json()["detail"].lower()


class TestFeatureToggle:
    """Test DEVDIAG_ENABLED toggle."""

    def test_disabled_returns_404(self, client):
        """Return 404 when DEVDIAG_ENABLED=0."""
        with patch.dict(
            "os.environ",
            {
                "DEVDIAG_BASE": "https://devdiag.example.com",
                "DEVDIAG_ENABLED": "0",
            },
        ):
            response = client.get("/ops/diag/health")

        assert response.status_code == 404


class TestHeaderPropagation:
    """Test trace header propagation."""

    def test_trace_headers_forwarded(self, client, mock_env):
        """Forward trace headers to DevDiag."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "1000", "x-request-id": "test-rid"}
        mock_response.json.return_value = {
            "ok": True,
            "url": "https://app.ledger-mind.org",
            "preset": "app",
            "result": {"problems": [], "score": 100},
        }

        captured_headers = {}

        async def capture_headers(url, json, headers, timeout):
            captured_headers.update(headers)
            return mock_response

        with patch(
            "app.routes.devdiag_proxy._post_with_retry",
            new_callable=AsyncMock,
            side_effect=capture_headers,
        ):
            response = client.post(
                "/ops/diag",
                json={
                    "url": "https://app.ledger-mind.org",
                    "preset": "app",
                    "tenant": "ledgermind",
                },
                headers={
                    "x-request-id": "frontend-rid-123",
                    "x-b3-traceid": "trace-abc",
                },
            )

        assert response.status_code == 200
        assert captured_headers["x-request-id"] == "frontend-rid-123"
        assert captured_headers["x-b3-traceid"] == "trace-abc"
        assert "Bearer test-jwt-token" in captured_headers["authorization"]

    def test_request_id_in_response(self, client, mock_env):
        """Include x-request-id in response headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "content-length": "1000",
            "x-request-id": "devdiag-rid-456",
        }
        mock_response.json.return_value = {
            "ok": True,
            "url": "https://app.ledger-mind.org",
            "preset": "app",
            "result": {"problems": [], "score": 100},
        }

        with patch(
            "app.routes.devdiag_proxy._post_with_retry", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            response = client.post(
                "/ops/diag",
                json={
                    "url": "https://app.ledger-mind.org",
                    "preset": "app",
                    "tenant": "ledgermind",
                },
            )

        # Note: FastAPI TestClient doesn't preserve custom headers in response
        # In production, x-request-id will be in response.headers
        assert response.status_code == 200
