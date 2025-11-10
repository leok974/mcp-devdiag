#!/usr/bin/env python3
"""Sync SQLite learning database to PostgreSQL analytics warehouse.

Usage:
    python scripts/sync_sqlite_to_pg.py

Environment variables:
    SQLITE_PATH: Path to SQLite database (default: devdiag.db)
    PG_DSN: PostgreSQL connection string (required)
        Example: postgresql://devdiag:password@localhost:5432/devdiag

This script performs one-way sync from SQLite to Postgres:
- Inserts new diag_run records (idempotent via natural key check)
- Upserts fix_outcome records (accumulates support counts)
"""

import os
import sqlite3
import sys
from typing import Any

try:
    import psycopg2
    from psycopg2.extras import execute_batch
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)

# Configuration
SQLITE_PATH = os.getenv("SQLITE_PATH", "devdiag.db")
PG_DSN = os.getenv("PG_DSN")

if not PG_DSN:
    print("ERROR: PG_DSN environment variable required", file=sys.stderr)
    print("Example: export PG_DSN='postgresql://devdiag:pass@localhost:5432/devdiag'")
    sys.exit(1)


def rows(conn: sqlite3.Connection, table: str) -> list[tuple[Any, ...]]:
    """Fetch all rows from SQLite table."""
    return conn.execute(f"SELECT * FROM {table}").fetchall()


def sync_diag_runs(sqlite_conn: sqlite3.Connection, pg_cursor: Any) -> int:
    """
    Sync diag_run records from SQLite to Postgres.

    Returns:
        Number of records inserted
    """
    runs = rows(sqlite_conn, "diag_run")
    if not runs:
        return 0

    # Convert SQLite rows to Postgres format
    # SQLite: (id, ts, tenant, target_hash, env_fp, problems, evidence, preset)
    values = [
        (
            f"to_timestamp({ts})",  # Convert Unix timestamp to Postgres timestamp
            tenant,
            target_hash,
            env_fp,
            problems,  # Already JSON string
            evidence,  # Already JSON string
            preset,
        )
        for (id_, ts, tenant, target_hash, env_fp, problems, evidence, preset) in runs
    ]

    # Batch insert with conflict handling (skip duplicates)
    sql = """
    INSERT INTO devdiag.diag_run (ts, tenant, target_hash, env_fp, problems, evidence, preset)
    VALUES (to_timestamp(%s), %s, %s, %s, %s::jsonb, %s::jsonb, %s)
    ON CONFLICT DO NOTHING
    """

    inserted = 0
    for ts, tenant, target_hash, env_fp, problems, evidence, preset in values:
        pg_cursor.execute(sql, (ts, tenant, target_hash, env_fp, problems, evidence, preset))
        inserted += pg_cursor.rowcount

    return inserted


def sync_fix_outcomes(sqlite_conn: sqlite3.Connection, pg_cursor: Any) -> int:
    """
    Sync fix_outcome records from SQLite to Postgres.

    Accumulates support counts on conflict (same tenant/problem/fix/env_fp).

    Returns:
        Number of records upserted
    """
    outcomes = rows(sqlite_conn, "fix_outcome")
    if not outcomes:
        return 0

    # SQLite: (id, ts, tenant, problem_code, fix_code, confidence, support, env_fp, notes)
    sql = """
    INSERT INTO devdiag.fix_outcome (ts, tenant, problem_code, fix_code, confidence, support, env_fp, notes)
    VALUES (to_timestamp(%s), %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (tenant, problem_code, fix_code, env_fp) DO UPDATE
    SET support = devdiag.fix_outcome.support + EXCLUDED.support,
        confidence = EXCLUDED.confidence,
        ts = EXCLUDED.ts
    """

    upserted = 0
    for id_, ts, tenant, problem_code, fix_code, confidence, support, env_fp, notes in outcomes:
        pg_cursor.execute(sql, (ts, tenant, problem_code, fix_code, confidence, support, env_fp, notes))
        upserted += 1

    return upserted


def main() -> None:
    """Main sync logic."""
    print(f"Connecting to SQLite: {SQLITE_PATH}")
    if not os.path.exists(SQLITE_PATH):
        print(f"ERROR: SQLite database not found: {SQLITE_PATH}", file=sys.stderr)
        sys.exit(1)

    sqlite_conn = sqlite3.connect(SQLITE_PATH)

    print(f"Connecting to PostgreSQL: {PG_DSN.split('@')[1] if '@' in PG_DSN else 'localhost'}")
    try:
        pg_conn = psycopg2.connect(PG_DSN)
        pg_cursor = pg_conn.cursor()
    except Exception as e:
        print(f"ERROR: Failed to connect to PostgreSQL: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        # Sync diag_run records
        print("Syncing diag_run records...")
        runs_inserted = sync_diag_runs(sqlite_conn, pg_cursor)
        print(f"  ✓ Inserted {runs_inserted} diag_run records")

        # Sync fix_outcome records
        print("Syncing fix_outcome records...")
        outcomes_upserted = sync_fix_outcomes(sqlite_conn, pg_cursor)
        print(f"  ✓ Upserted {outcomes_upserted} fix_outcome records")

        # Commit transaction
        pg_conn.commit()
        print("\n✅ Sync completed successfully")

    except Exception as e:
        pg_conn.rollback()
        print(f"\n❌ Sync failed: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        sqlite_conn.close()
        pg_cursor.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
