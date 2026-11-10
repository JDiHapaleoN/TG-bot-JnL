"""Automated SQLite online backup, SHA-256 checksum verification, and safe restore."""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from bot.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BackupMetadata:
    backup_path: Path
    checksum_path: Path
    sha256: str
    users_count: int
    transactions_count: int
    recurring_count: int
    created_at: str


def resolve_sqlite_db_path(database_url: Optional[str] = None) -> Optional[Path]:
    """Extract filesystem path from a sqlite/sqlite+aiosqlite URL."""
    url = database_url or settings.database_url
    if not url.startswith("sqlite"):
        return None
    if ":///:memory:" in url or url.endswith(":memory:"):
        return None
    prefix_split = url.split(":///", 1)
    if len(prefix_split) != 2:
        return None
    return Path(prefix_split[1]).resolve()


def _compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_backup_integrity(backup_path: Path) -> BackupMetadata:
    """
    Verify a backup file's SHA-256 checksum, SQLite PRAGMA integrity_check,
    and table readability. Raises RuntimeError if any check fails.
    """
    backup_path = Path(backup_path).resolve()
    if not backup_path.exists() or backup_path.stat().st_size == 0:
        raise RuntimeError(f"Backup file missing or empty: {backup_path}")

    checksum_path = backup_path.with_suffix(backup_path.suffix + ".sha256")
    actual_sha = _compute_sha256(backup_path)
    if checksum_path.exists():
        expected_sha = checksum_path.read_text(encoding="utf-8").strip().split()[0]
        if actual_sha != expected_sha:
            raise RuntimeError(
                f"Backup SHA-256 mismatch for {backup_path}: expected {expected_sha}, got {actual_sha}"
            )

    conn = sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True, timeout=10)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check")
        row = cur.fetchone()
        if not row or row[0] != "ok":
            raise RuntimeError(f"SQLite integrity_check failed on {backup_path}: {row}")

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
    finally:
        conn.close()

    return BackupMetadata(
        backup_path=backup_path,
        checksum_path=checksum_path,
        sha256=actual_sha,
        users_count=users_cnt,
        transactions_count=tx_cnt,
        recurring_count=rec_cnt,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def create_database_backup(
    source_db_path: Optional[Path] = None,
    backup_dir: Optional[Path] = None,
    tag: str = "auto",
    max_backups: int = 30,
    upload_s3: bool = True,
) -> Optional[BackupMetadata]:
    """
    Create a hot online backup of the SQLite database using sqlite3.Connection.backup(),
    write a SHA-256 manifest, verify integrity, and prune old backups beyond max_backups.
    Optionally uploads encrypted backup to S3 cloud storage.
    """
    src_path = Path(source_db_path).resolve() if source_db_path else resolve_sqlite_db_path()
    if not src_path or not src_path.exists():
        return None

    target_dir = Path(backup_dir).resolve() if backup_dir else settings.backup_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    # Ensure backup directory is never the exact same file as source
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    safe_tag = "".join(c for c in tag if c.isalnum() or c in ("-", "_")) or "auto"
    backup_file = target_dir / f"finance_bot_{safe_tag}_{timestamp}.db"
    checksum_file = backup_file.with_suffix(".db.sha256")

    # Step 1: Checkpoint WAL before hot backup to ensure maximum data consistency
    src_conn = sqlite3.connect(str(src_path), timeout=15)
    try:
        try:
            src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.OperationalError:
            pass
        src_conn.commit()
    finally:
        src_conn.close()

    # Step 2: Hot copy via SQLite online backup API
    src_conn = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True, timeout=15)
    dst_conn = sqlite3.connect(str(backup_file), timeout=15)
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    sha256_hex = _compute_sha256(backup_file)
    checksum_file.write_text(f"{sha256_hex}  {backup_file.name}\n", encoding="utf-8")

    try:
        os.chmod(backup_file, 0o600)
        os.chmod(checksum_file, 0o600)
    except OSError:
        pass

    meta = verify_backup_integrity(backup_file)
    logger.info(
        "Database backup created and verified: %s (users=%d, txs=%d, sha256=%s...)",
        backup_file.name,
        meta.users_count,
        meta.transactions_count,
        meta.sha256[:12],
    )

    _prune_old_backups(target_dir, max_backups=max_backups)

    # Step 3: Independent Cloud Backup (S3)
    if upload_s3 and settings.s3_backup_enabled:
        try:
            from bot.services.cloud_backup import upload_encrypted_backup_to_s3
            upload_encrypted_backup_to_s3(backup_file, meta)
        except Exception as cloud_err:
            logger.warning("Cloud S3 backup upload skipped or failed: %s", cloud_err)

    return meta


