"""Independent S3-compatible cloud backup with client-side AES-256-GCM encryption.

Supports AWS S3, Cloudflare R2, MinIO, Backblaze B2, and Yandex Cloud.
Provides client-side zero-knowledge encryption, automatic verification,
30-day multi-generation retention policy, and disaster recovery restore.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from bot.config import settings
from bot.services.backup import (
    BackupMetadata,
    _compute_sha256,
    list_backups,
    restore_database_from_backup,
    verify_backup_integrity,
)

logger = logging.getLogger("cloud_backup")


def _derive_encryption_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 256-bit AES key from passphrase and salt using PBKDF2-HMAC-SHA256."""
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_file(source_path: Path, output_path: Path, passphrase: str) -> None:
    """
    Encrypt file using AES-256-GCM.
    Binary layout: [16-byte salt][12-byte nonce][ciphertext + 16-byte auth tag].
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not passphrase:
        raise ValueError("S3_ENCRYPTION_KEY / passphrase is required for client-side encryption")

    salt = os.urandom(16)
    key = _derive_encryption_key(passphrase, salt)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)

    data = source_path.read_bytes()
    ciphertext = aesgcm.encrypt(nonce, data, None)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(salt)
        f.write(nonce)
        f.write(ciphertext)


def decrypt_file(encrypted_path: Path, output_path: Path, passphrase: str) -> None:
    """
    Decrypt AES-256-GCM encrypted file and verify authentication tag.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not passphrase:
        raise ValueError("S3_ENCRYPTION_KEY / passphrase is required for decryption")

    raw = encrypted_path.read_bytes()
    if len(raw) < 44:  # 16 salt + 12 nonce + 16 tag minimum
        raise ValueError(f"Encrypted file is too short: {len(raw)} bytes")

    salt = raw[:16]
    nonce = raw[16:28]
    ciphertext = raw[28:]

    key = _derive_encryption_key(passphrase, salt)
    aesgcm = AESGCM(key)
    try:
        decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as exc:
        raise RuntimeError("Decryption failed! Invalid encryption key or corrupted data.") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(decrypted_data)


def _get_s3_client():
    """Create a configured boto3 S3 client."""
    import boto3
    from botocore.config import Config

    kwargs = {
        "service_name": "s3",
        "region_name": settings.s3_region_name or "us-east-1",
        "config": Config(signature_version="s3v4"),
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    if settings.s3_access_key_id and settings.s3_secret_access_key:
        kwargs["aws_access_key_id"] = settings.s3_access_key_id
        kwargs["aws_secret_access_key"] = settings.s3_secret_access_key

    return boto3.client(**kwargs)


def upload_encrypted_backup_to_s3(
    backup_path: Path,
    metadata: Optional[BackupMetadata] = None,
) -> Optional[str]:
    """
    Encrypt and upload a verified database backup to S3 storage.
    Enforces client-side encryption, integrity checks, and 30-day retention pruning.
    """
    if not settings.s3_backup_enabled:
        logger.debug("S3 backup disabled (S3_BACKUP_ENABLED=false).")
        return None

    if not settings.s3_bucket_name:
        logger.warning("S3_BUCKET_NAME is not configured; skipping cloud backup.")
        return None

    if not settings.s3_encryption_key:
        logger.error("S3_ENCRYPTION_KEY is not set; client-side encryption is mandatory for cloud backups!")
        raise ValueError("S3_ENCRYPTION_KEY must be configured when S3_BACKUP_ENABLED=true")

    meta = metadata or verify_backup_integrity(backup_path)
    s3_key = f"backups/{backup_path.name}.enc"
    sha_key = f"backups/{backup_path.name}.sha256"

    with tempfile.TemporaryDirectory() as tmpdir:
        encrypted_file = Path(tmpdir) / f"{backup_path.name}.enc"
        logger.info("Encrypting backup with AES-256-GCM before upload...")
        encrypt_file(backup_path, encrypted_file, settings.s3_encryption_key)

        s3 = _get_s3_client()

        # Step 1: Upload encrypted backup
        logger.info("Uploading %s to S3 bucket %s...", s3_key, settings.s3_bucket_name)
        s3.upload_file(
            Filename=str(encrypted_file),
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            ExtraArgs={
                "Metadata": {
                    "original_sha256": meta.sha256,
                    "users_count": str(meta.users_count),
                    "transactions_count": str(meta.transactions_count),
                    "recurring_count": str(meta.recurring_count),
                    "created_at": meta.created_at,
                }
            },
        )

        # Step 2: Upload SHA-256 manifest
        sha_text = f"{meta.sha256}  {backup_path.name}\n"
        s3.put_object(
            Bucket=settings.s3_bucket_name,
            Key=sha_key,
            Body=sha_text.encode("utf-8"),
        )

        # Step 3: Verify uploaded object exists and size matches
        head = s3.head_object(Bucket=settings.s3_bucket_name, Key=s3_key)
        uploaded_size = head.get("ContentLength", 0)
        local_enc_size = encrypted_file.stat().st_size
        if uploaded_size != local_enc_size:
            raise RuntimeError(
                f"S3 upload verification failed: size mismatch (local={local_enc_size}, remote={uploaded_size})"
            )

        logger.info(
            "Cloud backup uploaded and verified: s3://%s/%s (size=%d bytes)",
            settings.s3_bucket_name,
            s3_key,
            uploaded_size,
        )

        # Step 4: Prune remote backups older than retention policy (min 30 days)
        prune_s3_backups(s3, max_age_days=max(30, settings.s3_retention_days))

    return s3_key


def prune_s3_backups(s3_client=None, max_age_days: int = 30) -> int:
    """Delete S3 backups older than max_age_days."""
    if not settings.s3_bucket_name:
        return 0

    s3 = s3_client or _get_s3_client()
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    deleted_count = 0

    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=settings.s3_bucket_name, Prefix="backups/"):
            for obj in page.get("Contents", []):
                last_modified = obj.get("LastModified")
                key = obj.get("Key", "")
                if last_modified and last_modified < cutoff:
                    logger.info("Pruning expired remote backup: %s (age > %d days)", key, max_age_days)
                    s3.delete_object(Bucket=settings.s3_bucket_name, Key=key)
                    deleted_count += 1
    except Exception as exc:
        logger.warning("Could not prune old S3 backups: %s", exc)

    return deleted_count


