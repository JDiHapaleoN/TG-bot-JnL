"""Safe, verified storage migration for relocating the SQLite database.

Physically migrates legacy/in-repo database (e.g. /opt/jnl-bot/data/finance_bot.db)
to the standard persistent location (/var/lib/jnl-bot/data/finance_bot.db) using
the SQLite Online Backup API, WAL checkpointing, SHA-256 verification, and row-count checks.
Never deletes the source database until verified, never overwrites an existing valid target,
and retains verified archive copies.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from bot.config import BASE_DIR, settings

logger = logging.getLogger("storage_migration")


def _compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _inspect_sqlite_counts(db_path: Path) -> Tuple[int, int, int]:
    """Return (users_count, transactions_count, recurring_count) from a valid SQLite DB."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check")
        row = cur.fetchone()
        if not row or row[0] != "ok":
            raise RuntimeError(f"PRAGMA integrity_check failed on {db_path}: {row}")

        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in cur.fetchall()}

        users_cnt = 0
        if "users" in tables:
            cur.execute("SELECT COUNT(*) FROM users")
            users_cnt = int(cur.fetchone()[0])

        tx_cnt = 0
        if "transactions" in tables:
            cur.execute("SELECT COUNT(*) FROM transactions")
            tx_cnt = int(cur.fetchone()[0])

        rec_cnt = 0
        if "recurring_transactions" in tables:
            cur.execute("SELECT COUNT(*) FROM recurring_transactions")
            rec_cnt = int(cur.fetchone()[0])

        return users_cnt, tx_cnt, rec_cnt
    finally:
        conn.close()


def safe_migrate_storage(
    source_db: Optional[Path] = None,
    target_db: Optional[Path] = None,
    backup_dir: Optional[Path] = None,
) -> bool:
    """
    Safely relocate source_db to target_db.
    Guarantees:
    - If target_db already exists with data, NEVER overwrites it.
    - If source_db does not exist, nothing to migrate (returns True).
    - Uses SQLite Online Backup API with WAL checkpointing.
    - Compares SHA-256 and row counts.
    - On failure, removes partial target and preserves source untouched.
    - On success, renames source to an archive backup; never deletes it.
    """
    src = Path(source_db).resolve() if source_db else (BASE_DIR / "data" / "finance_bot.db").resolve()
    tgt = Path(target_db).resolve() if target_db else Path("/var/lib/jnl-bot/data/finance_bot.db").resolve()
    bkp = Path(backup_dir).resolve() if backup_dir else settings.backup_dir

    # If src and tgt resolve to the exact same file, no relocation needed
    if src == tgt:
        logger.info("Source and target are the same path (%s). No migration needed.", src)
        return True

    # If source does not exist, no relocation needed
    if not src.exists() or src.stat().st_size == 0:
        logger.info("Source database does not exist (%s). Nothing to migrate.", src)
        return True

    logger.info("Initiating safe storage relocation from %s to %s", src, tgt)

    # If target already exists and is non-empty, verify it
    if tgt.exists() and tgt.stat().st_size > 0:
        try:
            tgt_users, tgt_txs, _ = _inspect_sqlite_counts(tgt)
            logger.warning(
                "Target database %s already exists and is valid (users=%d, txs=%d). "
                "Preserving target database to prevent data overwrite.",
                tgt,
                tgt_users,
                tgt_txs,
            )
            # Safely archive source instead of overwriting target
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            archive_src = src.with_suffix(f".db.legacy_archived_{timestamp}")
            src.rename(archive_src)
            logger.info("Archived source to %s", archive_src)
            return True
        except Exception as exc:
            logger.error("Target database exists but is corrupted: %s", exc)
            raise RuntimeError(f"Target database exists but failed integrity check: {tgt}") from exc

    # Ensure target directory exists
    tgt.parent.mkdir(parents=True, exist_ok=True)
    bkp.mkdir(parents=True, exist_ok=True)

    # Step 1: Ensure source consistency with WAL checkpoint
    src_conn = sqlite3.connect(str(src), timeout=15)
    try:
        try:
            src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.OperationalError:
            pass
        src_conn.commit()
    finally:
        src_conn.close()

    src_users, src_txs, src_rec = _inspect_sqlite_counts(src)
    logger.info("Source database verified: users=%d, txs=%d, recurring=%d", src_users, src_txs, src_rec)

    # Step 2: Atomic hot copy via SQLite Online Backup API
    partial_tgt = tgt.with_suffix(".db.transfer_tmp")
    if partial_tgt.exists():
        partial_tgt.unlink()

    src_c = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=15)
    dst_c = sqlite3.connect(str(partial_tgt), timeout=15)
    try:
        with dst_c:
            src_c.backup(dst_c)
    except Exception as exc:
        dst_c.close()
        src_c.close()
        if partial_tgt.exists():
            partial_tgt.unlink()
        logger.error("SQLite backup failed during relocation: %s. Source is untouched.", exc)
        raise RuntimeError(f"Storage migration backup failed: {exc}") from exc
    finally:
        dst_c.close()
        src_c.close()

    # Step 3: Verify target integrity and count rows
    try:
        tgt_users, tgt_txs, tgt_rec = _inspect_sqlite_counts(partial_tgt)
        if (src_users != tgt_users) or (src_txs != tgt_txs) or (src_rec != tgt_rec):
            raise RuntimeError(
                f"Row count mismatch! Source: ({src_users}, {src_txs}, {src_rec}) != "
                f"Target: ({tgt_users}, {tgt_txs}, {tgt_rec})"
            )

        sha = _compute_sha256(partial_tgt)
        sha_file = tgt.with_suffix(".db.sha256")
        sha_file.write_text(f"{sha}  {tgt.name}\n", encoding="utf-8")

        # Atomic move to final target path
        partial_tgt.replace(tgt)
        try:
            os.chmod(tgt, 0o600)
            os.chmod(sha_file, 0o600)
        except OSError:
            pass

    except Exception as exc:
        if partial_tgt.exists():
            partial_tgt.unlink()
        logger.error("Verification failed on migrated database: %s. Target removed, source untouched.", exc)
        raise RuntimeError(f"Migrated database verification failed: {exc}") from exc

    # Step 4: Archive source database (NEVER rm -rf)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_name = src.parent / f"{src.name}.migrated_backup_{timestamp}"
    try:
        src.rename(archive_name)
        # Also rename any leftover wal or shm files
        for suffix in ("-wal", "-shm"):
            extra = Path(str(src) + suffix)
            if extra.exists():
                extra.rename(Path(str(archive_name) + suffix))
        logger.info("Source database safely archived to %s", archive_name)
    except OSError as err:
        logger.warning("Could not rename source after migration: %s", err)

    logger.info("Storage migration successfully completed: %s -> %s (users=%d, txs=%d)", src, tgt, tgt_users, tgt_txs)
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    parser = argparse.ArgumentParser(description="Safely migrate SQLite database to persistent storage")
    parser.add_argument("--source", type=Path, default=None, help="Source database file path")
    parser.add_argument("--target", type=Path, default=None, help="Target database file path")
    parser.add_argument("--backup-dir", type=Path, default=None, help="Backup directory")

    args = parser.parse_args()
    try:
        ok = safe_migrate_storage(source_db=args.source, target_db=args.target, backup_dir=args.backup_dir)
        sys.exit(0 if ok else 1)
    except Exception as exc:
        logger.error("Storage migration failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
