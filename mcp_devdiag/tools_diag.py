# mcp_devdiag/tools_diag.py
"""MCP tool handlers for generalized diagnostic probes."""

from typing import Any, Optional, cast
import httpx
from fastmcp import FastMCP

from .config import load_config
from .limits import guard
from .probes.adapters import get_driver
from .probes import (
    dom_overlays,
    csp_headers,
    handshake,
    framework_versions,
    csp_inline,
    bundle,
)
from .probes.fixes import fixes_for

# Initialize MCP app
mcp = FastMCP("DevDiag Probes")

# Load configuration
CONFIG = load_config()


def http_client_factory():
    """Create HTTP client for driver."""
    return httpx.AsyncClient()


def _assert_allowed(url: str) -> None:
    """
    Validate URL against allowlist.

    Args:
        url: URL to validate

    Raises:
        ValueError: If URL is not in allowlist
    """
    if not CONFIG.method_url_allowed("GET", url):
        raise ValueError(f"URL not allow-listed: {url}")


@mcp.tool()
async def diag_bundle(url: str, driver: Optional[str] = None, preset: Optional[str] = None) -> dict:
    """
    Run curated set of diagnostic probes based on presets.

    Args:
        url: Target URL to probe
        driver: Driver type ("http", "playwright", "puppeteer", "selenium") or None for auto-detect
        preset: Probe preset ("chat", "embed", "app", "full", or None for "full")

    Returns:
        Aggregated problems, remediation, evidence, and severity score
    """
    _assert_allowed(url)
    guard(CONFIG.tenant, "diag_bundle")
    drv = await get_driver(driver, http_client_factory)
    try:
        return await bundle.run_bundle(drv, url, {"diag": CONFIG.__dict__.get("diag", {})}, preset)
    finally:
        await drv.dispose()


@mcp.tool()
async def diag_quickcheck(url: str) -> dict:
    """
    Fast HTTP-only CSP and iframe compatibility check (CI-safe).

    Args:
        url: Target URL to probe

    Returns:
        Probe results using "chat" preset (CSP headers, handshake)
    """
    _assert_allowed(url)
    guard(CONFIG.tenant, "diag_quickcheck")
    drv = await get_driver("http", http_client_factory)
    try:
        return await bundle.run_bundle(drv, url, {"diag": CONFIG.__dict__.get("diag", {})}, "chat")
    finally:
        await drv.dispose()


@mcp.tool()
async def diag_remediation(problems: list[str]) -> dict:
    """
    Get remediation steps for specific problem codes.

    Args:
        problems: List of problem codes

    Returns:
        Dict mapping problem codes to fix recipes
    """
    return fixes_for(problems)


@mcp.tool()
async def diag_probe_dom_overlays(url: str, driver: Optional[str] = None) -> dict[str, Any]:
    """
    Detect DOM overlays that may block embedded content.

    Args:
        url: Target URL to probe
        driver: Driver type or None for auto-detect (requires browser for DOM inspection)

    Returns:
        Problems, evidence, and remediation for overlay issues
    """
    drv = await get_driver(driver, http_client_factory)
    try:
        return cast(
            dict[str, Any], await dom_overlays.run(drv, url, CONFIG.__dict__.get("diag", {}))
        )
    finally:
        await drv.dispose()


@mcp.tool()
async def diag_probe_csp_headers(url: str) -> dict[str, Any]:
    """
    Validate Content Security Policy and X-Frame-Options headers.

    Args:
        url: Target URL to probe

    Returns:
        Problems, evidence, and remediation for CSP/XFO issues
    """
    drv = await get_driver("http", http_client_factory)
    try:
        csp_cfg = CONFIG.__dict__.get("diag", {}).get("csp", {})
        return cast(dict[str, Any], await csp_headers.run(drv, url, csp_cfg))
    finally:
        await drv.dispose()


@mcp.tool()
async def diag_probe_chat_handshake(url: str, driver: Optional[str] = None) -> dict:
    """
    Detect generic embed/iframe ready handshake signals.

    Args:
        url: Target URL to probe
        driver: Driver type or None for auto-detect (requires browser for postMessage)

    Returns:
        Problems, evidence, and remediation for handshake issues
    """
    _assert_allowed(url)
    drv = await get_driver(driver, http_client_factory)
    try:
        handshake_cfg = CONFIG.__dict__.get("diag", {}).get("handshake", {})
        return cast(dict[str, Any], await handshake.run(drv, url, handshake_cfg))
    finally:
        await drv.dispose()