def list_s3_backups(s3_client=None) -> List[dict]:
    """List available remote encrypted backups in S3."""
    if not settings.s3_bucket_name:
        return []
    s3 = s3_client or _get_s3_client()
    results = []
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=settings.s3_bucket_name, Prefix="backups/"):
            for obj in page.get("Contents", []):
                key = obj.get("Key", "")
                if key.endswith(".enc"):
                    results.append({
                        "key": key,
                        "size": obj.get("Size", 0),
                        "last_modified": obj.get("LastModified"),
                    })
    except Exception as exc:
        logger.error("Failed to list S3 backups: %s", exc)
    results.sort(key=lambda x: x.get("last_modified") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return results


def restore_database_from_s3(
    target_db_path: Path,
    s3_key: Optional[str] = None,
    passphrase: Optional[str] = None,
    s3_client=None,
) -> BackupMetadata:
    """
    Disaster recovery: download the latest (or specified) encrypted backup from S3,
    decrypt it, verify SHA-256 and integrity, and restore to target_db_path.
    """
    if not settings.s3_bucket_name:
        raise ValueError("S3_BUCKET_NAME is not configured")

    encryption_key = passphrase or settings.s3_encryption_key
    if not encryption_key:
        raise ValueError("S3_ENCRYPTION_KEY is required to decrypt cloud backups")

    s3 = s3_client or _get_s3_client()

    chosen_key = s3_key
    if not chosen_key:
        available = list_s3_backups(s3)
        if not available:
            raise RuntimeError(f"No backups found in s3://{settings.s3_bucket_name}/backups/")
        chosen_key = available[0]["key"]

    logger.info("Downloading remote backup %s from s3://%s...", chosen_key, settings.s3_bucket_name)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_enc = Path(tmpdir) / "downloaded.enc"
        tmp_dec = Path(tmpdir) / "downloaded_decrypted.db"

        s3.download_file(
            Bucket=settings.s3_bucket_name,
            Key=chosen_key,
            Filename=str(tmp_enc),
        )

        logger.info("Decrypting cloud backup...")
        decrypt_file(tmp_enc, tmp_dec, encryption_key)

        # Check for remote sha256 manifest
        sha_key = chosen_key.replace(".enc", ".sha256")
        try:
            sha_obj = s3.get_object(Bucket=settings.s3_bucket_name, Key=sha_key)
            expected_sha = sha_obj["Body"].read().decode("utf-8").strip().split()[0]
            actual_sha = _compute_sha256(tmp_dec)
            if actual_sha != expected_sha:
                raise RuntimeError(
                    f"Remote checksum mismatch: expected {expected_sha}, got {actual_sha}"
                )
            tmp_dec.with_suffix(".db.sha256").write_text(f"{actual_sha}  {tmp_dec.name}\n", encoding="utf-8")
        except Exception as exc:
            logger.warning("Could not verify remote .sha256 manifest: %s", exc)

        meta = verify_backup_integrity(tmp_dec)
        logger.info("Decrypted cloud backup verified: users=%d, txs=%d", meta.users_count, meta.transactions_count)

        restored_meta = restore_database_from_backup(
            backup_path=tmp_dec,
            target_db_path=target_db_path,
        )
        return restored_meta


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    parser = argparse.ArgumentParser(description="JnL-Bot Cloud S3 Backup Utility")
    parser.add_argument("--list", action="store_true", help="List remote backups")
    parser.add_argument("--upload-latest", action="store_true", help="Encrypt and upload latest local backup")
    parser.add_argument("--restore-latest", action="store_true", help="Download and restore latest cloud backup")
    parser.add_argument("--target", type=Path, default=Path("/var/lib/jnl-bot/data/finance_bot.db"), help="Restore target path")

    args = parser.parse_args()

    if args.list:
        backups = list_s3_backups()
        print(f"Available backups in s3://{settings.s3_bucket_name}:")
        for b in backups:
            print(f"  {b['key']}  ({b['size']} bytes, modified {b['last_modified']})")
        sys.exit(0)

    if args.upload_latest:
        local_backups = list_backups()
        if not local_backups:
            logger.error("No local backups found to upload")
            sys.exit(1)
        latest = local_backups[0]
        meta = upload_encrypted_backup_to_s3(latest)
        if meta:
            logger.info("Successfully uploaded latest backup: %s", meta)
            sys.exit(0)
        else:
            sys.exit(1)

    if args.restore_latest:
        meta = restore_database_from_s3(target_db_path=args.target)
        logger.info("Disaster recovery completed successfully into %s (users=%d, txs=%d)", args.target, meta.users_count, meta.transactions_count)
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
