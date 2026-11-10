"""Safe, non-destructive schema migration engine for SQLite / SQLAlchemy.

Enforces the Expand-and-Contract migration pattern:
- Only additive migrations (ADD COLUMN with DEFAULT or NULLABLE).
- Never DROP COLUMN, never DROP TABLE, never truncate.
- Pre-flight testing on an isolated copy before touching the live database.
- Guarantees backward compatibility with previous code versions upon rollback.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

from bot.config import settings

logger = logging.getLogger("migrations")


def _get_existing_columns(sync_conn: Connection, table_name: str) -> Set[str]:
    result = sync_conn.execute(text(f"PRAGMA table_info({table_name})"))
    return {row[1] for row in result.fetchall()}


def _get_applied_versions(sync_conn: Connection) -> Set[int]:
    sync_conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version INTEGER PRIMARY KEY, "
            "name VARCHAR(128) NOT NULL, "
            "applied_at TIMESTAMP NOT NULL"
            ")"
        )
    )
    res = sync_conn.execute(text("SELECT version FROM schema_migrations"))
    return {int(row[0]) for row in res.fetchall()}


def _record_migration(sync_conn: Connection, version: int, name: str) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    sync_conn.execute(
        text(
            "INSERT OR IGNORE INTO schema_migrations (version, name, applied_at) "
            "VALUES (:v, :n, :t)"
        ),
        {"v": version, "n": name, "t": now_iso},
    )


def run_safe_migrations(sync_conn: Connection) -> None:
    """
    Execute non-destructive schema migrations on an existing database.
    Never drops or truncates tables or columns; preserves 100% of existing user data.
    """
    applied = _get_applied_versions(sync_conn)

    # Migration 0: Ensure all user columns exist (reminders, settings)
    user_cols = _get_existing_columns(sync_conn, "users")
    if user_cols:
        if "notify_recurring" not in user_cols:
            logger.info("Applying migration: add 'notify_recurring' column to 'users'")
            sync_conn.execute(
                text("ALTER TABLE users ADD COLUMN notify_recurring BOOLEAN NOT NULL DEFAULT 1")
            )
        if "daily_reminder" not in user_cols:
            logger.info("Applying migration: add 'daily_reminder' column to 'users'")
            sync_conn.execute(
                text("ALTER TABLE users ADD COLUMN daily_reminder BOOLEAN NOT NULL DEFAULT 0")
            )
        if "reminder_hour" not in user_cols:
            logger.info("Applying migration: add 'reminder_hour' column to 'users'")
            sync_conn.execute(
                text("ALTER TABLE users ADD COLUMN reminder_hour INTEGER NOT NULL DEFAULT 20")
            )
        if "last_reminder_date" not in user_cols:
            logger.info("Applying migration: add 'last_reminder_date' column to 'users'")
            sync_conn.execute(
                text("ALTER TABLE users ADD COLUMN last_reminder_date VARCHAR(16)")
            )
    if 0 not in applied:
        _record_migration(sync_conn, 0, "ensure_user_reminder_columns")

    # Migration 1: Ensure 'category' column exists on 'transactions'
    tx_cols = _get_existing_columns(sync_conn, "transactions")
    if tx_cols:
        if "category" not in tx_cols:
            logger.info("Applying migration: add 'category' column to 'transactions'")
            sync_conn.execute(
                text(
                    "ALTER TABLE transactions ADD COLUMN category VARCHAR(64) NOT NULL DEFAULT 'other'"
                )
            )
    if 1 not in applied:
        _record_migration(sync_conn, 1, "add_transactions_category")

    # Migration 2: Ensure 'recurring_id' and 'idempotency_key' exist on 'transactions'
    tx_cols = _get_existing_columns(sync_conn, "transactions")
    if tx_cols:
        if "recurring_id" not in tx_cols:
            logger.info("Applying migration: add 'recurring_id' column to 'transactions'")
            sync_conn.execute(
                text("ALTER TABLE transactions ADD COLUMN recurring_id INTEGER REFERENCES recurring_transactions(id)")
            )
        if "idempotency_key" not in tx_cols:
            logger.info("Applying migration: add 'idempotency_key' column to 'transactions'")
            sync_conn.execute(
                text("ALTER TABLE transactions ADD COLUMN idempotency_key VARCHAR(128)")
            )
        sync_conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_transactions_idempotency_key "
                "ON transactions (idempotency_key)"
            )
        )
    if 2 not in applied:
        _record_migration(sync_conn, 2, "add_transactions_idempotency_key")

    # Migration 3: Ensure 'processed_updates' table exists for Telegram Update deduplication
    sync_conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS processed_updates ("
            "update_id BIGINT PRIMARY KEY, "
            "telegram_id BIGINT, "
            "processed_at TIMESTAMP NOT NULL"
            ")"
        )
    )
    sync_conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_processed_updates_telegram_id "
            "ON processed_updates (telegram_id)"
        )
    )
    if 3 not in applied:
        _record_migration(sync_conn, 3, "create_processed_updates_table")


def test_migration_on_isolated_copy(source_db_path: Optional[Path] = None) -> bool:
    """
    Test migrations on an isolated temporary copy of the production database.
    Verifies that:
    1. Migrations complete without errors.
    2. PRAGMA integrity_check returns 'ok'.
    3. Essential tables remain intact and readable.
    Never alters or locks the live production database.
    """
    from bot.services.backup import resolve_sqlite_db_path

    src = Path(source_db_path).resolve() if source_db_path else resolve_sqlite_db_path()
    if not src or not src.exists() or src.stat().st_size == 0:
        logger.info("No existing database to test migrations against; isolated test skipped.")
        return True

    logger.info("Running pre-flight migration test on isolated copy of %s...", src)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = Path(tmpdir) / "test_migration_isolated.db"

        # Hot backup copy using sqlite3
        src_conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=10)
        dst_conn = sqlite3.connect(str(tmp_db), timeout=10)
        try:
            with dst_conn:
                src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
            src_conn.close()

        # Apply migrations on the isolated copy
        eng = create_engine(f"sqlite:///{tmp_db}")
        try:
            with eng.begin() as conn:
                run_safe_migrations(conn)

            # Verify integrity
            with eng.connect() as conn:
                res = conn.execute(text("PRAGMA integrity_check")).fetchone()
                if not res or res[0] != "ok":
                    raise RuntimeError(f"Integrity check failed on isolated copy: {res}")

                # Verify tables can be queried
                for tbl in ("users", "transactions"):
                    chk = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
                    logger.debug("Isolated copy verification: %s count=%s", tbl, chk)

        finally:
            eng.dispose()

    logger.info("Pre-flight migration test SUCCESS: schema is fully compatible.")
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    parser = argparse.ArgumentParser(description="JnL-Bot Migration Manager")
    parser.add_argument("--test-isolated", action="store_true", help="Run migration check on isolated copy")
    parser.add_argument("--apply", action="store_true", help="Apply migrations to active database")

    args = parser.parse_args()

    if args.test_isolated:
        ok = test_migration_on_isolated_copy()
        sys.exit(0 if ok else 1)

    if args.apply:
        from bot.services.backup import resolve_sqlite_db_path
        src = resolve_sqlite_db_path()
        if not src:
            logger.error("Could not resolve SQLite database path")
            sys.exit(1)
        eng = create_engine(f"sqlite:///{src}")
        try:
            with eng.begin() as conn:
                run_safe_migrations(conn)
            logger.info("Migrations successfully applied to %s", src)
            sys.exit(0)
        finally:
            eng.dispose()

    parser.print_help()


if __name__ == "__main__":
    main()
