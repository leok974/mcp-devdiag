"""Database helper for closed-loop learning (SQLite by default)."""

from __future__ import annotations

import os
import sqlite3
import time
from typing import Any


def _ensure_dir(path: str) -> None:
    """Ensure parent directory exists for database file."""
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def connect(store: str) -> sqlite3.Connection:
    """
    Connect to SQLite database with WAL mode.

    Args:
        store: Connection string like "sqlite:///devdiag.db"

    Returns:
        SQLite connection with tables created

    Raises:
        AssertionError: If store is not a sqlite:// URL
    """
    # Only sqlite supported here; allow "sqlite:///file.db"
    assert store.startswith("sqlite://"), "Only sqlite is implemented in this helper"

    # Handle both sqlite:///path/to/file.db and sqlite:///C:/path/to/file.db (Windows)
    path = store.replace("sqlite:///", "", 1)
    if not path:
        path = store.replace("sqlite://", "", 1)

    _ensure_dir(path)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.execute("PRAGMA journal_mode = WAL;")

    # Table: diagnostic runs
    conn.execute(
        """
    CREATE TABLE IF NOT EXISTS diag_run(
      id INTEGER PRIMARY KEY,
      ts INTEGER NOT NULL,
      tenant TEXT NOT NULL,
      target_hash TEXT NOT NULL,
      env_fp TEXT NOT NULL,
      problems TEXT NOT NULL, -- JSON array
      evidence TEXT NOT NULL, -- JSON (top-level safe keys only)
      preset TEXT
    );"""
    )

    # Table: fix outcomes (learned successes)
    conn.execute(
        """
    CREATE TABLE IF NOT EXISTS fix_outcome(
      id INTEGER PRIMARY KEY,
      ts INTEGER NOT NULL,
      tenant TEXT NOT NULL,
      problem_code TEXT NOT NULL,
      fix_code TEXT NOT NULL,
      confidence REAL NOT NULL,
      support INTEGER NOT NULL,
      env_fp TEXT NOT NULL,
      notes TEXT,
      UNIQUE(tenant, problem_code, fix_code, env_fp)
    );"""
    )

    return conn


def rowcount(conn: sqlite3.Connection, table: str) -> int:
    """Count rows in a table."""
    result = conn.execute(f"SELECT COUNT(1) FROM {table}").fetchone()
    return int(result[0]) if result else 0


def insert(conn: sqlite3.Connection, table: str, **cols: Any) -> int:
    """
    Insert a row into a table.

    Args:
        conn: Database connection
        table: Table name
        **cols: Column name-value pairs

    Returns:
        Last inserted row ID
    """
    keys = ",".join(cols.keys())
    qs = ",".join(["?"] * len(cols))
    cur = conn.execute(f"INSERT INTO {table}({keys}) VALUES({qs})", tuple(cols.values()))
    last_id = cur.lastrowid
    return last_id if last_id is not None else 0


def update_support(
    conn: sqlite3.Connection,
    tenant: str,
    problem: str,
    fix: str,
    env_fp: str,
    add: int,
    conf: float,
) -> None:
    """
    Update or insert fix outcome support count.

    Args:
        conn: Database connection
        tenant: Tenant identifier
        problem: Problem code
        fix: Fix code
        env_fp: Environment fingerprint
        add: Support count to add
        conf: Updated confidence score
    """
    cur = conn.execute(
        """SELECT id,support FROM fix_outcome
                          WHERE tenant=? AND problem_code=? AND fix_code=? AND env_fp=?""",
        (tenant, problem, fix, env_fp),
    )
    row = cur.fetchone()
    if row:
        conn.execute(
            "UPDATE fix_outcome SET support=support+?, confidence=? WHERE id=?", (add, conf, row[0])
        )
    else:
        insert(
            conn,
            "fix_outcome",
            ts=int(time.time()),
            tenant=tenant,
            problem_code=problem,
            fix_code=fix,
            confidence=conf,
            support=add,
            env_fp=env_fp,
            notes=None,
        )
