"""RBAC and authorization utilities for DevDiag."""

import base64
import json
from typing import Any

# Define role capabilities
READER_CAN = {
    "get_status",
    "get_network_summary",
    "get_metrics",
    "get_request_diagnostics",
}
OPERATOR_CAN = {
    "set_mode",
    "set_sampling",
    "add_probe",
    "delete_probe",
    "export_snapshot",
    "compare_envs",
} | READER_CAN


class AuthorizationError(Exception):
    """Raised when authorization fails."""

    pass


async def parse_jwt_payload(
    token: str, jwks_url: str | None = None, audience: str = "mcp-devdiag"
) -> dict[str, Any]:
    """
    Parse and verify JWT payload.

    If jwks_url is provided, performs full JWKS verification.
    Otherwise falls back to lightweight decode (dev mode only).

    Args:
        token: JWT token to parse
        jwks_url: Optional JWKS endpoint URL for verification
        audience: Expected audience claim (default: "mcp-devdiag")

    Returns:
        Decoded JWT claims

    Raises:
        Exception: If verification fails
    """
    if jwks_url:
        # Production mode: verify with JWKS
        from .security_jwks import verify_jwt

        return await verify_jwt(token, jwks_url, audience)

    # Development mode: lightweight decode (NO VERIFICATION)
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        # Add padding if needed
        payload_part = parts[1]
        padding = "=" * (4 - len(payload_part) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_part + padding).decode())
        return payload
    except Exception:
        return {}


def parse_jwt_payload_sync(token: str) -> dict[str, Any]:
    """
    Synchronous JWT payload parser (lightweight, dev mode only).

    Args:
        token: JWT token to parse

    Returns:
        Decoded JWT claims (no verification)
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload_part = parts[1]
        padding = "=" * (4 - len(payload_part) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_part + padding).decode())
        return payload
    except Exception:
        return {}


def authorize(required: str, auth_header: str | None = None) -> dict[str, Any]:
    """
    Authorize a request based on required capability (synchronous version).

    For async JWKS verification, use authorize_async().

    Args:
        required: Required capability (e.g., "get_metrics")
        auth_header: Authorization header value (e.g., "Bearer token")

    Returns:
        dict with role information

    Raises:
        AuthorizationError: If authorization fails
    """
    role = "reader"  # Default role

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        payload = parse_jwt_payload_sync(token)
        role = payload.get("role", "reader")

    # Determine capabilities for role
    can = OPERATOR_CAN if role == "operator" else READER_CAN

    if required not in can:
        raise AuthorizationError(f"Role '{role}' cannot perform '{required}'")

    return {"role": role, "can": list(can)}


async def authorize_async(
    required: str, auth_header: str | None = None, jwks_url: str | None = None
) -> dict[str, Any]:
    """
    Authorize a request with async JWKS verification.

    Args:
        required: Required capability (e.g., "get_metrics")
        auth_header: Authorization header value (e.g., "Bearer token")
        jwks_url: Optional JWKS URL for JWT verification

    Returns:
        dict with role information

    Raises:
        AuthorizationError: If authorization fails
    """
    role = "reader"  # Default role

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        payload = await parse_jwt_payload(token, jwks_url)
        role = payload.get("role", "reader")

    # Determine capabilities for role
    can = OPERATOR_CAN if role == "operator" else READER_CAN

    if required not in can:
        raise AuthorizationError(f"Role '{role}' cannot perform '{required}'")

    return {"role": role, "can": list(can)}
