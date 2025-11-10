from __future__ import annotations
import json, os, subprocess, time, ipaddress, uuid, logging, sys
from typing import Literal, Optional, Any, Dict
from fastapi import FastAPI, HTTPException, Depends, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, AnyHttpUrl, Field
from jose import jwt, jwk
from jose.utils import base64url_decode
import requests
import threading

# --------------------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------------------
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")

# --------------------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------------------
JWKS_URL = os.getenv("JWKS_URL", "")
JWT_AUD = os.getenv("JWT_AUD", "mcp-devdiag")
ALLOW_PRIVATE_IP = os.getenv("ALLOW_PRIVATE_IP", "0") == "1"
RATE_LIMIT_RPS = float(os.getenv("RATE_LIMIT_RPS", "2"))  # simple token bucket
ALLOWED_ORIGINS = [o for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o]
CLI_BIN = os.getenv("DEVDIAG_CLI", "mcp-devdiag")
CLI_TIMEOUT = int(os.getenv("DEVDIAG_TIMEOUT_S", "180"))
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "2"))

# Concurrency control
_sem = threading.Semaphore(MAX_CONCURRENT)

# Centralize CLI invocation here in case flags differ in future versions.
# Adjust this function if your mcp-devdiag CLI uses different flags.
def run_devdiag_cli(url: str, preset: str, suppress: Optional[list[str]], extra_args: list[str]) -> Dict[str, Any]:
    """
    Calls the DevDiag CLI and returns parsed JSON.

    Expected CLI (example):
      mcp-devdiag probe --url <url> --preset <preset> --format json [--suppress P1 --suppress P2]
    If your CLI differs, update the command below (single place).
    """
    cmd = [CLI_BIN, "probe", "--url", url, "--preset", preset, "--format", "json"]
    if suppress:
        for code in suppress:
            cmd += ["--suppress", code]
    cmd += extra_args
    
    # Acquire concurrency slot
    acquired = _sem.acquire(timeout=CLI_TIMEOUT)
    if not acquired:
        raise HTTPException(status_code=503, detail="Busy: concurrent runs at capacity")
    
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=CLI_TIMEOUT)
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            # If CLI emitted pretty logs + JSON, try last JSON block
            last_brace = out.rfind("{")
            return json.loads(out[last_brace:])
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"DevDiag error: {e.output.strip() or str(e)}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="DevDiag timed out")
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail=f"Non-JSON output from DevDiag: {out[:4000]}")
    finally:
        _sem.release()

# --------------------------------------------------------------------------------------
# Security (JWT via JWKS)
# --------------------------------------------------------------------------------------
_jwks_cache: Dict[str, Any] = {}
_jwks_ts = 0.0
def _get_jwks() -> Dict[str, Any]:
    global _jwks_cache, _jwks_ts
    if not JWKS_URL:
        return {}
    if time.time() - _jwks_ts > 300 or not _jwks_cache:
        r = requests.get(JWKS_URL, timeout=5)
        r.raise_for_status()
        _jwks_cache = r.json()
        _jwks_ts = time.time()
    return _jwks_cache

def verify_jwt(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not JWKS_URL:
        return {"sub": "anonymous"}  # auth disabled for local dev if no JWKS_URL
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization[len("Bearer "):].strip()
    jwks = _get_jwks()
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")
    if not jwks or "keys" not in jwks:
        raise HTTPException(status_code=500, detail="JWKS unavailable")
    key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
    if key is None:
        raise HTTPException(status_code=401, detail="Unrecognized key id")
    try:
        payload = jwt.decode(token, key, algorithms=[key.get("alg", "RS256")], audience=JWT_AUD)
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"JWT invalid: {str(e)}")

# --------------------------------------------------------------------------------------
# Basic token-bucket rate limiting (per-process)
# --------------------------------------------------------------------------------------
_tokens = RATE_LIMIT_RPS
_last_refill = time.time()
_lock = threading.Lock()

