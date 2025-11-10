"""DevDiag MCP tools - production-safe diagnostic endpoints."""

import os
import time
from typing import Any, Dict
import httpx
from mcp_devdiag.config import load_config
from mcp_devdiag.security import authorize, AuthorizationError
from fastmcp import FastMCP

# Load configuration
CFG = load_config()

# Prometheus endpoint from environment
PROM_URL = os.getenv("PROM_URL", "http://prometheus:9090")

# Create FastMCP app for devdiag tools
app = FastMCP("mcp-devdiag-tools")


def _filter_headers(hdrs: httpx.Headers, allowlist: list[str] | None, deny: list[str]) -> dict:
    """Filter headers based on allowlist or denylist."""
    if allowlist:
        allow = {h.lower() for h in allowlist}
        return {k: v for k, v in hdrs.items() if k.lower() in allow}
    denyset = {h.lower() for h in deny}
    return {k: v for k, v in hdrs.items() if k.lower() not in denyset}


@app.tool()
def set_mode(
    mode: str, ttl_seconds: int | None = None, auth_header: str | None = None
) -> Dict[str, Any]:
    """
    Set DevDiag operating mode (requires operator role).

    Args:
        mode: Operating mode (e.g., "dev", "prod:observe", "prod:incident")
        ttl_seconds: Optional TTL for ephemeral mode override
        auth_header: Authorization header (Bearer token)
    """
    try:
        authorize("set_mode", auth_header)
    except AuthorizationError as e:
        return {"ok": False, "error": str(e)}

    # TODO: persist ephemeral override with auto-revert timer
    CFG.mode = mode
    return {"ok": True, "mode": CFG.mode, "ttl": ttl_seconds}


@app.tool()
async def get_metrics(window: str = "15m", auth_header: str | None = None) -> Dict[str, Any]:
    """
    Get aggregated metrics for the specified time window (requires reader role).

    Queries Prometheus for HTTP request rates and latency percentiles.

    Args:
        window: Time window (e.g., "15m", "1h", "24h")
        auth_header: Authorization header (Bearer token)
    """
    try:
        authorize("get_metrics", auth_header)
    except AuthorizationError as e:
        return {"ok": False, "error": str(e)}

    # Query Prometheus for metrics
    query = f'rate(http_server_requests_seconds_count{{job="api"}}[{window}])'
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{PROM_URL}/api/v1/query", params={"query": query})
            prom_data = response.json()

        # Parse Prometheus response for basic rates
        # In production, you'd parse the actual metric data here
        return {
            "ok": True,
            "window": window,
            "rates": {"2xx": 0, "4xx": 0, "5xx": 0},  # TODO: parse from prom_data
            "latency_ms": {"p50": 0, "p90": 0},  # TODO: query latency metrics
            "prom_status": prom_data.get("status", "unknown"),
        }
    except Exception as e:
        # Fallback to stub data if Prometheus is unavailable
        return {
            "ok": True,
            "window": window,
            "rates": {"2xx": 0, "4xx": 0, "5xx": 0},
            "latency_ms": {"p50": 0, "p90": 0},
            "prom_error": str(e),
        }


@app.tool()
def get_error_buckets(window: str = "15m", auth_header: str | None = None) -> Dict[str, Any]:
    """
    Get error signature buckets for the specified time window (requires reader role).

    Args:
        window: Time window (e.g., "15m", "1h", "24h")
        auth_header: Authorization header (Bearer token)
    """
    try:
        authorize("get_metrics", auth_header)
    except AuthorizationError as e:
        return {"ok": False, "error": str(e)}

    # TODO: implement signature bucketing
    return {"window": window, "buckets": []}


@app.tool()
async def get_request_diagnostics(
    url: str,
    method: str = "GET",
    headers_allowlist: list[str] | None = None,
    auth_header: str | None = None,
) -> Dict[str, Any]:
    """
    Probe a URL and return diagnostic information (requires reader role).

    Only URLs matching allow_probes patterns in devdiag.yaml are permitted.

    Args:
        url: URL to probe
        method: HTTP method (default: GET)
        headers_allowlist: Optional list of headers to include in response
        auth_header: Authorization header (Bearer token)
    """
    try:
        authorize("get_request_diagnostics", auth_header)
    except AuthorizationError as e:
        return {"ok": False, "error": str(e)}

    if not CFG.method_url_allowed(method, url):
        return {"ok": False, "error": "probe url not allow-listed"}

    # Perform timed, header-redacted httpx probe
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(
            timeout=5.0, http2=True, verify=True, follow_redirects=False
        ) as client:
            response = await client.request(method.upper(), url)

        ms = round((time.perf_counter() - t0) * 1000)

        # Filter headers based on allowlist or denylist
        deny_headers = CFG.redaction.get("headers_deny", [])
        filtered_headers = _filter_headers(response.headers, headers_allowlist, deny_headers)

        # Extract CORS headers
        cors = {
            k: response.headers.get(k)
            for k in [
                "access-control-allow-origin",
                "access-control-allow-credentials",
                "access-control-allow-methods",
                "access-control-allow-headers",
            ]
            if response.headers.get(k)
        }

        # TLS/HTTP version details (best-effort)
        tls_info = {"http_version": getattr(response, "http_version", "unknown")}

        return {
            "ok": True,
            "url": url,
            "method": method.upper(),
            "status": response.status_code,
            "ms": ms,
            "headers": filtered_headers,
            "cors": cors,
            "tls": tls_info,
        }
    except httpx.TimeoutException:
        ms = round((time.perf_counter() - t0) * 1000)
        return {
            "ok": False,
            "error": "timeout",
            "url": url,
            "method": method.upper(),
            "ms": ms,
        }
    except Exception as e:
        ms = round((time.perf_counter() - t0) * 1000)
        return {
            "ok": False,
            "error": str(e),
            "url": url,
            "method": method.upper(),
            "ms": ms,
        }


@app.tool()
def compare_envs(
    a: str = "staging", b: str = "prod", auth_header: str | None = None
) -> Dict[str, Any]:
    """
    Compare environment configurations between two environments (requires operator role).

    Args:
        a: First environment name
        b: Second environment name
        auth_header: Authorization header (Bearer token)
    """
    try:
        authorize("compare_envs", auth_header)
    except AuthorizationError as e:
        return {"ok": False, "error": str(e)}

    # TODO: load snapshots (e.g., from S3) and diff keys for cors/cookies/origins
    return {"diff": []}


def main():
    """Run the DevDiag tools MCP server."""
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
