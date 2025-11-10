"""RBAC and authorization utilities for DevDiag."""

import base64
import json

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


def parse_jwt_payload(token: str) -> dict:
    """
    Parse JWT payload without verification (stub implementation).

    WARNING: This is a minimal implementation for development.
    In production, replace with proper JWT verification using
    python-jose with JWKS validation.
    """
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


def authorize(required: str, auth_header: str | None = None) -> dict:
    """
    Authorize a request based on required capability.

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
        payload = parse_jwt_payload(token)
        role = payload.get("role", "reader")

    # Determine capabilities for role
    can = OPERATOR_CAN if role == "operator" else READER_CAN

    if required not in can:
        raise AuthorizationError(f"Role '{role}' cannot perform '{required}'")

    return {"role": role, "can": list(can)}
