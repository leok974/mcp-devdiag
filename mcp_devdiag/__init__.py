"""
mcp-devdiag: MCP server for autonomous dev diagnostics.

Provides probes for DOM overlays, CSP headers, handshake analysis, framework versions, and more.
"""

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "server",
    "analyzer",
    "tail",
    "schema",
    "probes",
    "security",
    "security_jwks",
    "limits",
    "incident",
    "config",
]
