# mcp_devdiag/security_jwks.py
"""JWKS-based JWT verification for production authentication."""

from typing import Any
import time
import httpx
from jose import jwt


class JWKSCache:
    """Cache for JWKS (JSON Web Key Set) to avoid repeated fetches."""

    def __init__(self, url: str, ttl: int = 600):
        """
        Initialize JWKS cache.

        Args:
            url: JWKS endpoint URL
            ttl: Time-to-live in seconds (default 10 minutes)
        """
        self.url = url
        self.ttl = ttl
        self._keys: dict[str, Any] | None = None
        self._exp = 0

    async def get(self) -> dict[str, Any]:
        """
        Get JWKS, using cache if valid.

        Returns:
            JWKS dictionary with 'keys' array
        """
        now = int(time.time())
        if self._keys and now < self._exp:
            return self._keys

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(self.url)
            response.raise_for_status()
            data = response.json()

        self._keys = data
        self._exp = now + self.ttl
        return data


async def verify_jwt(token: str, jwks_url: str, audience: str) -> dict[str, Any]:
    """
    Verify JWT using JWKS endpoint.

    Args:
        token: JWT token to verify
        jwks_url: JWKS endpoint URL
        audience: Expected audience claim

    Returns:
        Decoded JWT claims

    Raises:
        jose.exceptions.JWTError: If token is invalid
        jose.exceptions.ExpiredSignatureError: If token is expired
        jose.exceptions.JWTClaimsError: If audience doesn't match
    """
    cache = JWKSCache(jwks_url)
    jwks = await cache.get()
    return jwt.decode(token, jwks, algorithms=["RS256"], audience=audience)
