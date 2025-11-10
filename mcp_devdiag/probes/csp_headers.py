# mcp_devdiag/probes/csp_headers.py
"""Content Security Policy and X-Frame-Options validation."""

from typing import Any


def parse_csp_directives(csp: str) -> dict[str, str]:
    """
    Parse CSP header into directive dictionary.

    Args:
        csp: Raw CSP header value

    Returns:
        Dict mapping directive names to their values
    """
    directives = {}
    for part in csp.split(";"):
        tokens = part.strip().split(" ", 1)
        if not tokens or not tokens[0]:
            continue
        directive = tokens[0].lower()
        value = tokens[1] if len(tokens) > 1 else ""
        directives[directive] = value
    return directives


async def run(driver: Any, url: str, csp_cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Validate CSP and X-Frame-Options headers for embed compatibility.

    Args:
        driver: Driver instance (HTTP mode recommended)
        url: Target URL to probe
        csp_cfg: CSP configuration with must_include and forbidden_xfo

    Returns:
        Dict with problems, evidence, and remediation
    """
    problems: list[str] = []
    remediation: list[str] = []

    await driver.goto(url)
    resp = await driver.get_response()

    # Extract headers
    csp = resp.headers.get("content-security-policy", "")
    xfo = resp.headers.get("x-frame-options", "")

    directives = parse_csp_directives(csp)

    # Check required CSP directives
    must_include = csp_cfg.get("must_include", [])
    for rule in must_include:
        directive_name = rule.get("directive", "").lower()
        any_of = rule.get("any_of", [])

        if directive_name not in directives:
            problems.append("IFRAME_FRAME_ANCESTORS_BLOCKED")
            remediation.append(
                f"Add `{directive_name}` directive to CSP with appropriate origins (e.g., 'self')."
            )
            break

        # Check if any of the required values are present
        directive_value = directives[directive_name]
        if not any(token in directive_value for token in any_of):
            problems.append("IFRAME_FRAME_ANCESTORS_BLOCKED")
            remediation.append(
                f"Add allowed origins to `{directive_name}` directive (e.g., 'self' or https://your-host)."
            )
            break

    # Check forbidden X-Frame-Options values
    forbidden_xfo = csp_cfg.get("forbidden_xfo", ["deny"])
    if xfo and any(forbidden.lower() in xfo.lower() for forbidden in forbidden_xfo):
        problems.append("IFRAME_FRAME_ANCESTORS_BLOCKED")
        remediation.append(
            "Remove `X-Frame-Options: DENY` for embedded routes; prefer CSP `frame-ancestors`."
        )

    evidence = {
        "status": resp.status_code,
        "csp": csp or None,
        "csp_directives": directives if directives else None,
        "xfo": xfo or None,
    }

    return {"problems": problems, "evidence": evidence, "remediation": remediation}
