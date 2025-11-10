"""Policy tests for DevDiag production configuration."""

import yaml
from pathlib import Path


def test_prod_sampling_and_no_bodies():
    """Verify production config has safe sampling rates and no body capture."""
    config_path = Path("devdiag.yaml")
    if not config_path.exists():
        # Skip if config doesn't exist (dev mode)
        return

    cfg = yaml.safe_load(config_path.read_text())

    # Check if running in production mode
    if cfg.get("mode", "").startswith("prod"):
        # Sampling rates must be <=5% for production
        assert cfg["sampling"]["frontend_events"] <= 0.05, (
            f"frontend_events sampling rate {cfg['sampling']['frontend_events']} "
            "exceeds 5% limit for production"
        )
        assert cfg["sampling"]["network_spans"] <= 0.05, (
            f"network_spans sampling rate {cfg['sampling']['network_spans']} "
            "exceeds 5% limit for production"
        )

        # Bodies capture must be disabled by design (no key present)
        assert "capture_bodies" not in cfg, "Body capture is not allowed in production mode"
        assert "capture_request_bodies" not in cfg, (
            "Request body capture is not allowed in production mode"
        )
        assert "capture_response_bodies" not in cfg, (
            "Response body capture is not allowed in production mode"
        )


def test_redaction_config_present():
    """Verify redaction configuration is present for sensitive headers."""
    config_path = Path("devdiag.yaml")
    if not config_path.exists():
        return

    cfg = yaml.safe_load(config_path.read_text())

    # Redaction must be configured
    assert "redaction" in cfg, "Redaction configuration must be present"

    redaction = cfg["redaction"]

    # Sensitive headers must be denied
    assert "headers_deny" in redaction, "headers_deny must be configured"
    deny_list = [h.lower() for h in redaction["headers_deny"]]

    required_denies = ["authorization", "cookie", "set-cookie"]
    for header in required_denies:
        assert header in deny_list, f"Header '{header}' must be in headers_deny list"


def test_allow_probes_configured():
    """Verify probe allowlist is configured and non-empty."""
    config_path = Path("devdiag.yaml")
    if not config_path.exists():
        return

    cfg = yaml.safe_load(config_path.read_text())

    # Allow probes must be configured
    assert "allow_probes" in cfg, "allow_probes must be configured"
    assert len(cfg["allow_probes"]) > 0, "allow_probes must not be empty"

    # Each pattern should start with method
    for pattern in cfg["allow_probes"]:
        assert any(
            pattern.startswith(method) for method in ["GET ", "POST ", "HEAD ", "PUT ", "DELETE "]
        ), f"Probe pattern '{pattern}' must start with HTTP method"
