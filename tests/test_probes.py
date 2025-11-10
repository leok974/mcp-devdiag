"""Tests for diagnostic probes - HTTP-only and browser modes."""

import pytest
from mcp_devdiag.probes.adapters import HttpDriver, get_driver
from mcp_devdiag.probes import csp_headers, dom_overlays
from mcp_devdiag.probes.fixes import get_fixes, get_all_fixes


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, status_code=200, headers=None):
        self.status_code = status_code
        self.headers = headers or {}


class MockHttpClient:
    """Mock HTTP client for testing."""

    def __init__(self, response):
        self._response = response

    async def get(self, url, **kwargs):
        return self._response

    async def aclose(self):
        pass


@pytest.mark.asyncio
async def test_http_driver_basic():
    """Test HTTP driver navigation and response."""
    mock_resp = MockResponse(
        status_code=200,
        headers={"content-type": "text/html"},
    )
    client = MockHttpClient(mock_resp)
    driver = HttpDriver(client)

    await driver.goto("https://example.com")
    resp = await driver.get_response()

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/html"
    assert driver.name == "http"


@pytest.mark.asyncio
async def test_http_driver_no_js():
    """Test HTTP driver raises error on JS evaluation."""
    mock_resp = MockResponse()
    client = MockHttpClient(mock_resp)
    driver = HttpDriver(client)

    await driver.goto("https://example.com")

    with pytest.raises(NotImplementedError, match="JavaScript evaluation"):
        await driver.eval_js("console.log('test')")


@pytest.mark.asyncio
async def test_http_driver_no_console():
    """Test HTTP driver returns empty console logs."""
    mock_resp = MockResponse()
    client = MockHttpClient(mock_resp)
    driver = HttpDriver(client)

    await driver.goto("https://example.com")
    logs = await driver.get_console()

    assert logs == []


@pytest.mark.asyncio
async def test_csp_headers_probe_http_mode():
    """Test CSP headers probe in HTTP-only mode."""
    mock_resp = MockResponse(
        status_code=200,
        headers={
            "content-security-policy": "frame-ancestors 'self' https://*.example.com",
            "x-frame-options": "SAMEORIGIN",
        },
    )
    client = MockHttpClient(mock_resp)
    driver = HttpDriver(client)

    cfg = {
        "must_include": [
            {"directive": "frame-ancestors", "any_of": ["'self'", "https://*.example.com"]}
        ],
        "forbidden_xfo": ["DENY"],
    }

    result = await csp_headers.run(driver, "https://example.com", cfg)

    # Should pass - CSP is correct and XFO is not DENY
    assert result["problems"] == []
    assert result["evidence"]["status"] == 200
    assert "frame-ancestors" in result["evidence"]["csp"]


@pytest.mark.asyncio
async def test_csp_headers_probe_missing_directive():
    """Test CSP headers probe detects missing frame-ancestors."""
    mock_resp = MockResponse(
        status_code=200,
        headers={
            "content-security-policy": "default-src 'self'",
        },
    )
    client = MockHttpClient(mock_resp)
    driver = HttpDriver(client)

    cfg = {
        "must_include": [{"directive": "frame-ancestors", "any_of": ["'self'"]}],
        "forbidden_xfo": ["DENY"],
    }

    result = await csp_headers.run(driver, "https://example.com", cfg)

    assert "IFRAME_FRAME_ANCESTORS_BLOCKED" in result["problems"]
    assert len(result["remediation"]) > 0


@pytest.mark.asyncio
async def test_csp_headers_probe_forbidden_xfo():
    """Test CSP headers probe detects forbidden X-Frame-Options."""
    mock_resp = MockResponse(
        status_code=200,
        headers={
            "x-frame-options": "DENY",
        },
    )
    client = MockHttpClient(mock_resp)
    driver = HttpDriver(client)

    cfg = {
        "must_include": [],
        "forbidden_xfo": ["DENY"],
    }

    result = await csp_headers.run(driver, "https://example.com", cfg)

    assert "IFRAME_FRAME_ANCESTORS_BLOCKED" in result["problems"]
    assert any("X-Frame-Options" in r for r in result["remediation"])


@pytest.mark.asyncio
async def test_dom_overlays_probe_http_mode():
    """Test DOM overlays probe degrades gracefully in HTTP mode."""
    mock_resp = MockResponse()
    client = MockHttpClient(mock_resp)
    driver = HttpDriver(client)

    cfg = {
        "overlay_min_width_pct": 0.85,
        "overlay_min_height_pct": 0.5,
    }

    result = await dom_overlays.run(driver, "https://example.com", cfg)

    # HTTP mode cannot detect DOM, should return empty problems
    assert result["problems"] == []
    assert "note" in result["evidence"]
    assert "http-only" in result["evidence"]["note"]


def test_fixes_mapping():
    """Test remediation fixes mapping."""
    # Test known problem code
    fixes = get_fixes("IFRAME_FRAME_ANCESTORS_BLOCKED")
    assert len(fixes) > 0
    assert any("frame-ancestors" in f.lower() for f in fixes)

    # Test unknown problem code
    unknown_fixes = get_fixes("UNKNOWN_PROBLEM")
    assert len(unknown_fixes) == 1
    assert "No specific remediation" in unknown_fixes[0]


def test_get_all_fixes():
    """Test batch remediation retrieval."""
    problems = ["IFRAME_FRAME_ANCESTORS_BLOCKED", "OVERLAY_VIEWPORT_COVER"]
    all_fixes = get_all_fixes(problems)

    assert len(all_fixes) == 2
    assert "IFRAME_FRAME_ANCESTORS_BLOCKED" in all_fixes
    assert "OVERLAY_VIEWPORT_COVER" in all_fixes
    assert all(isinstance(fixes, list) for fixes in all_fixes.values())


@pytest.mark.asyncio
async def test_driver_factory_http():
    """Test driver factory returns HTTP driver when no browser available."""

    def client_factory():
        return MockHttpClient(MockResponse())

    driver = await get_driver("http", client_factory, playwright_factory=None)

    assert driver.name == "http"
    assert isinstance(driver, HttpDriver)


@pytest.mark.asyncio
async def test_driver_factory_auto_degrades():
    """Test driver factory degrades to HTTP when playwright unavailable."""

    def client_factory():
        return MockHttpClient(MockResponse())

    # Request playwright but no factory provided
    driver = await get_driver("playwright", client_factory, playwright_factory=None)

    # Should gracefully degrade to HTTP
    assert driver.name == "http"
    assert isinstance(driver, HttpDriver)
