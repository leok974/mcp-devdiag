# mcp_devdiag/probes/bundle.py
"""Bundle runner that executes multiple diagnostic probes."""

from typing import Any, Optional
from . import dom_overlays, csp_headers, handshake, framework_versions, csp_inline
from .score import score as score_problems

# Probe presets for different use cases
PRESETS = {
    "chat": ["csp_headers", "handshake", "csp_inline"],
    "embed": ["csp_headers", "dom_overlays", "csp_inline"],
    "app": ["csp_headers", "framework_versions", "dom_overlays", "csp_inline"],
    "full": [
        "dom_overlays",
        "csp_headers",
        "handshake",
        "framework_versions",
        "csp_inline",
    ],
}


def _apply_suppressions(problems: list[str], cfg: dict[str, Any]) -> list[str]:
    """
    Filter out suppressed problem codes.

    Args:
        problems: List of problem codes
        cfg: Diag config section with optional 'suppress' list

    Returns:
        Filtered problems excluding suppressed codes
    """
    suppressed_codes = {s["code"] for s in cfg.get("suppress", []) if isinstance(s, dict)}
    return [p for p in problems if p not in suppressed_codes]


async def run_bundle(
    driver: Any, url: str, cfg: dict[str, Any], preset: Optional[str] = None
) -> dict[str, Any]:
    """
    Run a curated set of diagnostic probes.

    Args:
        driver: Driver instance (HTTP or browser)
        url: Target URL to probe
        cfg: Full configuration dict with 'diag' section
        preset: Probe preset ("chat", "embed", "app", "full", or None for "full")

    Returns:
        Dict with aggregated problems, remediation, evidence, and severity score
    """
    results = []
    diag_cfg = cfg.get("diag", {})

    # Determine which probes to run
    preset_name = preset or "full"
    probe_names = PRESETS.get(preset_name, PRESETS["full"])

    # Run selected probes
    if "dom_overlays" in probe_names:
        results.append(
            {
                "name": "dom_overlays",
                "result": await dom_overlays.run(driver, url, diag_cfg),
            }
        )

    if "csp_headers" in probe_names:
        results.append(
            {
                "name": "csp_headers",
                "result": await csp_headers.run(driver, url, diag_cfg.get("csp", {})),
            }
        )

    if "handshake" in probe_names:
        results.append(
            {
                "name": "handshake",
                "result": await handshake.run(driver, url, diag_cfg.get("handshake", {})),
            }
        )

    if "framework_versions" in probe_names:
        results.append(
            {
                "name": "framework_versions",
                "result": await framework_versions.run(driver, url, diag_cfg.get("framework", {})),
            }
        )

    if "csp_inline" in probe_names:
        results.append(
            {"name": "csp_inline", "result": await csp_inline.run(driver, url, diag_cfg)}
        )

    # Aggregate results
    all_problems: set[str] = set()
    all_remediation: set[str] = set()
    evidence = {}

    for item in results:
        probe_name: str = item["name"]  # type: ignore
        probe_result: dict[str, Any] = item["result"]  # type: ignore

        # Collect unique problems
        problems_list = probe_result.get("problems", [])
        if isinstance(problems_list, list):
            all_problems.update(problems_list)

        # Collect unique remediation steps
        remediation_list = probe_result.get("remediation", [])
        if isinstance(remediation_list, list):
            all_remediation.update(remediation_list)

        # Store evidence by probe name
        evidence[probe_name] = probe_result.get("evidence", {})

    problems = sorted(all_problems)

    # Apply suppressions from config
    problems = _apply_suppressions(problems, diag_cfg)

    total_score = score_problems(problems)

    return {
        "problems": problems,
        "remediation": sorted(all_remediation),
        "evidence": evidence,
        "score": total_score,
        "preset": preset_name,
        "probes_run": len(results),
    }