@mcp.tool()
async def diag_probe_framework_versions(url: str, driver: Optional[str] = None) -> dict:
    """
    Auto-detect React/Vue/Svelte/Angular framework versions from console.

    Args:
        url: Target URL to probe
        driver: Driver type or None for auto-detect (requires browser for console logs)

    Returns:
        Problems, evidence, and remediation for framework version issues
    """
    _assert_allowed(url)
    drv = await get_driver(driver, http_client_factory)
    try:
        framework_cfg = CONFIG.__dict__.get("diag", {}).get("framework", {})
        return cast(dict[str, Any], await framework_versions.run(drv, url, framework_cfg))
    finally:
        await drv.dispose()


@mcp.tool()
async def diag_probe_csp_inline(url: str, driver: Optional[str] = None) -> dict[str, Any]:
    """
    Check for inline script CSP violations.

    Args:
        url: Target URL to probe
        driver: Driver type or None for auto-detect (requires browser for inline checks)

    Returns:
        Problems, evidence, and remediation for CSP inline issues
    """
    _assert_allowed(url)
    drv = await get_driver(driver, http_client_factory)
    try:
        return cast(dict[str, Any], await csp_inline.run(drv, url, CONFIG.__dict__.get("diag", {})))
    finally:
        await drv.dispose()


@mcp.tool()
async def diag_probe_iframes(url: str, driver: Optional[str] = None) -> dict:
    """
    Validate iframe sandbox and permissions.

    Args:
        url: Target URL to probe
        driver: Driver type or None for auto-detect

    Returns:
        Problems, evidence, and remediation for iframe issues
    """
    _assert_allowed(url)
    # TODO: Implement iframe-specific probe
    # For now, delegate to bundle which includes CSP checks
    drv = await get_driver(driver, http_client_factory)
    try:
        return {
            "problems": [],
            "evidence": {"note": "iframe probe not yet implemented; use diag_bundle"},
            "remediation": [],
        }
    finally:
        await drv.dispose()


@mcp.tool()
async def diag_probe_portal_root(url: str, driver: Optional[str] = None) -> dict:
    """
    Check for portal root container existence.

    Args:
        url: Target URL to probe
        driver: Driver type or None for auto-detect (requires browser for DOM inspection)

    Returns:
        Problems, evidence, and remediation for portal root issues
    """
    _assert_allowed(url)
    drv = await get_driver(driver, http_client_factory)
    try:
        if drv.name == "http":
            return {
                "problems": [],
                "evidence": {"note": "http-only; portal detection requires browser"},
                "remediation": [],
            }

        portal_roots = CONFIG.__dict__.get("diag", {}).get("portal_roots", [])
        js = f"""
        (() => {{
            const selectors = {portal_roots};
            const found = selectors.map(sel => {{
                const el = document.querySelector(sel);
                return {{ selector: sel, exists: !!el }};
            }});
            return found;
        }})();
        """

        evidence = await drv.eval_js(js)
        problems = []
        remediation = []

        if not any(item["exists"] for item in evidence):
            problems.append("PORTAL_ROOT_MISSING")
            remediation.extend(
                [
                    f"Ensure a portal container exists: {', '.join(portal_roots)}",
                    "Create portal root programmatically at boot if missing.",
                ]
            )

        return {"problems": problems, "evidence": evidence, "remediation": remediation}
    finally:
        await drv.dispose()


@mcp.tool()
def get_probe_result_schema() -> dict[str, Any]:
    """
    Get JSON schema for ProbeResult type.

    Returns:
        JSON schema for probe result structure
    """
    import json
    import os

    schema_path = os.path.join(os.path.dirname(__file__), "schemas", "probe_result.json")
    with open(schema_path, "r") as f:
        return json.load(f)


@mcp.tool()
async def diag_status_plus(
    base_url: str, preset: str = "app", driver: Optional[str] = None
) -> dict[str, Any]:
    """
    Admin-grade status endpoint with scoring and fix recommendations.

    Args:
        base_url: Target base URL to diagnose
        preset: Probe preset ("chat", "embed", "app", "full")
        driver: Driver type or None for auto-detect

    Returns:
        Status with ok flag, score, problems, fixes, and evidence
    """
    _assert_allowed(base_url)
    guard(CONFIG.tenant, "diag_status_plus")

    drv = await get_driver(driver, http_client_factory)
    try:
        result = await bundle.run_bundle(
            drv, base_url, {"diag": CONFIG.__dict__.get("diag", {})}, preset
        )

        return {
            "ok": not result.get("problems", []),
            "score": result.get("score", 0),
            "severity": result.get("severity", "info"),
            "problems": result.get("problems", []),
            "fixes": fixes_for(result.get("problems", [])),
            "evidence": result.get("evidence", {}),
        }
    finally:
        await drv.dispose()
