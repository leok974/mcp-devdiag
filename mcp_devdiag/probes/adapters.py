# mcp_devdiag/probes/adapters.py
"""Driver abstraction for HTTP-only and browser-based diagnostics."""

from typing import Any, Optional, Protocol
import httpx


class Driver(Protocol):
    """Abstract driver interface for diagnostic probes."""

    name: str

    async def goto(self, url: str) -> None:
        """Navigate to URL."""
        ...

    async def eval_js(self, expr: str) -> Any:
        """Evaluate JavaScript expression."""
        ...

    async def get_console(self) -> list[str]:
        """Get console logs."""
        ...

    async def get_response(self) -> Any:
        """Get HTTP response object."""
        ...

    async def dispose(self) -> None:
        """Clean up driver resources."""
        ...


class HttpDriver:
    """HTTP-only driver for prod-safe header/CSP checks."""

    name = "http"

    def __init__(self, client: httpx.AsyncClient):
        self._client = client
        self._response: Optional[httpx.Response] = None

    async def goto(self, url: str) -> None:
        """Fetch URL with timeout."""
        self._response = await self._client.get(url, timeout=5.0, follow_redirects=True)

    async def eval_js(self, expr: str) -> Any:
        """Not supported in HTTP mode."""
        raise NotImplementedError("JavaScript evaluation requires browser driver")

    async def get_console(self) -> list[str]:
        """No console in HTTP mode."""
        return []

    async def get_response(self) -> httpx.Response:
        """Get the HTTP response."""
        if self._response is None:
            raise RuntimeError("No response available - call goto() first")
        return self._response

    async def dispose(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()


class PlaywrightDriver:
    """Playwright-based driver for runtime DOM/console diagnostics."""

    name = "playwright"

    def __init__(self, page):
        self._page = page
        self._console_logs: list[str] = []
        self._page.on("console", lambda msg: self._console_logs.append(msg.text))

    async def goto(self, url: str) -> None:
        """Navigate to URL with Playwright."""
        await self._page.goto(url, wait_until="networkidle", timeout=10000)

    async def eval_js(self, expr: str) -> Any:
        """Evaluate JavaScript in page context."""
        return await self._page.evaluate(expr)

    async def get_console(self) -> list[str]:
        """Return captured console logs."""
        return self._console_logs.copy()

    async def get_response(self) -> Any:
        """Get last response (limited support)."""
        # Note: Playwright doesn't provide easy access to full response
        # This is a placeholder for compatibility
        return None

    async def dispose(self) -> None:
        """Close browser page."""
        await self._page.close()


async def get_driver(
    kind: Optional[str],
    http_client_factory,
    playwright_factory=None,
) -> Driver:
    """
    Get appropriate driver based on kind and availability.

    Args:
        kind: "http", "playwright", "puppeteer", "selenium", or None (auto-detect)
        http_client_factory: Callable that returns httpx.AsyncClient
        playwright_factory: Optional callable that returns Playwright page

    Returns:
        Driver instance (HttpDriver or PlaywrightDriver)
    """
    kind = (kind or "http").lower()

    # Force HTTP if no browser factory available
    if kind == "http" or playwright_factory is None:
        return HttpDriver(http_client_factory())

    # Playwright support
    if kind == "playwright":
        if playwright_factory is None:
            # Graceful degradation
            return HttpDriver(http_client_factory())
        page = await playwright_factory()
        return PlaywrightDriver(page)

    # TODO: Add puppeteer/selenium support
    # For now, default to HTTP for unsupported drivers
    return HttpDriver(http_client_factory())
