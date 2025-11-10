# mcp_devdiag/incident.py
"""Incident response TTL auto-revert for mode and sampling changes."""

import asyncio
import time
from typing import Any, Callable, Awaitable

# Global incident state
_state: dict[str, Any] = {"expiry": 0, "saved": None, "task": None}


def now() -> int:
    """Get current timestamp in seconds."""
    return int(time.time())


async def elevate(
    set_mode: Callable[[str], Awaitable[None]],
    set_sampling: Callable[..., Awaitable[None]],
    ttl_s: int,
    saved_snapshot: dict[str, Any],
) -> None:
    """
    Temporarily elevate to high-fidelity mode with auto-revert after TTL.

    Args:
        set_mode: Async function to set mode
        set_sampling: Async function to set sampling config
        ttl_s: Time-to-live in seconds before auto-revert
        saved_snapshot: Previous configuration to restore
    """
    # Save current state
    _state["saved"] = saved_snapshot
    _state["expiry"] = now() + ttl_s

    async def _timer() -> None:
        """Timer task that reverts configuration after TTL."""
        try:
            await asyncio.sleep(ttl_s)
            # Revert to saved configuration
            await set_mode(saved_snapshot["mode"])
            await set_sampling(**saved_snapshot["sampling"])
        finally:
            # Clear incident state
            _state.update({"expiry": 0, "saved": None, "task": None})

    # Cancel previous timer if exists
    if _state["task"]:
        _state["task"].cancel()

    # Start new timer
    _state["task"] = asyncio.create_task(_timer())


def remaining() -> int:
    """
    Get remaining seconds until auto-revert.

    Returns:
        Seconds remaining (0 if no active incident)
    """
    return max(0, _state["expiry"] - now())