def _prune_old_backups(backup_dir: Path, max_backups: int = 30) -> None:
    if max_backups <= 0:
        return
    backups = sorted(
        backup_dir.glob("finance_bot_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old_db in backups[max_backups:]:
        old_sha = old_db.with_suffix(".db.sha256")
        try:
            old_db.unlink(missing_ok=True)
            old_sha.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Could not prune old backup %s: %s", old_db, exc)


def list_backups(backup_dir: Optional[Path] = None) -> List[Path]:
    target_dir = Path(backup_dir).resolve() if backup_dir else settings.backup_dir
    if not target_dir.exists():
        return []
    return sorted(
        target_dir.glob("finance_bot_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def restore_database_from_backup(
    backup_path: Path,
    target_db_path: Path,
    safety_backup_dir: Optional[Path] = None,
) -> BackupMetadata:
    """
    Safely restore a verified backup into target_db_path.
    1. Verifies backup integrity and SHA-256 checksum BEFORE touching target_db_path.
    2. Creates a pre-restore safety snapshot if target_db_path already exists.
    3. Restores via SQLite online backup API and verifies the restored target database.
    """
    backup_path = Path(backup_path).resolve()
    target_db_path = Path(target_db_path).resolve()

    # Step 1: Verify source backup first
    source_meta = verify_backup_integrity(backup_path)

    # Step 2: If target DB exists and is non-empty, save a pre-restore safety backup
    if target_db_path.exists() and target_db_path.stat().st_size > 0:
        safe_dir = safety_backup_dir or backup_path.parent
        try:
            create_database_backup(
                source_db_path=target_db_path,
                backup_dir=safe_dir,
                tag="pre_restore_safety",
                upload_s3=False,
            )
        except Exception as exc:
            logger.warning("Pre-restore safety backup skipped: %s", exc)

    target_db_path.parent.mkdir(parents=True, exist_ok=True)

    # Step 3: Perform atomic SQLite backup from backup_path -> target_db_path
    src_conn = sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True, timeout=15)
    dst_conn = sqlite3.connect(str(target_db_path), timeout=15)
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    # Step 4: Verify integrity of the restored target database
    restored_meta = verify_backup_integrity(target_db_path)
    if (
        restored_meta.users_count != source_meta.users_count
        or restored_meta.transactions_count != source_meta.transactions_count
    ):
        raise RuntimeError("Restored database row counts do not match backup!")

    logger.info(
        "Database successfully restored to %s (users=%d, txs=%d)",
        target_db_path,
        restored_meta.users_count,
        restored_meta.transactions_count,
    )
    return restored_meta


def ensure_pre_update_backup(
    source_db_path: Optional[Path] = None,
    backup_dir: Optional[Path] = None,
) -> bool:
    """
    Mandatory pre-update backup gatekeeper.
    - If no database exists yet (clean install): returns True.
    - If database exists: creates hot backup, verifies SHA-256 and integrity.
    - Returns True only if backup exists and is 100% verified.
    - Returns False / raises if backup creation or verification fails.
    """
    src_path = Path(source_db_path).resolve() if source_db_path else resolve_sqlite_db_path()
    if not src_path or not src_path.exists():
        logger.info(
            "Pre-update backup: clean initial install detected (no database at %s). Update permitted.",
            src_path,
        )
        return True

    # Check for empty file
    if src_path.stat().st_size == 0:
        logger.info("Pre-update backup: 0-byte database file; update permitted.")
        return True

    logger.info("Pre-update backup: creating and verifying mandatory backup for %s...", src_path)
    try:
        meta = create_database_backup(
            source_db_path=src_path,
            backup_dir=backup_dir,
            tag="pre_update",
            upload_s3=True,
        )
        if meta is None or not meta.backup_path.exists():
            logger.error("Pre-update backup failed: backup file was not created!")
            return False

        # Additional verification on generated backup
        verified = verify_backup_integrity(meta.backup_path)
        if verified.sha256 != meta.sha256:
            logger.error("Pre-update backup verification failed: SHA-256 mismatch!")
            return False

        logger.info(
            "Pre-update backup SUCCESS: %s verified (users=%d, txs=%d). Update permitted.",
            meta.backup_path.name,
            meta.users_count,
            meta.transactions_count,
        )
        return True
    except Exception as exc:
        logger.critical(
            "FATAL: Pre-update backup failed with error: %s. Aborting update to protect database!",
            exc,
            exc_info=True,
        )
        return False


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    parser = argparse.ArgumentParser(description="JnL-Bot Backup Management Utility")
    parser.add_argument("--pre-update", action="store_true", help="Run mandatory pre-update backup and verification")
    parser.add_argument("--create", action="store_true", help="Create a manual backup")
    parser.add_argument("--tag", type=str, default="manual", help="Tag for manual backup")
    parser.add_argument("--list", action="store_true", help="List available local backups")
    parser.add_argument("--restore", type=Path, default=None, help="Path to backup to restore")
    parser.add_argument("--target", type=Path, default=None, help="Target path for restore")

    args = parser.parse_args()

    if args.pre_update:
        ok = ensure_pre_update_backup()
        sys.exit(0 if ok else 1)

    if args.create:
        meta = create_database_backup(tag=args.tag)
        if meta:
            print(f"Backup created: {meta.backup_path} (users={meta.users_count}, txs={meta.transactions_count})")
            sys.exit(0)
        else:
            print("Failed to create backup (no source database found)")
            sys.exit(1)

    if args.list:
        backups = list_backups()
        print(f"Local backups in {settings.backup_dir}:")
        for b in backups:
            print(f"  {b.name} ({b.stat().st_size} bytes)")
        sys.exit(0)

    if args.restore:
        target = args.target or resolve_sqlite_db_path()
        if not target:
            print("Error: Target database path could not be resolved.")
            sys.exit(1)
        meta = restore_database_from_backup(args.restore, target)
        print(f"Restored successfully to {target} (users={meta.users_count}, txs={meta.transactions_count})")
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
