"""devdiag_client.py - Python client SDK for mcp-devdiag

Usage:
    Copy to your project and install: pip install requests
"""

import requests
from typing import Any, Dict, List, Optional


class DevDiagClient:
    """Client for mcp-devdiag API."""

    def __init__(self, base_url: str, jwt: str, timeout: int = 10):
        """
        Initialize DevDiag client.

        Args:
            base_url: Base URL of DevDiag server (e.g., "https://diag.example.com")
            jwt: JWT token for authentication
            timeout: Request timeout in seconds (default: 10)
        """
        self.base_url = base_url.rstrip("/")
        self.jwt = jwt
        self.timeout = timeout
        self.headers = {"Authorization": f"Bearer {jwt}"}

    def status_plus(
        self, target_url: str, preset: str = "app", driver: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregate diagnostics with scoring and fix recommendations.

        Args:
            target_url: URL to diagnose
            preset: Probe preset ("chat", "embed", "app", "full")
            driver: Optional driver type ("http", "playwright")

        Returns:
            Dict with ok, score, severity, problems, fixes, evidence

        Raises:
            requests.HTTPError: If API request fails
        """
        params = {"base_url": target_url, "preset": preset}
        if driver:
            params["driver"] = driver

        response = requests.get(
            f"{self.base_url}/mcp/diag/status_plus",
            params=params,
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def quickcheck(self, target_url: str) -> Dict[str, Any]:
        """
        Fast HTTP-only quickcheck (CI-safe, no browser).

        Args:
            target_url: URL to check

        Returns:
            Dict with probe results (CSP/iframe compatibility)

        Raises:
            requests.HTTPError: If API request fails
        """
        response = requests.post(
            f"{self.base_url}/mcp/diag/quickcheck",
            json={"url": target_url},
            headers={**self.headers, "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def remediation(self, problems: List[str]) -> Dict[str, List[str]]:
        """
        Get remediation steps for specific problem codes.

        Args:
            problems: List of problem codes (e.g., ["IFRAME_FRAME_ANCESTORS_BLOCKED"])

        Returns:
            Dict mapping problem codes to remediation steps

        Raises:
            requests.HTTPError: If API request fails
        """
        response = requests.post(
            f"{self.base_url}/mcp/diag/remediation",
            json={"problems": problems},
            headers={**self.headers, "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_schema(self) -> Dict[str, Any]:
        """
        Get ProbeResult JSON schema.

        Returns:
            JSON schema dict for ProbeResult type

        Raises:
            requests.HTTPError: If API request fails
        """
        response = requests.get(
            f"{self.base_url}/mcp/diag/schema/probe_result",
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def bundle(
        self, target_url: str, preset: Optional[str] = None, driver: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run diagnostic probe bundle.

        Args:
            target_url: URL to probe
            preset: Optional probe preset ("chat", "embed", "app", "full")
            driver: Optional driver type ("http", "playwright")

        Returns:
            Bundle result with aggregated problems, remediation, evidence

        Raises:
            requests.HTTPError: If API request fails
        """
        payload = {"url": target_url}
        if preset:
            payload["preset"] = preset
        if driver:
            payload["driver"] = driver

        response = requests.post(
            f"{self.base_url}/mcp/diag/bundle",
            json=payload,
            headers={**self.headers, "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


# Example usage:
if __name__ == "__main__":
    import os

    client = DevDiagClient(base_url=os.environ["DEVDIAG_URL"], jwt=os.environ["DEVDIAG_READER_JWT"])

    # Get comprehensive status
    result = client.status_plus("https://app.example.com", preset="full")
    if not result["ok"]:
        print(f"Problems detected (score: {result['score']}):")
        for problem in result["problems"]:
            print(f"  - {problem}")
            if problem in result["fixes"]:
                print(f"    Fixes: {result['fixes'][problem]}")

    # Quick check for CI
    quick = client.quickcheck("https://app.example.com/chat/")
    print(f"Quickcheck: {quick}")
