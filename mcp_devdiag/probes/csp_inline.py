# mcp_devdiag/probes/csp_inline.py
"""Detect CSP inline script violations."""

from typing import Any


async def run(driver: Any, url: str, _cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Detect Content Security Policy violations for inline scripts.

    Args:
        driver: Driver instance (requires browser for console errors)
        url: Target URL to probe
        _cfg: Configuration (currently unused)

    Returns:
        Dict with problems, evidence, and remediation
    """
    problems: list[str] = []
    remediation: list[str] = []

    await driver.goto(url)

    # HTTP-only mode cannot detect runtime CSP violations
    if driver.name == "http":
        return {
            "problems": [],
            "evidence": {"note": "http-only; use headers scan for CSP"},
            "remediation": [],
        }

    # Get console logs and filter for CSP violations
    console_logs = await driver.get_console()
    csp_errors = [
        msg
        for msg in console_logs
        if "Content Security Policy" in msg
        and ("inline script" in msg or "inline style" in msg or "eval" in msg)
    ]

    if not csp_errors:
        return {
            "problems": [],
            "evidence": {"errors": [], "total_logs": len(console_logs)},
            "remediation": [],
        }

    # Found CSP violations
    problems.append("CSP_INLINE_BLOCKED")
    remediation.extend(
        [
            "Move inline JS to external file or add nonce-based CSP (`script-src 'nonce-$nonce'`).",
            "Temporary: add exact SHA-256 hash to `script-src` while removing inline scripts.",
            "For inline styles, use nonce or move to external CSS.",
            "Avoid `eval()` and similar dynamic code execution; refactor to use safer alternatives.",
        ]
    )

    evidence = {
        "errors": csp_errors[:5],  # Limit to first 5 errors
        "total_violations": len(csp_errors),
        "total_logs": len(console_logs),
    }

    return {"problems": problems, "evidence": evidence, "remediation": remediation}