def rate_limit():
    global _tokens, _last_refill
    with _lock:
        now = time.time()
        delta = now - _last_refill
        _last_refill = now
        _tokens = min(RATE_LIMIT_RPS, _tokens + delta * RATE_LIMIT_RPS)
        if _tokens < 1.0:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        _tokens -= 1.0

# --------------------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------------------
Preset = Literal["chat", "embed", "app", "full"]

class DiagRequest(BaseModel):
    url: AnyHttpUrl
    preset: Preset = "app"
    suppress: Optional[list[str]] = Field(default=None, description="Problem codes to suppress")
    extra_args: Optional[list[str]] = Field(default=None, description="Extra CLI flags to pass through")

class DiagResponse(BaseModel):
    ok: bool
    url: AnyHttpUrl
    preset: Preset
    result: Dict[str, Any]

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def _is_private_ip(url: str) -> bool:
    # very small guard against SSRF to internal networks when desired
    try:
        # Fast path: resolve host using system resolver only when needed.
        from urllib.parse import urlparse
        host = urlparse(url).hostname
        if not host:
            return True
        # Let the OS resolve; if it fails we let DevDiag error later
        ip = requests.get(f"https://dns.google/resolve?name={host}&type=A", timeout=3).json()
        answers = ip.get("Answer", [])
        for a in answers:
            ipaddr = ipaddress.ip_address(a.get("data"))
            if ipaddr.is_private or ipaddr.is_loopback or ipaddr.is_reserved or ipaddr.is_link_local:
                return True
        return False
    except Exception:
        # If DNS fails, be conservative (block) to avoid SSRF in prod
        return True

# --------------------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------------------
app = FastAPI(title="DevDiag HTTP Wrapper", version="0.1.0")

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("x-request-id", str(uuid.uuid4()))
    start = time.time()
    response = await call_next(request)
    dur = (time.time() - start) * 1000
    logging.info(json.dumps({
        "event": "http_access",
        "rid": rid,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "ms": round(dur, 2),
    }))
    response.headers["x-request-id"] = rid
    return response

if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/healthz")
def healthz():
    return {"ok": True, "service": "devdiag-http", "version": "0.1.0"}

@app.head("/healthz")
def healthz_head():
    return Response(status_code=200)

@app.get("/metrics")
def metrics():
    """Prometheus-compatible metrics endpoint"""
    lines = [
        '# HELP devdiag_http_up 1 if server is healthy',
        '# TYPE devdiag_http_up gauge',
        'devdiag_http_up 1',
        '# HELP devdiag_http_rate_limit_rps configured RPS',
        '# TYPE devdiag_http_rate_limit_rps gauge',
        f'devdiag_http_rate_limit_rps {RATE_LIMIT_RPS}',
        '# HELP devdiag_http_max_concurrent configured concurrent runs',
        '# TYPE devdiag_http_max_concurrent gauge',
        f'devdiag_http_max_concurrent {MAX_CONCURRENT}',
        '# HELP devdiag_http_timeout_seconds configured CLI timeout',
        '# TYPE devdiag_http_timeout_seconds gauge',
        f'devdiag_http_timeout_seconds {CLI_TIMEOUT}',
    ]
    return Response("\n".join(lines) + "\n", media_type="text/plain")

@app.get("/probes")
def probes():
    # Static list to keep the wrapper decoupled from internal probe registry
    return {
        "presets": ["chat", "embed", "app", "full"],
        "notes": "Probes are selected by preset inside DevDiag; pass suppress codes to mute known issues."
    }

@app.post("/diag/run", response_model=DiagResponse)
def diag_run(req: DiagRequest, _: Dict[str, Any] = Depends(verify_jwt), request: Request = None):
    rate_limit()
    if not ALLOW_PRIVATE_IP and _is_private_ip(str(req.url)):
        raise HTTPException(status_code=400, detail="Refusing private/loopback/unknown host (set ALLOW_PRIVATE_IP=1 to override)")
    result = run_devdiag_cli(
        url=str(req.url),
        preset=req.preset,
        suppress=req.suppress,
        extra_args=req.extra_args or [],
    )
    return DiagResponse(ok=True, url=req.url, preset=req.preset, result=result)
