"""
EvalForge integration example for DevDiag HTTP API (Python backend)

Server-side usage in Python/FastAPI/Flask applications.
"""

import os
from typing import Optional, List, Dict, Any, Literal
import httpx

DEVDIAG_BASE = os.getenv("DEVDIAG_BASE", "http://localhost:8080")
DEVDIAG_JWT = os.getenv("DEVDIAG_JWT")  # Optional: only needed if JWKS_URL is set

Preset = Literal["chat", "embed", "app", "full"]


class DevDiagClient:
    """HTTP client for DevDiag server"""

    def __init__(self, base_url: str = DEVDIAG_BASE, jwt: Optional[str] = DEVDIAG_JWT):
        self.base_url = base_url.rstrip("/")
        self.jwt = jwt

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.jwt:
            headers["Authorization"] = f"Bearer {self.jwt}"
        return headers

    async def run_diagnostics(
        self,
        url: str,
        preset: Preset = "app",
        suppress: Optional[List[str]] = None,
        extra_args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run DevDiag diagnostics on a URL

        Args:
            url: Target URL to diagnose
            preset: Probe preset (chat, embed, app, full)
            suppress: List of problem codes to suppress
            extra_args: Extra CLI flags to pass through

        Returns:
            Diagnostic response with ok, url, preset, result

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/diag/run",
                json={
                    "url": url,
                    "preset": preset,
                    "suppress": suppress or [],
                    "extra_args": extra_args or [],
                },
                headers=self._headers(),
                timeout=180.0,  # DevDiag can take time with Playwright
            )
            response.raise_for_status()
            return response.json()

    async def health_check(self) -> Dict[str, Any]:
        """Check server health"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/healthz")
            response.raise_for_status()
            return response.json()

    async def get_presets(self) -> Dict[str, Any]:
        """Get available probe presets"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/probes")
            response.raise_for_status()
            return response.json()


# Example usage in FastAPI:
#
# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel, HttpUrl
#
# app = FastAPI()
# devdiag = DevDiagClient()
#
# class DiagRequest(BaseModel):
#     url: HttpUrl
#     preset: Preset = "app"
#
# @app.post("/api/check-url")
# async def check_url(req: DiagRequest):
#     try:
#         result = await devdiag.run_diagnostics(
#             url=str(req.url),
#             preset=req.preset,
#         )
#         return result
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=e.response.status_code, detail=str(e))


# Example usage in Flask:
#
# from flask import Flask, request, jsonify
# import asyncio
#
# app = Flask(__name__)
# devdiag = DevDiagClient()
#
# @app.route("/api/check-url", methods=["POST"])
# def check_url():
#     data = request.json
#     url = data.get("url")
#     preset = data.get("preset", "app")
#
#     try:
#         result = asyncio.run(devdiag.run_diagnostics(url=url, preset=preset))
#         return jsonify(result)
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
