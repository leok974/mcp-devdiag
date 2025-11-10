"""Tests for suppressions and S3 export functionality."""

import pytest


def test_suppressions_applied():
    """Test that suppressions filter out specified problem codes."""
    from mcp_devdiag.probes.bundle import _apply_suppressions

    problems = ["CSP_MISSING", "CORS_WILDCARD", "PORTAL_ROOT_MISSING"]
    cfg = {
        "suppress": [{"code": "PORTAL_ROOT_MISSING", "reason": "Native toasts; no portal needed"}]
    }

    filtered = _apply_suppressions(problems, cfg)

    assert "CSP_MISSING" in filtered
    assert "CORS_WILDCARD" in filtered
    assert "PORTAL_ROOT_MISSING" not in filtered


def test_suppressions_multiple_codes():
    """Test suppressing multiple problem codes."""
    from mcp_devdiag.probes.bundle import _apply_suppressions

    problems = ["A", "B", "C", "D"]
    cfg = {
        "suppress": [
            {"code": "B"},
            {"code": "D", "reason": "Known issue"},
        ]
    }

    filtered = _apply_suppressions(problems, cfg)

    assert filtered == ["A", "C"]


def test_suppressions_empty_config():
    """Test that empty suppress config doesn't filter anything."""
    from mcp_devdiag.probes.bundle import _apply_suppressions

    problems = ["A", "B", "C"]
    cfg = {}

    filtered = _apply_suppressions(problems, cfg)

    assert filtered == ["A", "B", "C"]


def test_export_redaction_keeps_safe_keys():
    """Test that export only keeps SAFE_KEYS."""
    from mcp_devdiag.export_s3 import _redact

    payload = {
        "ok": True,
        "problems": ["CSP_MISSING"],
        "evidence": {"probe": {"detail": "value"}},
        "score": 5,
        "headers": {"cookie": "secret"},  # Should be removed
        "body": "sensitive",  # Should be removed
    }

    redacted = _redact(payload)

    # Check safe keys are present
    assert "ok" in redacted
    assert "problems" in redacted
    assert "evidence" in redacted
    assert "score" in redacted

    # Check sensitive keys are removed
    assert "headers" not in redacted
    assert "body" not in redacted


def test_export_redaction_nested_dicts():
    """Test that redaction works recursively."""
    from mcp_devdiag.export_s3 import _redact

    payload = {
        "problems": ["X"],
        "evidence": {
            "probe1": {"allowed": "yes"},
            "probe2": {"secret": "no"},  # nested non-safe key
        },
        "unauthorized": {"nested": "data"},  # Should be removed
    }

    redacted = _redact(payload)

    assert "problems" in redacted
    assert "evidence" in redacted
    assert "unauthorized" not in redacted


@pytest.mark.asyncio
async def test_export_snapshot_missing_config():
    """Test that export fails without S3 configuration."""
    from mcp_devdiag.export_s3 import export_snapshot

    with pytest.raises(ValueError, match="S3 export not configured"):
        await export_snapshot({"problems": []}, "test-tenant", {})


@pytest.mark.asyncio
async def test_export_snapshot_missing_bucket():
    """Test that export fails without bucket specified."""
    from mcp_devdiag.export_s3 import export_snapshot

    with pytest.raises(ValueError, match="S3 export not configured"):
        await export_snapshot({"problems": []}, "test-tenant", {"region": "us-east-1"})
