"""Playwright driver adapter for runtime DOM checks (staging only)."""

from typing import Any, List
from .adapters import Driver


class PlaywrightDriver(Driver):
    """
    Playwright-based driver for DOM inspection and JavaScript evaluation.
    
    Should only be enabled in staging/dev environments via diag.browser_enabled config.
    """
    
    name = "playwright"
    
    def __init__(self):
        self._pw = None
        self.browser = None
        self.page = None
        self._console: List[str] = []
    
    async def start(self):
        """Initialize Playwright browser instance."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Install with: pip install playwright && playwright install chromium"
            )
        
        self._pw = await async_playwright().start()
        self.browser = await self._pw.chromium.launch(headless=True)
        ctx = await self.browser.new_context()
        self.page = await ctx.new_page()
        self.page.on("console", lambda m: self._console.append(m.text()))
    
    async def goto(self, url: str) -> None:
        """Navigate to URL and wait for network idle."""
        if self.page is None:
            await self.start()
        await self.page.goto(url, wait_until="networkidle", timeout=10000)
    
    async def eval_js(self, expr: str) -> Any:
        """Evaluate JavaScript expression in page context."""
        if self.page is None:
            raise RuntimeError("Page not initialized - call goto() first")
        return await self.page.evaluate(expr)
    
    async def get_console(self) -> list[str]:
        """Get captured console logs."""
        return list(self._console)
    
    async def dispose(self) -> None:
        """Clean up browser resources."""
        if self.browser:
            await self.browser.close()
        if self._pw:
            await self._pw.stop()
