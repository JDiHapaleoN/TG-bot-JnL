"""Safe, non-destructive schema migration engine for SQLite / SQLAlchemy."""

import logging
from datetime import datetime, timezone
from typing import Set

from sqlalchemy import text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


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

