"""Tests for closed-loop learning functionality."""

from pathlib import Path

import pytest

from mcp_devdiag.learning.core import Learner, RunRow, canonical_env_fp


def test_record_and_suggest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test recording runs and suggesting fixes based on learned outcomes."""
    store = f"sqlite:///{tmp_path}/devdiag.db"
    learner = Learner(store=store, alpha=0.6, beta=0.7, min_support=1)

    # Previous run with CSP problem
    prev = {
        "base_url": "https://app.example.com",
        "problems": ["CSP_INLINE_BLOCKED"],
        "evidence": {
            "framework": "react@18.3.1",
            "xfo": "DENY",
            "csp": "frame-ancestors 'none'",
        },
        "preset": "chat",
    }

    # Current run with problem resolved
    curr = {
        "base_url": "https://app.example.com",
        "problems": [],
        "evidence": {
            "framework": "react@18.3.1",
            "xfo": "DENY",
            "csp": "frame-ancestors 'self'",
        },
        "preset": "chat",
    }

    # Record both runs
    rid1 = learner.record_run(
        RunRow(
            ts=1,
            tenant="t",
            target_hash="h",
            env_fp=canonical_env_fp(prev["evidence"]),
            problems=prev["problems"],
            evidence=prev["evidence"],
            preset="chat",
        )
    )
    assert rid1 > 0

    rid2 = learner.record_run(
        RunRow(
            ts=2,
            tenant="t",
            target_hash="h",
            env_fp=canonical_env_fp(curr["evidence"]),
            problems=curr["problems"],
            evidence=curr["evidence"],
            preset="chat",
        )
    )
    assert rid2 > rid1

    # Auto-label the fix success
    fixes = {"CSP_INLINE_BLOCKED": ["FIX_CSP_NONCE_OR_REMOVE_INLINE"]}
    labeled = learner.autolabel_success("t", prev, curr, fixes)
    assert len(labeled) == 1
    assert labeled[0][0] == "CSP_INLINE_BLOCKED"
    assert labeled[0][1] == "FIX_CSP_NONCE_OR_REMOVE_INLINE"

    # Query suggestions for the same problem
    sugs = learner.suggest("t", "CSP_INLINE_BLOCKED", prev["evidence"])
    assert len(sugs) > 0
    assert sugs[0]["fix_code"].startswith("FIX_CSP_")
    assert "confidence" in sugs[0]
    assert "support" in sugs[0]
    assert sugs[0]["support"] >= 1


def test_canonical_env_fp() -> None:
    """Test environment fingerprint generation."""
    evidence1 = {
        "framework": "react@18.3.1",
        "xfo": "DENY",
        "csp": "frame-ancestors 'self'",
        "server": ["nginx"],
        "routes": ["/api/health"],
        "secret": "should-not-be-included",  # Not in SAFE_KEYS
    }

    evidence2 = {
        "framework": "react@18.3.1",
        "xfo": "DENY",
        "csp": "frame-ancestors 'self'",
        "server": ["nginx"],
        "routes": ["/api/health"],
        "secret": "different-secret",  # Should not affect fingerprint
    }

    fp1 = canonical_env_fp(evidence1)
    fp2 = canonical_env_fp(evidence2)

    # Fingerprints should be identical (secrets excluded)
    assert fp1 == fp2
    assert len(fp1) == 64  # SHA256 hex digest length


def test_suggest_min_support(tmp_path: Path) -> None:
    """Test that suggestions respect min_support threshold."""
    store = f"sqlite:///{tmp_path}/devdiag.db"
    learner = Learner(store=store, alpha=0.6, beta=0.7, min_support=3)

    evidence = {"framework": "vue@3.4.0"}
    env_fp = canonical_env_fp(evidence)

    # Record only 2 successes (below min_support of 3)
    for i in range(2):
        learner.record_run(
            RunRow(
                ts=i,
                tenant="t",
                target_hash="h",
                env_fp=env_fp,
                problems=["FRAMEWORK_OUTDATED"],
                evidence=evidence,
                preset="app",
            )
        )

    # Manually increment support (simulating autolabel)
    from mcp_devdiag.learning.db import update_support

    update_support(
        learner.conn, "t", "FRAMEWORK_OUTDATED", "FIX_UPDATE_FRAMEWORK", env_fp, add=2, conf=0.8
    )

    # Should not suggest (support=2 < min_support=3)
    sugs = learner.suggest("t", "FRAMEWORK_OUTDATED", evidence)
    assert len(sugs) == 0

    # Add one more to reach min_support
    update_support(
        learner.conn, "t", "FRAMEWORK_OUTDATED", "FIX_UPDATE_FRAMEWORK", env_fp, add=1, conf=0.85
    )

    # Should now suggest
    sugs = learner.suggest("t", "FRAMEWORK_OUTDATED", evidence)
    assert len(sugs) == 1
    assert sugs[0]["fix_code"] == "FIX_UPDATE_FRAMEWORK"
    assert sugs[0]["support"] == 3


def test_learner_multiple_tenants(tmp_path: Path) -> None:
    """Test that learning is isolated by tenant."""
    store = f"sqlite:///{tmp_path}/devdiag.db"
    learner = Learner(store=store, alpha=0.6, beta=0.7, min_support=1)

    evidence = {"framework": "react@18.0.0"}
    env_fp = canonical_env_fp(evidence)

    # Record fix for tenant A
    from mcp_devdiag.learning.db import update_support

    update_support(learner.conn, "tenant_a", "REACT_OLD", "FIX_UPGRADE", env_fp, add=5, conf=0.9)

    # Tenant A should see suggestion
    sugs_a = learner.suggest("tenant_a", "REACT_OLD", evidence)
    assert len(sugs_a) == 1
    assert sugs_a[0]["fix_code"] == "FIX_UPGRADE"

    # Tenant B should NOT see suggestion (no data)
    sugs_b = learner.suggest("tenant_b", "REACT_OLD", evidence)
    assert len(sugs_b) == 0
