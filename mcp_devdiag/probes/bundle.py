# mcp_devdiag/probes/bundle.py
"""Bundle runner that executes multiple diagnostic probes."""

from typing import Any
from . import dom_overlays, csp_headers, handshake, framework_versions, csp_inline


async def run_bundle(driver: Any, url: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Run a curated set of diagnostic probes.

    Args:
        driver: Driver instance (HTTP or browser)
        url: Target URL to probe
        cfg: Full configuration dict with 'diag' section

    Returns:
        Dict with aggregated problems, remediation, and evidence from all probes
    """
    results = []
    diag_cfg = cfg.get("diag", {})

    # Run all probes
    results.append(
        {
            "name": "dom_overlays",
            "result": await dom_overlays.run(driver, url, diag_cfg),
        }
    )

    results.append(
        {
            "name": "csp_headers",
            "result": await csp_headers.run(driver, url, diag_cfg.get("csp", {})),
        }
    )

    results.append(
        {
            "name": "handshake",
            "result": await handshake.run(driver, url, diag_cfg.get("handshake", {})),
        }
    )

    results.append(
        {
            "name": "framework_versions",
            "result": await framework_versions.run(driver, url, diag_cfg.get("framework", {})),
        }
    )

    results.append({"name": "csp_inline", "result": await csp_inline.run(driver, url, diag_cfg)})

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

    return {
        "problems": sorted(all_problems),
        "remediation": sorted(all_remediation),
        "evidence": evidence,
        "probes_run": len(results),
    }
