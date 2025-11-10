# mcp_devdiag/probes/types.py
"""Standardized types for diagnostic probe results."""

from typing import Any, Literal, TypedDict

Severity = Literal["info", "warn", "error", "critical"]


class ProbeResult(TypedDict, total=False):
    """Standard result shape for all diagnostic probes."""

    probe: str  # Probe identifier (e.g., "csp_headers")
    problems: list[str]  # Problem codes detected
    remediation: list[str]  # Fix recommendations
    evidence: dict[str, Any]  # Diagnostic data collected
    severity: Severity  # Default "warn" if not specified
