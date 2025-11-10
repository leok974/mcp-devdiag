# mcp_devdiag/probes/handshake.py
"""Generic embed ready signal detection."""

from typing import Any


async def run(driver: Any, url: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Detect if embedded content sends ready signal via postMessage or console.

    Args:
        driver: Driver instance (requires browser for runtime detection)
        url: Target URL to probe
        cfg: Configuration with message_types and timeout_ms

    Returns:
        Dict with problems, evidence, and remediation
    """
    problems: list[str] = []
    remediation: list[str] = []

    await driver.goto(url)

    # HTTP-only mode cannot detect runtime messages
    if driver.name == "http":
        return {
            "problems": [],
            "evidence": {"note": "http-only; no postMessage visibility"},
            "remediation": [],
        }

    # Get configuration
    message_types = cfg.get("message_types", ["ready"])
    timeout_ms = cfg.get("timeout_ms", 3000)

    # Get console logs (some ready signals appear in console)
    console_logs = await driver.get_console()

    # Check if any expected message type appears in console logs
    ready_found = False
    for message_type in message_types:
        if any(message_type in log for log in console_logs):
            ready_found = True
            break

    if not ready_found:
        problems.append("EMBED_NO_READY_SIGNAL")
        remediation.extend(
            [
                "Post a ready message after mount: `parent.postMessage({type:'embed:ready'}, origin)`",
                f"Expected message types: {', '.join(message_types)}",
                "Ensure message is sent after all critical resources are loaded.",
            ]
        )

    evidence = {
        "console_logs": console_logs[:10],  # Limit to first 10 logs
        "expected_types": message_types,
        "timeout_ms": timeout_ms,
        "ready_found": ready_found,
    }

    return {"problems": problems, "evidence": evidence, "remediation": remediation}
