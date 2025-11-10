"""Production policy enforcement tests."""

import os
import yaml
import pytest


def test_prod_policy_defaults():
    """Enforce production-safe defaults in devdiag.yaml."""
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "devdiag.yaml")
    if not os.path.exists(cfg_path):
        pytest.skip("devdiag.yaml not found")

    cfg = yaml.safe_load(open(cfg_path))
    mode = cfg.get("mode", "")

    if mode.startswith("prod"):
        # Production mode must have conservative sampling
        sampling = cfg.get("sampling", {})
        assert sampling.get("frontend_events", 0.02) <= 0.05, (
            "frontend_events sampling must be ≤5% in prod"
        )
        assert sampling.get("network_spans", 0.02) <= 0.05, (
            "network_spans sampling must be ≤5% in prod"
        )

        # Must never capture bodies in production
        assert "capture_bodies" not in cfg, "capture_bodies must not be configured in prod"

        # JWKS verification required in production
        rbac = cfg.get("rbac", {})
        assert rbac.get("jwks_url"), "JWKS URL required in prod mode for real JWT verification"


def test_rbac_roles_defined():
    """Verify RBAC roles are properly configured."""
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "devdiag.yaml")
    if not os.path.exists(cfg_path):
        pytest.skip("devdiag.yaml not found")

    cfg = yaml.safe_load(open(cfg_path))
    rbac = cfg.get("rbac", {})

    assert rbac.get("provider") == "jwt", "RBAC provider must be jwt"
    roles = rbac.get("roles", [])
    assert len(roles) >= 2, "Must define at least reader and operator roles"

    role_names = {r["name"] for r in roles}
    assert "reader" in role_names, "Must have reader role"
    assert "operator" in role_names, "Must have operator role"


def test_redaction_configured():
    """Verify sensitive header redaction is configured."""
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "devdiag.yaml")
    if not os.path.exists(cfg_path):
        pytest.skip("devdiag.yaml not found")

    cfg = yaml.safe_load(open(cfg_path))
    redaction = cfg.get("redaction", {})

    # Must deny sensitive headers
    headers_deny = redaction.get("headers_deny", [])
    assert "authorization" in [h.lower() for h in headers_deny], "Must deny authorization header"
    assert "cookie" in [h.lower() for h in headers_deny], "Must deny cookie header"


def test_allow_probes_exists():
    """Verify probe allowlist is configured."""
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "devdiag.yaml")
    if not os.path.exists(cfg_path):
        pytest.skip("devdiag.yaml not found")

    cfg = yaml.safe_load(open(cfg_path))
    allow_probes = cfg.get("allow_probes", [])

    assert len(allow_probes) > 0, "Must configure at least one allowed probe URL"
    assert all(isinstance(p, str) for p in allow_probes), "All probe patterns must be strings"
