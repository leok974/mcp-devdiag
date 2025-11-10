# mcp_devdiag/probes/fixes.py
"""Generic remediation mapping for diagnostic problems."""

# Vendor-neutral problem codes with portable fix recipes
FIXES = {
    "IFRAME_FRAME_ANCESTORS_BLOCKED": [
        "Serve embedded routes with `Content-Security-Policy: frame-ancestors 'self' https://your-host`.",
        "Remove/avoid `X-Frame-Options: DENY`; prefer CSP.",
        "Verify CSP includes your parent domain in frame-ancestors directive.",
    ],
    "IFRAME_SANDBOX_WEAK": [
        'Remove `allow-same-origin` from iframe sandbox. Keep minimal: `sandbox="allow-scripts allow-popups"` if needed.',
        "Avoid combining allow-same-origin with allow-scripts (security risk).",
        "Test iframe functionality with strictest sandbox first, then relax as needed.",
    ],
    "EMBED_NO_READY_SIGNAL": [
        "After mount, call `parent.postMessage({type:'<embed>:ready'}, origin)`.",
        "Ensure message is sent after all critical resources are loaded.",
        "Listen for parent's acknowledgment to confirm two-way communication.",
    ],
    "OVERLAY_VIEWPORT_COVER": [
        "Default overlays to hidden/inert; toggle with explicit state; avoid full-viewport blocks on load.",
        "Use `pointer-events:none` until overlay is intentionally activated.",
        "Check z-index stacking context to prevent unintended blocking.",
    ],
    "OVERLAY_SHADOW_BLOCKING": [
        "Shadow hosts: start `opacity:0; pointer-events:none; background:transparent`; enable on ready.",
        "Use 'open' mode for shadow DOM to allow external inspection.",
        "Defer shadow root attachment until after critical rendering.",
    ],
    "PORTAL_ROOT_MISSING": [
        "Ensure a portal container exists (e.g., `#__PORTAL_ROOT__`) or create one programmatically at boot.",
        'Add portal root to index.html: `<div id="__PORTAL_ROOT__"></div>`',
        "For framework portals (React, Vue), ensure createPortal target exists before rendering.",
    ],
    "FRAMEWORK_VERSION_MISMATCH": [
        "Pin UI framework + DOM adapter to exact matching versions; avoid mixing next/canary builds.",
        "Check package.json for version conflicts (e.g., react vs react-dom).",
        "Use npm list or yarn why to identify duplicate framework installations.",
    ],
    "CSP_INLINE_BLOCKED": [
        "Move inline JS to external files or use nonce-based CSP; only temporarily allow hashed inline scripts.",
        "Add nonce to script tags: `<script nonce=\"$nonce\">` and CSP: `script-src 'nonce-$nonce'`.",
        "For build tools, configure to extract inline scripts automatically.",
    ],
}


def get_fixes(problem_code: str) -> list[str]:
    """
    Get remediation steps for a problem code.

    Args:
        problem_code: Diagnostic problem code

    Returns:
        List of remediation steps, or generic advice if code unknown
    """
    return FIXES.get(
        problem_code,
        ["No specific remediation available for this problem code."],
    )


def get_all_fixes(problem_codes: list[str]) -> dict[str, list[str]]:
    """
    Get remediation for multiple problem codes.

    Args:
        problem_codes: List of diagnostic problem codes

    Returns:
        Dict mapping problem codes to remediation steps
    """
    return {code: get_fixes(code) for code in problem_codes}


def fixes_for(codes: list[str]) -> dict[str, list[str]]:
    """
    Get fixes for specified problem codes (alias for get_all_fixes).

    Args:
        codes: List of problem codes

    Returns:
        Dict mapping codes to fix recipes
    """
    return {c: FIXES[c] for c in codes if c in FIXES}
