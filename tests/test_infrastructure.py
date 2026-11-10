"""Comprehensive infrastructure verification suite:

1. DB copy failure during storage relocation: source DB remains intact.
2. Missing or corrupt pre-update backup: GitHub update is blocked.
3. Disk space exhaustion or write failure simulation: data preserved, update aborted.
4. Corrupted backup: restoration is rejected, target DB protected.
5. Source and target row-count mismatch: relocation is aborted.
6. Backward-compatible migration (Expand & Contract) and code rollback.
7. Systemd service / single-instance flock protection against split-brain.
8. Data preservation across full upgrade lifecycle.
9. Cloud S3 client-side encrypted backup, tamper detection, and disaster recovery.
10. SQLite runtime WAL mode, synchronous=FULL, and concurrency stress verification.
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.database.crud import (
    add_transaction,
    create_or_update_user,
    get_user_balance,
    get_user_by_telegram_id,
    get_user_transactions,
)
from bot.database.migrations import run_safe_migrations, test_migration_on_isolated_copy
from bot.database.models import Base
from bot.database.session import configure_sqlite_engine, init_db
from main import _acquire_single_instance_lock
from bot.services.backup import (
    create_database_backup,
    ensure_pre_update_backup,
    restore_database_from_backup,
    verify_backup_integrity,
)
from bot.services.cloud_backup import (
    decrypt_file,
    encrypt_file,
    restore_database_from_s3,
    upload_encrypted_backup_to_s3,
)
from bot.services.storage_migration import _inspect_sqlite_counts, safe_migrate_storage


def _make_engine(db_path: Path):
    url = f"sqlite+aiosqlite:///{db_path}"
    eng = create_async_engine(url, echo=False, connect_args={"timeout": 15.0})
    configure_sqlite_engine(eng)
    return eng


class InfrastructureReliabilitySuite(unittest.IsolatedAsyncioTestCase):

    async def test_01_migration_copy_failure_preserves_source(self) -> None:
        """
        Тест 1: Ошибка копирования базы во время переноса.
        Исходная база остаётся нетронутой, частичный целевой файл удаляется.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src_db = Path(tmpdir) / "source.db"
            tgt_db = Path(tmpdir) / "target.db"

            # Populate source DB
            eng = _make_engine(src_db)
            await init_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)
            async with sf() as session:
                u = await create_or_update_user(session, 900001, "Source User", currency="EUR")
                await add_transaction(session, u.id, "income", Decimal("150.00"), "EUR", "Original Income")
            await eng.dispose()

            src_size_before = src_db.stat().st_size
            self.assertGreater(src_size_before, 0)

            # Simulate failure during sqlite3.backup via connect wrapper
            orig_connect = sqlite3.connect
            call_count = 0

            def _failing_connect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                conn = orig_connect(*args, **kwargs)
                if call_count >= 2:
                    mock_conn = MagicMock(wraps=conn)
                    mock_conn.backup.side_effect = sqlite3.OperationalError("Simulated disk read error")
                    return mock_conn
                return conn

            with patch("bot.services.storage_migration.sqlite3.connect", side_effect=_failing_connect):
                with self.assertRaises(RuntimeError):
                    safe_migrate_storage(source_db=src_db, target_db=tgt_db)

            # Target DB must not exist or be empty
            self.assertFalse(tgt_db.exists())
            # Source DB must be completely preserved
            self.assertTrue(src_db.exists())
            self.assertEqual(src_db.stat().st_size, src_size_before)

            # Verify source data is intact
            eng_check = _make_engine(src_db)
            sf_check = async_sessionmaker(eng_check, expire_on_commit=False)
            async with sf_check() as session:
                u_check = await get_user_by_telegram_id(session, 900001)
                self.assertIsNotNone(u_check)
                self.assertEqual(await get_user_balance(session, u_check.id), Decimal("150.00"))
            await eng_check.dispose()

    async def test_02_missing_or_corrupt_pre_update_backup_aborts_update(self) -> None:
        """
        Тест 2: Отсутствие или ошибка резервной копии.
        GitHub-обновление не начинается (ensure_pre_update_backup возвращает False).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "corrupt.db"
            backup_dir = Path(tmpdir) / "backups"

            # 1. Clean initial install (no DB) -> True (permitted)
            clean_db = Path(tmpdir) / "non_existent.db"
            self.assertTrue(ensure_pre_update_backup(clean_db, backup_dir))

            # 2. Corrupt DB file -> False (update strictly aborted)
            db_path.write_bytes(b"NOT A VALID SQLITE HEADER CORRUPTED FILE CONTENT")
            ok = ensure_pre_update_backup(db_path, backup_dir)
            self.assertFalse(ok)

    async def test_03_disk_space_or_write_failure_simulation(self) -> None:
        """
        Тест 3: Недостаточно места на диске.
        Данные сохраняются, резервная копия прерывается, обновление отменяется.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src_db = Path(tmpdir) / "live.db"
            backup_dir = Path(tmpdir) / "backups"

            eng = _make_engine(src_db)
            await init_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)
            async with sf() as session:
                u = await create_or_update_user(session, 900003, "Disk User", currency="EUR")
                await add_transaction(session, u.id, "income", Decimal("777.00"), "EUR", "Salary")
            await eng.dispose()

            # Simulate OSError [Errno 28] No space left on device during backup
            with patch("bot.services.backup.create_database_backup", side_effect=OSError(28, "No space left on device")):
                ok = ensure_pre_update_backup(src_db, backup_dir)
                self.assertFalse(ok)

            # Live DB remains completely intact
            eng_check = _make_engine(src_db)
            sf_check = async_sessionmaker(eng_check, expire_on_commit=False)
            async with sf_check() as session:
                u_check = await get_user_by_telegram_id(session, 900003)
                self.assertIsNotNone(u_check)
                self.assertEqual(await get_user_balance(session, u_check.id), Decimal("777.00"))
            await eng_check.dispose()

    async def test_04_corrupted_backup_restore_rejected(self) -> None:
        """
        Тест 4: Повреждённый backup.
        Восстановление запрещено, целевая база защищена от перезаписи битыми данными.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            valid_db = Path(tmpdir) / "original.db"
            target_db = Path(tmpdir) / "target.db"
            backup_dir = Path(tmpdir) / "backups"

            eng = _make_engine(valid_db)
            await init_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)
            async with sf() as session:
                u = await create_or_update_user(session, 900004, "Original Target", currency="EUR")
                await add_transaction(session, u.id, "income", Decimal("1000.00"), "EUR", "Target Baseline")
            await eng.dispose()

            # Create backup
            meta = create_database_backup(valid_db, backup_dir, tag="corrupt_test")
            self.assertIsNotNone(meta)

            # Intentionally corrupt the backup bytes
            with open(meta.backup_path, "r+b") as f:
                f.seek(100)
                f.write(b"CORRUPTED_BYTES_IN_SQLITE_PAGE")

            # Restore must fail with RuntimeError
            with self.assertRaises(RuntimeError):
                restore_database_from_backup(meta.backup_path, target_db)

            # Target DB must not be overwritten
            self.assertFalse(target_db.exists())

    async def test_05_source_target_rowcount_mismatch_aborts_relocation(self) -> None:
        """
        Тест 5: Несовпадение исходной и целевой базы.
        Перенос отменяется, целевой файл удаляется, исходная база остаётся нетронутой.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src_db = Path(tmpdir) / "src_mismatch.db"
            tgt_db = Path(tmpdir) / "tgt_mismatch.db"

            eng = _make_engine(src_db)
            await init_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)
            async with sf() as session:
                u = await create_or_update_user(session, 900005, "Mismatch User", currency="EUR")
                await add_transaction(session, u.id, "income", Decimal("50.00"), "EUR", "Tx 1")
                await add_transaction(session, u.id, "expense", Decimal("20.00"), "EUR", "Tx 2")
            await eng.dispose()

            # Mock _inspect_sqlite_counts to simulate rowcount mismatch on target
            orig_inspect = _inspect_sqlite_counts
            call_count = 0

            def _flawed_inspect(p):
                nonlocal call_count
                call_count += 1
                users, txs, rec = orig_inspect(p)
                if call_count > 1:  # target inspection
                    return users, txs - 1, rec  # simulated missing transaction!
                return users, txs, rec

            with patch("bot.services.storage_migration._inspect_sqlite_counts", side_effect=_flawed_inspect):
                with self.assertRaises(RuntimeError):
                    safe_migrate_storage(src_db, tgt_db)

            self.assertFalse(tgt_db.exists())
            self.assertTrue(src_db.exists())

    async def test_06_backward_compatible_migration_and_code_rollback(self) -> None:
        """
        Тест 6: Обновление с миграцией и последующий rollback кода.
        Expand and Contract: добавленные колонки имеют default, старый код работает с новой схемой.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "migration_rollback.db"

            # 1. Base v0 schema (older code)
            raw = sqlite3.connect(str(db_path))
            raw.executescript(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    name VARCHAR(120) NOT NULL,
                    currency VARCHAR(8) NOT NULL,
                    timezone VARCHAR(64) NOT NULL,
                    language VARCHAR(8) NOT NULL,
                    is_registered BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL
                );
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    tx_type VARCHAR(16) NOT NULL,
                    amount NUMERIC(14, 2) NOT NULL,
                    currency VARCHAR(8) NOT NULL,
                    description VARCHAR(255),
                    created_at TIMESTAMP NOT NULL
                );
                INSERT INTO users (id, telegram_id, name, currency, timezone, language, is_registered, created_at)
                VALUES (1, 900006, 'Old User', 'EUR', 'UTC', 'ru', 1, '2026-01-01 10:00:00');
                INSERT INTO transactions (id, user_id, tx_type, amount, currency, description, created_at)
                VALUES (1, 1, 'income', 1000.00, 'EUR', 'Initial Salary', '2026-01-01 10:05:00');
                """
            )
            raw.commit()
            raw.close()

            # 2. Test migration on isolated copy before touching live DB
            self.assertTrue(test_migration_on_isolated_copy(db_path))

            # 3. Apply safe migrations (adds category, idempotency_key, etc. with defaults)
            sync_eng = create_engine(f"sqlite:///{db_path}")
            with sync_eng.begin() as conn:
                run_safe_migrations(conn)
            sync_eng.dispose()

            # 4. Simulate CODE ROLLBACK: execute queries written for the OLDER code version
            # Older code executes SELECT without knowing 'category' or 'idempotency_key'
            raw_rolled_back = sqlite3.connect(str(db_path))
            cur = raw_rolled_back.cursor()
            cur.execute("SELECT id, user_id, tx_type, amount, currency, description FROM transactions WHERE user_id = 1")
            rows = cur.fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][3], 1000.00)

            # Older code can also INSERT new records without specifying new columns (they take defaults)
            cur.execute(
                "INSERT INTO transactions (user_id, tx_type, amount, currency, description, created_at) "
                "VALUES (1, 'expense', 25.50, 'EUR', 'Old Style Insert', '2026-01-02 12:00:00')"
            )
            raw_rolled_back.commit()

            cur.execute("SELECT COUNT(*) FROM transactions WHERE user_id = 1")
            self.assertEqual(cur.fetchone()[0], 2)
            raw_rolled_back.close()

    async def test_07_systemd_service_and_single_instance_flock(self) -> None:
        """
        Тест 7: Защита от дублирующего запуска процессов через flock на bot.lock.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_dir = Path(tmpdir)
            with patch("main.resolve_sqlite_db_path", return_value=lock_dir / "finance_bot.db"):
                # First instance acquires lock successfully
                h1 = _acquire_single_instance_lock()
                self.assertIsNotNone(h1)

                # Second instance attempted concurrently returns None
                h2 = _acquire_single_instance_lock()
                self.assertIsNone(h2)

                # Once first instance releases lock, next instance can acquire
                h1.close()
                h3 = _acquire_single_instance_lock()
                self.assertIsNotNone(h3)
                h3.close()

    async def test_08_full_upgrade_lifecycle_data_preservation(self) -> None:
        """
        Тест 8: Проверка сохранности данных после полноценного обновления:
        - v1: создание данных
        - pre-update backup
        - миграция на изолированной копии
        - применение миграции к рабочей базе
        - v2: добавление новых данных
        - верификация всех данных v1 и v2
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "lifecycle.db"
            bkp_dir = Path(tmpdir) / "backups"

            eng1 = _make_engine(db_path)
            await init_db(eng1)
            sf1 = async_sessionmaker(eng1, expire_on_commit=False)
            async with sf1() as session:
                u = await create_or_update_user(session, 900008, "Lifecycle User", currency="EUR")
                await add_transaction(session, u.id, "income", Decimal("3000.00"), "EUR", "Salary V1")
                await add_transaction(session, u.id, "expense", Decimal("150.00"), "EUR", "Groceries V1")
            await eng1.dispose()

            # Step 1: Pre-update backup
            self.assertTrue(ensure_pre_update_backup(db_path, bkp_dir))

            # Step 2: Test migrations on isolated copy
            self.assertTrue(test_migration_on_isolated_copy(db_path))

            # Step 3: Run safe migrations on live DB
            eng2 = _make_engine(db_path)
            await init_db(eng2)
            sf2 = async_sessionmaker(eng2, expire_on_commit=False)
            async with sf2() as session:
                u2 = await get_user_by_telegram_id(session, 900008)
                # v2 adds transaction with new category system
                await add_transaction(
                    session, u2.id, "expense", Decimal("45.00"), "EUR", "Такси V2", category="transport"
                )
                bal = await get_user_balance(session, u2.id)
                self.assertEqual(bal, Decimal("2805.00"))
                txs, total = await get_user_transactions(session, u2.id, limit=10)
                self.assertEqual(total, 3)

            await eng2.dispose()

    async def test_09_cloud_s3_encrypted_backup_and_disaster_recovery(self) -> None:
        """
        Тест 9: Восстановление базы из удалённого облачного хранилища:
        - Клиентское шифрование AES-256-GCM
        - Проверка невозможности прочесть шифротекст без ключа
        - Загрузка в S3 (моделирование через mock/boto3)
        - Полное удаление локальной базы (Disaster recovery)
        - Скачивание, расшифровка, проверка SHA-256 и целостности
        - 100% восстановление всех записей
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source_db = tmp / "s3_source.db"
            backup_dir = tmp / "local_backups"
            disaster_target = tmp / "restored_after_disaster.db"
            passphrase = "SuperSecretMasterEncryptionKey2026!#"

            eng = _make_engine(source_db)
            await init_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)
            async with sf() as session:
                u = await create_or_update_user(session, 900009, "Cloud User", currency="USD")
                await add_transaction(session, u.id, "income", Decimal("5000.00"), "USD", "Consulting")
                await add_transaction(session, u.id, "expense", Decimal("1250.00"), "USD", "MacBook Pro")
            await eng.dispose()

            # 1. Create local backup
            meta = create_database_backup(source_db, backup_dir, tag="cloud_test", upload_s3=False)
            self.assertIsNotNone(meta)

            # 2. Test AES-256-GCM encryption & decryption
            enc_file = tmp / "backup.enc"
            dec_file = tmp / "decrypted.db"
            encrypt_file(meta.backup_path, enc_file, passphrase, iterations=1000)

            # Encrypted file is not valid SQLite
            with self.assertRaises(sqlite3.DatabaseError):
                sqlite3.connect(str(enc_file)).execute("SELECT * FROM users")

            # Wrong key fails decryption
            with self.assertRaises(RuntimeError):
                decrypt_file(enc_file, dec_file, "WrongKey123")

            # Correct key decrypts perfectly
            decrypt_file(enc_file, dec_file, passphrase)
            self.assertEqual(meta.sha256, verify_backup_integrity(dec_file).sha256)

            # 3. Simulate S3 cloud disaster recovery
            s3_mock = MagicMock()
            s3_objects = {}

            def _upload(Filename, Bucket, Key, ExtraArgs=None):
                s3_objects[Key] = Path(Filename).read_bytes()

            def _download(Bucket, Key, Filename):
                Path(Filename).write_bytes(s3_objects[Key])

            def _head(Bucket, Key):
                return {"ContentLength": len(s3_objects[Key])}

            def _get_obj(Bucket, Key):
                return {"Body": MagicMock(read=lambda: s3_objects[Key])}

            def _list_paginator(*args, **kwargs):
                paginator_mock = MagicMock()
                paginator_mock.paginate.return_value = [{
                    "Contents": [{"Key": k, "Size": len(v), "LastModified": None} for k, v in s3_objects.items()]
                }]
                return paginator_mock

            s3_mock.upload_file.side_effect = _upload
            s3_mock.download_file.side_effect = _download
            s3_mock.head_object.side_effect = _head
            s3_mock.get_object.side_effect = _get_obj
            s3_mock.get_paginator.side_effect = _list_paginator

            with patch("bot.services.cloud_backup.settings") as mock_settings:
                mock_settings.s3_backup_enabled = True
                mock_settings.s3_bucket_name = "test-finance-backups"
                mock_settings.s3_encryption_key = passphrase
                mock_settings.s3_retention_days = 30
                mock_settings.s3_region_name = "us-east-1"
                mock_settings.s3_endpoint_url = ""
                mock_settings.s3_access_key_id = "test-key"
                mock_settings.s3_secret_access_key = "test-secret"
                mock_settings.s3_pbkdf2_iterations = 1000

                # Upload to S3
                with patch("bot.services.cloud_backup._get_s3_client", return_value=s3_mock):
                    s3_key = upload_encrypted_backup_to_s3(meta.backup_path, meta)
                    self.assertIsNotNone(s3_key)

                    # Simulate total local loss and restore from S3
                    restored_meta = restore_database_from_s3(
                        target_db_path=disaster_target,
                        s3_key=s3_key,
                        passphrase=passphrase,
                        s3_client=s3_mock,
                    )
                    self.assertEqual(restored_meta.users_count, 1)
                    self.assertEqual(restored_meta.transactions_count, 2)

                    # Verify restored DB has full user records and balance
                    eng_restored = _make_engine(disaster_target)
                    sf_restored = async_sessionmaker(eng_restored, expire_on_commit=False)
                    async with sf_restored() as session:
                        u_r = await get_user_by_telegram_id(session, 900009)
                        self.assertIsNotNone(u_r)
                        self.assertEqual(await get_user_balance(session, u_r.id), Decimal("3750.00"))
                    await eng_restored.dispose()

    async def test_10_wal_mode_and_synchronous_runtime_verification(self) -> None:
        """
        Тест 10: Проверка корректной работы WAL на используемой версии SQLite.
        - journal_mode == 'wal'
        - synchronous == 2 (FULL)
        - busy_timeout == 15000
        - foreign_keys == 1 (ON)
        - Стресс-тест конкурентных операций (10 writers + 20 readers)
        """
        from bot.database.check_sqlite import run_concurrency_stress_test, verify_runtime_pragmas

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "wal_verify.db"
            pragmas = await verify_runtime_pragmas(db_path)

            self.assertEqual(pragmas["journal_mode"], "wal")
            self.assertEqual(pragmas["synchronous"], 2)  # FULL
            self.assertEqual(pragmas["busy_timeout"], 15000)
            self.assertEqual(pragmas["foreign_keys"], 1)

            # Concurrent stress test under WAL
            ok = await run_concurrency_stress_test(db_path, writers_count=10, reads_count=20)
            self.assertTrue(ok)

    async def test_11_monitoring_system_probes_and_alerts(self) -> None:
        """
        Тест 11: Проверка работы мониторинга, проверки диска, SQLite и отправки алертов админу.
        """
        from bot.services.monitoring import (
            check_disk_space,
            check_sqlite_health,
            load_monitoring_state,
            record_backup_failure,
            record_cloud_backup_success,
            record_local_backup_success,
            run_system_health_check,
            send_admin_alert,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            test_db = Path(tmpdir) / "mon_test.db"
            eng = _make_engine(test_db)
            await init_db(eng)
            await eng.dispose()

            # 1. Probe disk space
            disk = check_disk_space(Path(tmpdir))
            self.assertIn("free_gb", disk)
            self.assertIn("total_gb", disk)
            self.assertIn("free_pct", disk)

            # 2. Probe SQLite health
            sql = check_sqlite_health(test_db)
            self.assertTrue(sql["accessible"])
            self.assertTrue(sql["is_healthy"])
            self.assertEqual(sql["integrity"], "ok")

            # 3. State recording
            record_local_backup_success("test_backup.db")
            record_cloud_backup_success("backups/test_backup.db.enc")
            state = load_monitoring_state()
            self.assertEqual(state.last_local_backup_file, "test_backup.db")
            self.assertEqual(state.last_cloud_backup_key, "backups/test_backup.db.enc")
            self.assertEqual(state.consecutive_backup_failures, 0)

            record_backup_failure("S3 bucket access denied")
            state2 = load_monitoring_state()
            self.assertEqual(state2.consecutive_backup_failures, 1)

            # 4. Telegram admin alert dispatch & cooldown
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock(return_value=True)

            with patch("bot.services.monitoring.settings") as mon_settings:
                mon_settings.admin_telegram_id = 123456789
                mon_settings.backup_dir = Path(tmpdir)

                # First alert dispatches
                sent1 = await send_admin_alert(
                    mock_bot,
                    alert_key="unit_alert_test",
                    title="Test Alert",
                    details="Disk warning test",
                    force=False,
                )
                self.assertTrue(sent1)
                mock_bot.send_message.assert_awaited_once()

                # Second identical alert within cooldown period is suppressed
                mock_bot.send_message.reset_mock()
                sent2 = await send_admin_alert(
                    mock_bot,
                    alert_key="unit_alert_test",
                    title="Test Alert",
                    details="Disk warning test",
                    force=False,
                )
                self.assertFalse(sent2)
                mock_bot.send_message.assert_not_awaited()

    async def test_12_encryption_backward_compatibility(self) -> None:
        """
        Тест 12: Обратная совместимость шифрования бэкапов:
        - Version 1 (с заголовком JNLENC\x01 и 600,000 итерациями)
        - Version 0 (legacy без заголовка и 100,000 итерациями)
        - Проверка успешной расшифровки обоих форматов
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from bot.services.cloud_backup import _derive_encryption_key, MAGIC_HEADER

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            passphrase = "BackwardCompatibilitySecretKey2026!"
            payload = b"SQLITE_DATABASE_BINARY_PAYLOAD_ABC123"

            plain_src = tmp / "plain.db"
            plain_src.write_bytes(payload)

            # 1. Create Version 1 encrypted file (new format)
            enc_v1 = tmp / "backup_v1.enc"
            dec_v1 = tmp / "decrypted_v1.db"
            encrypt_file(plain_src, enc_v1, passphrase, iterations=1000)

            # Verify it starts with magic header
            self.assertTrue(enc_v1.read_bytes().startswith(MAGIC_HEADER))
            decrypt_file(enc_v1, dec_v1, passphrase)
            self.assertEqual(dec_v1.read_bytes(), payload)

            # 2. Create raw Version 0 encrypted file (legacy format without magic header, 100k iterations)
            enc_v0 = tmp / "backup_v0.enc"
            dec_v0 = tmp / "decrypted_v0.db"
            salt_v0 = os.urandom(16)
            key_v0 = _derive_encryption_key(passphrase, salt_v0, iterations=100_000)
            nonce_v0 = os.urandom(12)
            aesgcm = AESGCM(key_v0)
            ct_v0 = aesgcm.encrypt(nonce_v0, payload, None)
            with open(enc_v0, "wb") as f:
                f.write(salt_v0)
                f.write(nonce_v0)
                f.write(ct_v0)

            # Verify Version 0 does NOT have the magic header
            self.assertFalse(enc_v0.read_bytes().startswith(MAGIC_HEADER))

            # Decrypt Version 0 using our unified decrypt_file
            decrypt_file(enc_v0, dec_v0, passphrase)
            self.assertEqual(dec_v0.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
