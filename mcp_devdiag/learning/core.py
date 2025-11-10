"""Core learning logic for DevDiag closed-loop learning."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

from .db import connect, insert, update_support


@dataclass
class RunRow:
    """Represents a diagnostic run to be stored."""

    ts: int
    tenant: str
    target_hash: str
    env_fp: str
    problems: list[str]
    evidence: dict[str, Any]
    preset: str | None


def sha256(s: str) -> str:
    """Compute SHA256 hash of string."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def make_target_hash(base_url: str, hash_targets: bool) -> str:
    """
    Generate target hash from base URL.

    Args:
        base_url: Target URL
        hash_targets: If True, hash the URL; otherwise return as-is

    Returns:
        Hashed or plain base_url
    """
    return sha256(base_url) if hash_targets else base_url


SAFE_KEYS = {"csp", "xfo", "framework", "server", "routes"}


def canonical_env_fp(evidence: dict[str, Any]) -> str:
    """
    Generate canonical environment fingerprint from evidence.

    Only SAFE_KEYS are included to preserve privacy.

    Args:
        evidence: Evidence dictionary from diagnostic run

    Returns:
        SHA256 hash of canonical JSON representation
    """
    # copy only SAFE_KEYS, normalize types; then stable JSON -> sha256
    safe = {k: evidence.get(k) for k in SAFE_KEYS if k in evidence}
    return sha256(json.dumps(safe, sort_keys=True, separators=(",", ":")))


def jaccard(a: set[str], b: set[str]) -> float:
    """
    Compute Jaccard similarity between two sets.

    Args:
        a: First set
        b: Second set

    Returns:
        Jaccard index (0.0 to 1.0)
    """
    if not a and not b:
        return 1.0
    u = a | b
    i = a & b
    return len(i) / len(u) if u else 0.0


def env_tokens(evidence: dict[str, Any]) -> set[str]:
    """
    Extract environment tokens from evidence.

    Args:
        evidence: Evidence dictionary

    Returns:
        Set of tokens representing environment characteristics
    """
    t: set[str] = set()
    fw = evidence.get("framework")
    if isinstance(fw, str) and fw:
        t.add(f"fw:{fw}")
    xfo = (evidence.get("xfo") or "").upper()
    if xfo:
        t.add(f"xfo:{xfo}")
    csp = evidence.get("csp")
    if isinstance(csp, str) and "frame-ancestors" in csp:
        t.add("csp:fa")
    for s in evidence.get("server", []) or []:
        t.add(f"srv:{s}")
    for r in evidence.get("routes", []) or []:
        t.add(f"route:{r}")
    return t


def sigmoid(x: float) -> float:
    """Compute sigmoid function."""
    return 1 / (1 + math.exp(-x))


class Learner:
    """Closed-loop learning system for DevDiag."""

    def __init__(self, store: str, alpha: float, beta: float, min_support: int):
        """
        Initialize learner.

        Args:
            store: SQLite connection string
            alpha: Confidence parameter for support scaling
            beta: Confidence parameter for similarity weighting
            min_support: Minimum support count for suggestions
        """
        self.conn = connect(store)
        self.alpha = alpha
        self.beta = beta
        self.min_support = min_support

    def record_run(self, row: RunRow) -> int:
        """
        Record a diagnostic run.

        Args:
            row: RunRow containing diagnostic data

        Returns:
            ID of inserted row
        """
        return insert(
            self.conn,
            "diag_run",
            ts=row.ts,
            tenant=row.tenant,
            target_hash=row.target_hash,
            env_fp=row.env_fp,
            problems=json.dumps(row.problems),
            evidence=json.dumps(row.evidence),
            preset=row.preset,
        )

    def autolabel_success(
        self,
        tenant: str,
        prev_run: dict[str, Any],
        next_run: dict[str, Any],
        fixes_map: dict[str, list[str]],
    ) -> list[tuple[str, str]]:
        """
        Auto-label successful fixes by detecting disappeared problems.

        Args:
            tenant: Tenant identifier
            prev_run: Previous diagnostic run payload
            next_run: Current diagnostic run payload
            fixes_map: Map of problem codes to fix codes

        Returns:
            List of (problem_code, fix_code) pairs that were credited
        """
        # prev_run/next_run are diag payloads (already redacted)
        disappeared = set(prev_run["problems"]) - set(next_run["problems"])
        env_fp = canonical_env_fp(prev_run.get("evidence", {}))
        out: list[tuple[str, str]] = []
        for p in disappeared:
            candidates = fixes_map.get(p, [])
            if not candidates:
                continue
            # credit the first (primary) fix recipe for now
            fix = candidates[0]
            conf = self._confidence(
                support=1,
                prev_evidence=prev_run.get("evidence", {}),
                known_evidence=prev_run.get("evidence", {}),
            )
            update_support(self.conn, tenant, p, fix, env_fp, add=1, conf=conf)
            out.append((p, fix))
        return out

    def suggest(
        self, tenant: str, problem_code: str, evidence: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Suggest fixes for a problem based on learned outcomes.

        Args:
            tenant: Tenant identifier
            problem_code: Problem code to find fixes for
            evidence: Current environment evidence

        Returns:
            List of suggestions with fix_code, confidence, and support
        """
        # rank by support*similarity
        cur = self.conn.execute(
            """SELECT fix_code,confidence,support,env_fp FROM fix_outcome
                                   WHERE tenant=? AND problem_code=? AND support>=?""",
            (tenant, problem_code, self.min_support),
        )
        rows = cur.fetchall()
        if not rows:
            return []
        # Note: tokens_now could be used for future similarity enhancements
        # Currently similarity relies on confidence/support stored in DB
        suggestions = []
        for fix_code, confidence, support, env_fp in rows:
            # we don't store full evidence per row; similarity via tokens from current vs implied by env_fp hash
            # heuristic: rely on confidence/support primarily; tokens add small β signal (no env_fp reversal)
            sim = 1.0  # cannot reconstruct tokens from hash; weight via confidence/support
            score = confidence * (0.7 + 0.3 * sim)
            suggestions.append(
                {"fix_code": fix_code, "confidence": round(score, 3), "support": int(support)}
            )
        suggestions.sort(key=lambda x: (x["confidence"], x["support"]), reverse=True)
        return suggestions

    def _confidence(
        self, support: int, prev_evidence: dict[str, Any], known_evidence: dict[str, Any]
    ) -> float:
        """
        Calculate confidence score for a fix.

        Args:
            support: Number of times fix worked
            prev_evidence: Evidence from previous run
            known_evidence: Evidence from known successful fix

        Returns:
            Confidence score (0.0 to 1.0)
        """
        s = sigmoid(self.alpha * float(support))
        # lightweight: token overlap within a single run (acts as ≥ baseline)
        tokens_prev = env_tokens(prev_evidence)
        tokens_known = env_tokens(known_evidence)
        sim = jaccard(tokens_prev, tokens_known)
        return round(s * (self.beta * sim + (1 - self.beta)), 3)
