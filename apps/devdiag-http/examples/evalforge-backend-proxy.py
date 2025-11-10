"""
EvalForge backend proxy for DevDiag HTTP API

This backend route hides JWT tokens from the frontend and provides
a clean internal API for running diagnostics.

Usage in FastAPI:
  from .routes import devdiag_proxy
  app.include_router(devdiag_proxy.router, prefix="/api")
"""

import os
import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Literal

router = APIRouter()

# Configuration
DEVDIAG_BASE = os.getenv("DEVDIAG_BASE", "http://devdiag-http:8080")
DEVDIAG_JWT = os.getenv("DEVDIAG_JWT", "")

Preset = Literal["chat", "embed", "app", "full"]


class DiagRequest(BaseModel):
    """Diagnostic request from frontend"""
    url: HttpUrl
    preset: Preset = "app"
    suppress: Optional[List[str]] = None


class DiagResponse(BaseModel):
    """Diagnostic response to frontend"""
    ok: bool
    url: str
    preset: str
    problems: List[str]
    fixes: dict
    evidence: dict
    score: Optional[float] = None
    severity: Optional[str] = None


@router.post("/ops/diag", response_model=DiagResponse)
async def run_diagnostic(req: DiagRequest):
    """
    Run DevDiag diagnostic (proxies to devdiag-http server)
    
    Frontend calls this endpoint; backend handles JWT authentication
    with the DevDiag HTTP server.
    
    Example:
        POST /api/ops/diag
        {"url": "https://example.com", "preset": "app"}
    """
    headers = {"content-type": "application/json"}
    if DEVDIAG_JWT:
        headers["authorization"] = f"Bearer {DEVDIAG_JWT}"
    
    payload = {
        "url": str(req.url),
        "preset": req.preset,
        "suppress": req.suppress or [],
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{DEVDIAG_BASE}/diag/run",
                json=payload,
                headers=headers,
            )
            
            if response.status_code >= 400:
                detail = response.json().get("detail", response.text) if response.text else "DevDiag error"
                raise HTTPException(status_code=response.status_code, detail=detail)
            
            data = response.json()
            
            # Flatten response for frontend
            result = data.get("result", {})
            return DiagResponse(
                ok=data.get("ok", True),
                url=str(data.get("url", req.url)),
                preset=data.get("preset", req.preset),
                problems=result.get("problems", []),
                fixes=result.get("fixes", {}),
                evidence=result.get("evidence", {}),
                score=result.get("score"),
                severity=result.get("severity"),
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="DevDiag timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"DevDiag unavailable: {str(e)}")


@router.get("/ops/diag/health")
async def health_check():
    """
    Check if DevDiag HTTP server is healthy
    
    Example:
        GET /api/ops/diag/health
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{DEVDIAG_BASE}/healthz")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DevDiag unhealthy: {str(e)}")


# Example integration in main FastAPI app:
#
# from fastapi import FastAPI
# from .routes import devdiag_proxy
#
# app = FastAPI()
# app.include_router(devdiag_proxy.router, prefix="/api", tags=["diagnostics"])
#
# # Frontend usage:
# const response = await fetch('/api/ops/diag', {
#   method: 'POST',
#   headers: {'Content-Type': 'application/json'},
#   body: JSON.stringify({url: 'https://example.com', preset: 'app'}),
# });
