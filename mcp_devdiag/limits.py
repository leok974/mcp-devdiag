# mcp_devdiag/limits.py
"""Lightweight per-tenant rate limiting using token bucket algorithm."""

import time
from collections import defaultdict
from typing import DefaultDict


class TokenBucket:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, burst: int):
        """
        Initialize token bucket.

        Args:
            rate: Tokens added per second (e.g., 0.5 = 30/min)
            burst: Maximum tokens (burst capacity)
        """
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.ts = time.time()

    def allow(self) -> bool:
        """
        Check if request is allowed (consume 1 token).

        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        # Refill tokens based on elapsed time
        self.tokens = min(self.burst, self.tokens + (now - self.ts) * self.rate)
        self.ts = now

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


# Global bucket storage (tenant:key -> TokenBucket)
# Default: 30 requests/min (0.5/sec), burst of 5
_buckets: DefaultDict[str, TokenBucket] = defaultdict(lambda: TokenBucket(rate=0.5, burst=5))


def guard(tenant: str, key: str) -> None:
    """
    Rate limit guard for tenant/key combination.

    Args:
        tenant: Tenant identifier
        key: Operation key (e.g., "diag_bundle")

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    bucket_key = f"{tenant}:{key}"
    bucket = _buckets[bucket_key]

    if not bucket.allow():
        from fastapi import HTTPException

        raise HTTPException(status_code=429, detail="Rate limit exceeded")
