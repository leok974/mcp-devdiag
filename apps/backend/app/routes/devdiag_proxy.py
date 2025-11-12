from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel, HttpUrl, field_validator
from typing import List, Optional, Literal, Dict, Any
import httpx, os, asyncio, random

router = APIRouter()

DEVDIAG_BASE = os.getenv("DEVDIAG_BASE", "")
DEVDIAG_JWT  = os.getenv("DEVDIAG_JWT", "")
TIMEOUT_S    = int(os.getenv("DEVDIAG_TIMEOUT_S", "120"))
DEVDIAG_ENABLED = os.getenv("DEVDIAG_ENABLED", "1") == "1"
# Comma-separated; items may be full hosts or root domains like ".ledger-mind.org"
DEVDIAG_ALLOW_HOSTS = {h.strip().lower() for h in os.getenv(
    "DEVDIAG_ALLOW_HOSTS", "app.ledger-mind.org"
).split(",") if h.strip()}

# Optional: wire your own admin gate
# from app.routes.auth import admin_required

Preset = Literal["chat", "embed", "app", "full"]

class RunPayload(BaseModel):
    url: HttpUrl
    preset: Preset = "app"
    suppress: Optional[List[str]] = None
    tenant: str = "ledgermind"

    @field_validator("url")
    @classmethod
    def check_host(cls, v: HttpUrl) -> HttpUrl:
        host = v.host.lower()
        for allowed in DEVDIAG_ALLOW_HOSTS:
            if allowed.startswith("."):
                # Subdomain or exact root (".example.com" allows "a.example.com" and "example.com")
                if host == allowed[1:] or host.endswith(allowed):
                    return v
            else:
                if host == allowed:
                    return v
        raise ValueError(f"target host '{host}' not in allowlist")

class DiagResponse(BaseModel):
    ok: bool
    url: HttpUrl
    preset: Preset
    result: Dict[str, Any]

def require_base():
    if not DEVDIAG_BASE:
        raise HTTPException(status_code=503, detail="DevDiag base URL not configured")
    return True

def require_enabled():
    if not DEVDIAG_ENABLED:
        # 404 avoids leaking feature existence
        raise HTTPException(status_code=404, detail="Not found")
    return True

def _svc_headers(req: Request) -> dict:
    h = {"content-type": "application/json"}
    if DEVDIAG_JWT:
        h["authorization"] = f"Bearer {DEVDIAG_JWT}"
    # Trace headers pass-through (extend if you use W3C traceparent, etc.)
    for k in ("x-request-id", "x-b3-traceid", "x-b3-spanid", "traceparent"):
        v = req.headers.get(k)
        if v:
            h[k] = v
    return h

_client_limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)

@router.get("/ops/diag/health")
async def diag_health(
    _: bool = Depends(require_base),
    __: bool = Depends(require_enabled),
):
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False, limits=_client_limits) as client:
            r = await client.get(f"{DEVDIAG_BASE}/healthz")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"DevDiag health check failed: {e}")

async def _post_with_retry(url: str, json: dict, headers: dict, timeout: int) -> httpx.Response:
    # Retries on transient conditions; backoff with jitter
    attempts = (
        (0.0, None),
        (0.6 + random.random() * 0.4, {429, 503, 504}),
        (1.5 + random.random() * 0.7, {429, 503, 504}),
    )
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, limits=_client_limits) as client:
        last_exc = None
        for delay, retry_codes in attempts:
            if delay:
                await asyncio.sleep(delay)
            try:
                res = await client.post(url, json=json, headers=headers)
                if retry_codes and res.status_code in retry_codes:
                    last_exc = HTTPException(status_code=res.status_code, detail=res.text)
                    continue
                return res
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exc = e
        if isinstance(last_exc, HTTPException):
            raise last_exc
        raise HTTPException(status_code=502, detail=f"DevDiag call failed: {last_exc or 'retry exhausted'}")

@router.post("/ops/diag", response_model=DiagResponse)
async def run_diag(
    payload: RunPayload,
    request: Request,
    _: bool = Depends(require_base),
    __: bool = Depends(require_enabled),
    # ___: Any = Depends(admin_required)  # uncomment if you want admin-only
):
    headers = _svc_headers(request)
    try:
        r = await _post_with_retry(f"{DEVDIAG_BASE}/diag/run", payload.model_dump(), headers, TIMEOUT_S)
        # Cap overly large responses (defense-in-depth; adjust if needed)
        if int(r.headers.get("content-length") or "0") > 2_000_000:
            raise HTTPException(status_code=502, detail="DevDiag response too large")
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        data = r.json()
        # Propagate x-request-id if DevDiag set it
        rid = r.headers.get("x-request-id")
        resp = Response()
        if rid:
            resp.headers["x-request-id"] = rid
        # Let FastAPI render with typed model
        return DiagResponse.model_validate(data)
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="DevDiag timed out")
