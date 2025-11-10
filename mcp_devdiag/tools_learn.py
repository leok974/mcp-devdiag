"""MCP tools for closed-loop learning."""

from __future__ import annotations

import time
from typing import Any

from .config import load_config
from .learning.core import Learner, RunRow, canonical_env_fp, make_target_hash

CFG = load_config()
LEARN = Learner(
    store=CFG.learn.store,
    alpha=CFG.learn.alpha,
    beta=CFG.learn.beta,
    min_support=CFG.learn.min_support,
)


async def learn_record_run(payload: dict[str, Any], tenant: str) -> dict[str, Any]:
    """
    Record a diagnostic run for learning.

    Args:
        payload: Diagnostic run payload with base_url, problems, evidence, preset
        tenant: Tenant identifier

    Returns:
        Result dict with ok, run_id, env_fp (or skipped=True if disabled)
    """
    if not CFG.learn.enabled:
        return {"ok": False, "skipped": True}
    env_fp = canonical_env_fp(payload.get("evidence", {}))
    run_id = LEARN.record_run(
        RunRow(
            ts=int(time.time()),
            tenant=tenant,
            target_hash=make_target_hash(payload["base_url"], CFG.learn.privacy.hash_targets),
            env_fp=env_fp,
            problems=payload.get("problems", []),
            evidence=payload.get("evidence", {}),
            preset=payload.get("preset"),
        )
    )
    return {"ok": True, "run_id": run_id, "env_fp": env_fp}


async def learn_suggest(problem_code: str, evidence: dict[str, Any], tenant: str) -> dict[str, Any]:
    """
    Suggest fixes based on learned outcomes.

    Args:
        problem_code: Problem code to find fixes for
        evidence: Environment evidence
        tenant: Tenant identifier

    Returns:
        Result dict with ok, suggestions list (or skipped=True if disabled)
    """
    if not CFG.learn.enabled:
        return {"ok": False, "skipped": True, "suggestions": []}
    out = LEARN.suggest(tenant=tenant, problem_code=problem_code, evidence=evidence or {})
    return {"ok": True, "suggestions": out}
