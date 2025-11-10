# mcp_devdiag/probes/score.py
"""Severity scoring for diagnostic problems."""

from .types import Severity

# Weight each problem code by severity (higher = more critical)
WEIGHTS = {
    "IFRAME_FRAME_ANCESTORS_BLOCKED": 10,
    "EMBED_NO_READY_SIGNAL": 8,
    "CSP_INLINE_BLOCKED": 7,
    "OVERLAY_VIEWPORT_COVER": 6,
    "OVERLAY_SHADOW_BLOCKING": 5,
    "FRAMEWORK_VERSION_MISMATCH": 4,
    "PORTAL_ROOT_MISSING": 3,
    "IFRAME_SANDBOX_WEAK": 9,
}


def score(problems: list[str]) -> int:
    """
    Calculate severity score for a list of problem codes.

    Args:
        problems: List of problem codes

    Returns:
        Total severity score (higher = more critical)
    """
    return sum(WEIGHTS.get(p, 1) for p in set(problems))


def get_severity(problems: list[str]) -> Severity:
    """
    Get overall severity level based on problem codes.

    Args:
        problems: List of problem codes

    Returns:
        Severity level: "critical", "error", "warn", or "info"
    """
    if not problems:
        return "info"

    total_score = score(problems)

    if total_score >= 15:
        return "critical"
    elif total_score >= 8:
        return "error"
    elif total_score >= 3:
        return "warn"
    else:
        return "info"
