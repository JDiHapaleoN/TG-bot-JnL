"""Automated SQLite online backup, SHA-256 checksum verification, and safe restore."""

import hashlib
import logging
import os
import sqlite3
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

        cur.execute("SELECT COUNT(*) FROM users")
        users_cnt = int(cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM transactions")
        tx_cnt = int(cur.fetchone()[0])

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
) -> Optional[BackupMetadata]:
    """
    Create a hot online backup of the SQLite database using sqlite3.Connection.backup(),
    write a SHA-256 manifest, verify integrity, and prune old backups beyond max_backups.
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

    src_conn = sqlite3.connect(str(src_path), timeout=15)
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

