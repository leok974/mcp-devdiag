# mcp_devdiag/probes/dom_overlays.py
"""Detect DOM overlays that may block embedded content."""

from typing import Any
from .types import ProbeResult
from .score import get_severity

# JavaScript to detect viewport-covering elements and shadow DOM hosts
OVERLAY_DETECTION_JS = r"""
(() => {
  const covers = [...document.querySelectorAll('body *')].filter(el => {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const w = r.width, h = r.height;
    const okPos = cs.position === 'fixed' || cs.position === 'absolute';
    const okVis = cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) > 0;
    const vw = window.innerWidth, vh = window.innerHeight;
    return okPos && okVis && w >= vw * OVERLAY_W && h >= vh * OVERLAY_H;
  }).map(el => {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(),
      id: el.id || null,
      cls: el.className || null,
      z: cs.zIndex,
      bg: cs.backgroundColor,
      w: Math.round(r.width),
      h: Math.round(r.height),
      pointerEvents: cs.pointerEvents
    };
  });

  const shadowHosts = [...document.querySelectorAll('*')]
    .filter(el => el.shadowRoot)
    .map(el => ({
      tag: el.tagName.toLowerCase(),
      id: el.id || null,
      cls: el.className || null,
      mode: el.shadowRoot.mode
    }));

  return { covers, shadowHosts };
})();
"""


async def run(driver: Any, url: str, cfg: dict[str, Any]) -> ProbeResult:
    """
    Detect DOM overlays and shadow DOM that may interfere with embeds.

    Args:
        driver: Driver instance (HTTP or browser)
        url: Target URL to probe
        cfg: Configuration dict with overlay thresholds

    Returns:
        ProbeResult with problems, evidence, and remediation
    """
    problems: list[str] = []
    remediation: list[str] = []

    await driver.goto(url)

    # HTTP-only mode cannot detect runtime DOM
    if driver.name == "http":
        return ProbeResult(
            probe="dom_overlays",
            problems=[],
            evidence={"note": "http-only; no DOM runtime available"},
            remediation=[],
            severity="info",
        )

    # Get thresholds from config
    min_width = cfg.get("overlay_min_width_pct", 0.85)
    min_height = cfg.get("overlay_min_height_pct", 0.5)

    # Inject thresholds into JS
    js = OVERLAY_DETECTION_JS.replace("OVERLAY_W", str(min_width)).replace(
        "OVERLAY_H", str(min_height)
    )

    # Execute detection
    evidence = await driver.eval_js(js)

    # Analyze results
    if evidence.get("covers"):
        problems.append("OVERLAY_VIEWPORT_COVER")
        remediation.extend(
            [
                "Ensure global overlays start hidden/inert; reveal only when needed.",
                "Gate overlays behind ready states; use pointer-events:none until active.",
                "Check z-index stacking context to prevent unintended blocking.",
            ]
        )

    if evidence.get("shadowHosts"):
        problems.append("OVERLAY_SHADOW_BLOCKING")
        remediation.extend(
            [
                "Shadow hosts should default transparent/inert; reveal on ready signal.",
                "Use 'open' mode for shadow DOM to allow external inspection.",
            ]
        )

    return ProbeResult(
        probe="dom_overlays",
        problems=problems,
        remediation=remediation,
        evidence=evidence,
        severity=get_severity(problems),
    )
