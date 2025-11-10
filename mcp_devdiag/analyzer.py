"""Log analysis and diagnostic heuristics."""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json
import re
from .schema import Problem, StatusResponse, Context

LOG_DIR = Path(".tasteos_logs")
BACKEND_LOG = LOG_DIR / "backend.log"
FRONTEND_LOG = LOG_DIR / "frontend.log"
ENV_JSON = LOG_DIR / "env.json"
NETWORK_LOG = LOG_DIR / "network.jsonl"

_FAILED_FETCH = re.compile(r"TypeError: Failed to fetch", re.I)
_HTTP_ERR = re.compile(r"\b(401|403|500|502|503|504)\b")
_CORS_ERR = re.compile(r"CORS|Access-Control-Allow-Origin", re.I)


def load_env() -> Dict[str, Any]:
    """Load environment snapshot from env.json."""
    if ENV_JSON.exists():
        try:
            return json.loads(ENV_JSON.read_text())
        except Exception:
            return {}
    return {}


def detect_problems(env: Dict[str, Any], be_lines: List[str], fe_lines: List[str]) -> List[Problem]:
    """
    Analyze logs and environment to detect common development issues.

    Args:
        env: Environment snapshot from env.json
        be_lines: Backend log lines
        fe_lines: Frontend log lines

    Returns:
        List of detected problems with suggested fixes
    """
    problems: List[Problem] = []

    frontend_origin = env.get("frontend_origin")
    backend_origin = env.get("backend_origin")
    # allow_origins unused for now but may be used for diagnostics later
    _ = env.get("cors_allow_origins") or env.get("CORS allow_origins")

    cookie = env.get("cookie") or env.get("cookie_snapshot")
    cookie_domain = env.get("cookie_domain")
    cookie_secure = env.get("cookie_secure")
    cookie_samesite = env.get("cookie_samesite")

    # Optional promotion of warnings to errors (via env.json)
    error_on = set(env.get("devdiag_error_on", []))

    vite_api = env.get("VITE_API_BASE")
    # last_failed_url unused for now but may be used for diagnostics later
    _ = env.get("last_failed_url")
    last_error = env.get("last_error")

    # Origin mismatch detection
    if frontend_origin and backend_origin:
        # Compare hostnames only (not ports) - e.g., localhost vs 127.0.0.1
        fe_host = frontend_origin.split("//")[-1].split(":")[0]
        be_host = backend_origin.split("//")[-1].split(":")[0]
        if fe_host != be_host:
            problems.append(
                Problem(
                    severity="warn",
                    code="ORIGIN_MISMATCH",
                    message=f"Frontend origin {frontend_origin} differs from backend {backend_origin}.",
                    fix=[
                        "Ensure CORS allow_origins includes frontend origin",
                        "If using cookies, set allow_credentials=True",
                        "Align dev URLs (localhost vs 127.0.0.1)",
                    ],
                )
            )

    # Failed to fetch → likely CORS/network/cookie
    fe_text = "\n".join(fe_lines[-400:])
    if _FAILED_FETCH.search(fe_text) or (last_error and "Failed to fetch" in last_error):
        problems.append(
            Problem(
                severity="error",
                code="FAILED_TO_FETCH",
                message="Frontend reports 'TypeError: Failed to fetch'.",
                fix=[
                    "Confirm backend is up and reachable",
                    "Add exact frontend origin to CORS",
                    "Enable allow_credentials=True if using cookies",
                    "Use same host form (localhost vs 127.0.0.1)",
                ],
            )
        )

    # CORS specifically
    if _CORS_ERR.search(fe_text):
        problems.append(
            Problem(
                severity="error",
                code="CORS_BLOCK",
                message="CORS appears to be blocking requests.",
                fix=[
                    "Set CORSMiddleware allow_origins=[frontend_origin]",
                    "Set allow_credentials=True when using cookies",
                    "Expose/allow headers as needed",
                ],
            )
        )

    # Cookie domain / SameSite problems
    # NOTE: Previously gated on 'cookie is not None'. Now evaluate if we have ANY cookie-related hints.
    has_cookie_context = (
        cookie is not None
        or cookie_domain is not None
        or cookie_secure is not None
        or cookie_samesite is not None
    )
    if has_cookie_context:
        # Heuristic mismatches
        if cookie_domain and ("localhost" in str(cookie_domain) or ".int" in str(cookie_domain)):
            problems.append(
                Problem(
                    severity="warn",
                    code="COOKIE_DOMAIN_CHECK",
                    message=f"Cookie domain={cookie_domain} — verify it matches current host.",
                    fix=[
                        "For local dev, often omit domain to default to host",
                        "Use Secure=False on HTTP dev; SameSite=Lax",
                        "credentials: 'include' on fetch",
                    ],
                )
            )
        if (cookie_secure is True) and str(frontend_origin or "").startswith("http://"):
            problems.append(
                Problem(
                    severity="error",
                    code="COOKIE_SECURE_HTTP",
                    message="Secure cookie on HTTP dev will not attach.",
                    fix=[
                        "Set cookie secure=False in dev",
                        "Use HTTPS for secure=True",
                    ],
                )
            )
        if cookie_samesite and str(cookie_samesite).lower() not in ("lax", "none"):
            problems.append(
                Problem(
                    severity="warn",
                    code="COOKIE_SAMESITE_STRICT",
                    message=f"SameSite={cookie_samesite} may block cross-site usage.",
                    fix=["Prefer SameSite=Lax for same-site dev or None+Secure for cross-site"],
                )
            )

    # Wrong VITE_API_BASE
    if vite_api and backend_origin and vite_api != backend_origin:
        problems.append(
            Problem(
                severity="warn",
                code="VITE_API_BASE_MISMATCH",
                message=f"VITE_API_BASE={vite_api} but backend is {backend_origin}.",
                fix=["Point VITE_API_BASE to backend origin used for auth/requests"],
            )
        )

    # Backend errors
    be_text = "\n".join(be_lines[-400:])
    if _HTTP_ERR.search(be_text):
        problems.append(
            Problem(
                severity="warn",
                code="BACKEND_HTTP_ERRORS",
                message="Backend logs include 4xx/5xx responses.",
                fix=["Check specific endpoints and recent tracebacks"],
            )
        )

    if "alembic" in be_text or "migration" in be_text or "column" in be_text:
        problems.append(
            Problem(
                severity="warn",
                code="DB_DRIFT",
                message="Backend logs hint at DB migration issues.",
                fix=["Run alembic upgrade head or reset dev DB"],
            )
        )

    # Network JSONL heuristics (optional)
    try:
        if NETWORK_LOG.exists():
            import json as _json

            lines = NETWORK_LOG.read_text(encoding="utf-8").splitlines()[-300:]
            cnt_4xx = cnt_5xx = 0
            slow_urls = []
            for ln in lines:
                try:
                    ev = _json.loads(ln)
                except Exception:
                    continue
                st = int(ev.get("status") or 0)
                dur = int(ev.get("dur_ms") or 0)
                if 400 <= st < 500:
                    cnt_4xx += 1
                elif 500 <= st < 600:
                    cnt_5xx += 1
                if dur >= 2000:
                    slow_urls.append(ev.get("url"))
            if cnt_5xx >= 3:
                problems.append(
                    Problem(
                        severity="error",
                        code="MANY_5XX",
                        message=f"{cnt_5xx} recent 5xx responses.",
                        fix=["Check server errors and tracebacks"],
                    )
                )
            if cnt_4xx >= 5:
                problems.append(
                    Problem(
                        severity="warn",
                        code="MANY_4XX",
                        message=f"{cnt_4xx} recent 4xx responses.",
                        fix=["Check auth/permissions and request payloads"],
                    )
                )
            if slow_urls:
                problems.append(
                    Problem(
                        severity="warn",
                        code="SLOW_ENDPOINTS",
                        message=f"Slow requests ≥2s: {len(slow_urls)}",
                        fix=["Profile endpoints; check N+1 queries, cold starts"],
                    )
                )
    except Exception:
        pass

    # If network capture is enabled but no file/events, hint at CORS/preflight blocks
    v = (env or {}).get("VITE_DEVLOG_NETWORK") or (env or {}).get("vite_devlog_network")
    try_net = str(v).strip() == "1"
    if try_net and not NETWORK_LOG.exists():
        problems.append(
            Problem(
                severity="warn",
                code="NETWORK_CAPTURE_BLOCKED",
                message="Network capture enabled but no network.jsonl present.",
                fix=[
                    "Ensure /api/v1/devlog/network accepts simple POST (text/plain, no credentials) and CORS allows origin."
                ],
            )
        )

    # Promote selected warns to errors if requested by env.json
    if error_on:
        for p in problems:
            if (p.code in error_on) and p.severity == "warn":
                p.severity = "error"

    return problems


def build_status() -> StatusResponse:
    """
    Build comprehensive diagnostic status from logs and environment.

    Returns:
        StatusResponse with detected problems and context
    """
    from .tail import tail_lines

    env = load_env()
    fe = tail_lines(FRONTEND_LOG, n=600)
    be = tail_lines(BACKEND_LOG, n=600)

    problems = detect_problems(env, be, fe)
    ok = not any(p.severity == "error" for p in problems)

    ctx = Context(
        frontend_origin=env.get("frontend_origin"),
        backend_origin=env.get("backend_origin"),
        last_failed_url=env.get("last_failed_url"),
        last_error=env.get("last_error"),
        env=env,
    )
    return StatusResponse(ok=ok, problems=problems, context=ctx)
