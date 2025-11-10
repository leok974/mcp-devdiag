# mcp_devdiag/probes/framework_versions.py
"""Auto-detect frontend framework versions from console logs."""

import re
from typing import Any
from .types import ProbeResult
from .score import get_severity


def sniff_framework_logs(logs: list[str], regex_map: dict[str, str]) -> dict[str, str]:
    """
    Detect framework versions from console logs using regex patterns.

    Args:
        logs: List of console log messages
        regex_map: Dict mapping framework names to regex patterns

    Returns:
        Dict mapping detected framework names to matching log lines
    """
    detected = {}
    for framework, pattern in regex_map.items():
        try:
            rx = re.compile(pattern, re.IGNORECASE)
            matching_line = next((log for log in logs if rx.search(log)), None)
            if matching_line:
                detected[framework] = matching_line
        except re.error:
            # Skip invalid regex patterns
            continue
    return detected


async def run(driver: Any, url: str, cfg: dict[str, Any]) -> ProbeResult:
    """
    Auto-detect frontend framework versions (React, Vue, Svelte, etc.).

    Args:
        driver: Driver instance (requires browser for console logs)
        url: Target URL to probe
        cfg: Configuration with detect_console_regex patterns

    Returns:
        ProbeResult with problems, evidence, and remediation
    """
    problems: list[str] = []
    remediation: list[str] = []

    await driver.goto(url)

    # HTTP-only mode cannot detect console logs
    if driver.name == "http":
        return ProbeResult(
            probe="framework_versions",
            problems=[],
            evidence={"note": "http-only; no console logs available"},
            remediation=[],
            severity="info",
        )

    # Get console logs
    console_logs = await driver.get_console()

    # Detect frameworks
    regex_map = cfg.get("detect_console_regex", {})
    detected = sniff_framework_logs(console_logs, regex_map)

    # Check for version mismatches
    # Example: React + react-dom version mismatch
    if "react" in detected:
        react_log = detected["react"]
        # Look for mixed versions (e.g., "react 18.2.0" and "react-dom 18.3.0")
        if "next" in react_log.lower() or "canary" in react_log.lower():
            problems.append("FRAMEWORK_VERSION_MISMATCH")
            remediation.extend(
                [
                    "Pin UI framework runtime & DOM adapters to exact versions.",
                    "Avoid mixing next/canary builds with stable releases.",
                    "Check package.json for version conflicts (react vs react-dom).",
                ]
            )

    # Check for multiple frameworks (can cause conflicts)
    if len(detected) > 1:
        framework_names = ", ".join(detected.keys())
        problems.append("FRAMEWORK_VERSION_MISMATCH")
        remediation.append(
            f"Multiple frameworks detected ({framework_names}); ensure only one framework is active to avoid conflicts."
        )

    evidence = {
        "detected_frameworks": detected,
        "console_logs_count": len(console_logs),
        "regex_patterns": regex_map,
    }

    return ProbeResult(
        probe="framework_versions",
        problems=problems,
        remediation=remediation,
        evidence=evidence,
        severity=get_severity(problems),
    )
