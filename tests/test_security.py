"""Tests for DevDiag security and authorization."""

import pytest
from mcp_devdiag.security import authorize, AuthorizationError, READER_CAN, OPERATOR_CAN
from mcp_devdiag.config import load_config


def test_reader_role_permissions():
    """Test that reader role has correct permissions."""
    result = authorize("get_status", "Bearer fake.reader.token")
    assert result["role"] == "reader"
    assert "get_status" in READER_CAN
    assert "get_metrics" in READER_CAN
    assert "set_mode" not in READER_CAN


def test_operator_role_has_all_permissions():
    """Test that operator role has all permissions."""
    assert READER_CAN.issubset(OPERATOR_CAN)
    assert "set_mode" in OPERATOR_CAN
    assert "export_snapshot" in OPERATOR_CAN


def test_authorization_failure():
    """Test that authorization fails for insufficient permissions."""
    with pytest.raises(AuthorizationError):
        # Reader trying to perform operator action
        authorize("set_mode", None)  # No auth = reader role


def test_allow_probe_matching():
    """Test probe URL allowlist matching."""
    cfg = load_config()

    # These should match patterns in devdiag.yaml
    assert cfg.method_url_allowed("GET", "https://api.tasteos.app/healthz")
    assert cfg.method_url_allowed("GET", "https://api.tasteos.app/api/ready")
    assert cfg.method_url_allowed("HEAD", "https://cdn.tasteos.app/assets/logo.png")

    # These should NOT match
    assert not cfg.method_url_allowed("POST", "https://api.tasteos.app/healthz")
    assert not cfg.method_url_allowed("GET", "https://evil.com/secret")
    assert not cfg.method_url_allowed("DELETE", "https://api.tasteos.app/users/1")


def test_config_defaults():
    """Test configuration defaults when file doesn't exist."""
    cfg = load_config("nonexistent.yaml")
    assert cfg.mode == "dev"
    assert cfg.tenant == "default"
    assert cfg.allow_probes == []
    assert cfg.rbac == {"provider": "noop", "roles": []}
