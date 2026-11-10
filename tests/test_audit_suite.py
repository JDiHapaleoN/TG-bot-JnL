from __future__ import annotations

import asyncio
import datetime as dt
import logging
import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.database.crud import (
    add_transaction,
    create_or_update_user,
    create_recurring_transaction,
    delete_recurring_transaction,
    delete_transaction,
    get_recurring_by_id,
    get_transaction_by_id,
    get_user_balance,
    get_user_by_telegram_id,
    get_user_statistics,
    get_user_transactions,
    process_due_recurring_for_user,
    toggle_recurring_transaction,
    update_transaction,
    update_user_fields,
)
from bot.database.session import configure_sqlite_engine, init_db
from bot.database.models import Base
from bot.handlers.transactions import _handle_transaction_entry
from bot.middlewares.reliability import ReliabilityMiddleware, SecretRedactingFilter
from bot.services.backup import (
    BackupMetadata,
    create_database_backup,
    restore_database_from_backup,
    verify_backup_integrity,
)
from bot.webapp.server import verify_telegram_init_data


def _make_sqlite_engine(db_path: Path):
    url = f"sqlite+aiosqlite:///{db_path}"
    eng = create_async_engine(url, echo=False, connect_args={"timeout": 15.0})
    configure_sqlite_engine(eng)
    return eng


async def _init_test_db(eng) -> None:
    await init_db(eng)


class AuditReliabilitySuite(unittest.IsolatedAsyncioTestCase):
    """
    Comprehensive 10-scenario verification suite covering data persistence,
    user isolation, idempotency, atomic transactions, schema migrations,
    recurring payments, concurrency, and backup/restore integrity.
    """

    async def test_01_app_update_data_preservation(self) -> None:
        """
        Тест 1 — сохранение данных при обновлении приложения:
        1. Создать тестового пользователя.
        2. Добавить 50 расходов и 10 доходов.
        3. Обновить приложение / применить миграции.
        4. Проверить, что все записи, баланс и статистика полностью сохранились.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test1_update.db"
            eng = _make_sqlite_engine(db_path)
            await _init_test_db(eng)
            session_factory = async_sessionmaker(eng, expire_on_commit=False)

            expected_expenses = Decimal("0.00")
            expected_incomes = Decimal("0.00")

            async with session_factory() as session:
                user = await create_or_update_user(
                    session,
                    telegram_id=700001,
                    name="Alex Test",
                    phone="+491512345678",
                    country_code="DE",
                    country_name="Germany",
                    currency="EUR",
                    tz_name="Europe/Berlin",
                    language="ru",
                )
                for i in range(1, 51):
                    amt = Decimal(f"{i}.25")
                    expected_expenses += amt
                    await add_transaction(
                        session,
                        user_id=user.id,
                        tx_type="expense",
                        amount=amt,
                        currency="EUR",
                        description=f"Expense #{i}",
                        idempotency_key=f"t1:exp:{i}",
                    )
                for j in range(1, 11):
                    amt = Decimal(f"{j * 100}.50")
                    expected_incomes += amt
                    await add_transaction(
                        session,
                        user_id=user.id,
                        tx_type="income",
                        amount=amt,
                        currency="EUR",
                        description=f"Income #{j}",
                        idempotency_key=f"t1:inc:{j}",
                    )

            await eng.dispose()

            # Simulate application update + schema migration pass
            eng_after_update = _make_sqlite_engine(db_path)
            await _init_test_db(eng_after_update)
            session_factory_after = async_sessionmaker(eng_after_update, expire_on_commit=False)

            async with session_factory_after() as session:
                user_after = await get_user_by_telegram_id(session, 700001)
                self.assertIsNotNone(user_after)
                txs, total_count = await get_user_transactions(session, user_after.id, limit=100)
                self.assertEqual(total_count, 60)
                self.assertEqual(len(txs), 60)

                balance = await get_user_balance(session, user_after.id)
                self.assertEqual(balance, expected_incomes - expected_expenses)

                stats = await get_user_statistics(session, user_after)
                self.assertEqual(stats.total_expense, expected_expenses)
                self.assertEqual(stats.total_income, expected_incomes)
                self.assertEqual(stats.balance, expected_incomes - expected_expenses)

            await eng_after_update.dispose()

    async def test_02_server_restart_persistence(self) -> None:
        """
        Тест 2 — сохранение данных при перезапуске сервера:
        1. Добавить несколько операций.
        2. Полностью остановить соединения и пересоздать движок БД.
        3. Проверить, что данные не изменились.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test2_restart.db"
            eng1 = _make_sqlite_engine(db_path)
            await _init_test_db(eng1)
            sf1 = async_sessionmaker(eng1, expire_on_commit=False)

            async with sf1() as session:
                u = await create_or_update_user(
                    session,
                    telegram_id=700002,
                    name="Maria",
                    phone="+49111111",
                    country_code="DE",
                    country_name="Germany",
                    currency="EUR",
                    tz_name="Europe/Berlin",
                )
                await add_transaction(session, u.id, "income", Decimal("2500.00"), "EUR", "Зарплата")
                await add_transaction(session, u.id, "expense", Decimal("19.99"), "EUR", "Книга")
                await add_transaction(session, u.id, "expense", Decimal("4.50"), "EUR", "Кофе")

            # Simulate full server shutdown
            await eng1.dispose()

            # Simulate fresh startup
            eng2 = _make_sqlite_engine(db_path)
            await _init_test_db(eng2)
            sf2 = async_sessionmaker(eng2, expire_on_commit=False)

            async with sf2() as session:
                u2 = await get_user_by_telegram_id(session, 700002)
                self.assertIsNotNone(u2)
                bal = await get_user_balance(session, u2.id)
                self.assertEqual(bal, Decimal("2475.51"))
                txs, total = await get_user_transactions(session, u2.id, limit=10)
                self.assertEqual(total, 3)
                self.assertEqual(txs[0].description, "Кофе")

            await eng2.dispose()

    async def test_03_user_isolation_and_ownership(self) -> None:
        """
        Тест 3 — изоляция пользователей:
        1. Создать двух пользователей.
        2. Добавить операции и регулярные платежи каждому.
        3. Проверить, что данные, редактирование и удаление полностью изолированы.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test3_isolation.db"
            eng = _make_sqlite_engine(db_path)
            await _init_test_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)

            async with sf() as session:
                u1 = await create_or_update_user(
                    session,
                    telegram_id=800001,
                    name="User One",
                    phone="+10001",
                    country_code="DE",
                    country_name="Germany",
                    currency="EUR",
                    tz_name="Europe/Berlin",
                )
                u2 = await create_or_update_user(
                    session,
                    telegram_id=800002,
                    name="User Two",
                    phone="+10002",
                    country_code="US",
                    country_name="USA",
                    currency="USD",
                    tz_name="America/New_York",
                )

                tx1 = await add_transaction(session, u1.id, "income", Decimal("1000.00"), "EUR", "U1 Income")
                tx2 = await add_transaction(session, u2.id, "expense", Decimal("50.00"), "USD", "U2 Expense")

                rec1 = await create_recurring_transaction(
                    session=session,
                    user_id=u1.id,
                    title="Netflix",
                    amount=Decimal("15.00"),
                    currency="EUR",
                    tx_type="expense",
                    period="monthly",
                    next_run_date="2026-11-09",
                )

                # User 2 cannot fetch, edit, or delete User 1's transaction
                self.assertIsNone(await get_transaction_by_id(session, tx1.id, user_id=u2.id))
                self.assertIsNone(
                    await update_transaction(
                        session, tx1.id, user_id=u2.id, amount=Decimal("1.00"), description="Hacked"
                    )
                )
                self.assertFalse(await delete_transaction(session, tx1.id, user_id=u2.id))

                # User 2 cannot fetch, toggle, or delete User 1's recurring item
                self.assertIsNone(await get_recurring_by_id(session, rec1.id, user_id=u2.id))
                self.assertIsNone(await toggle_recurring_transaction(session, rec1.id, user_id=u2.id))
                self.assertFalse(await delete_recurring_transaction(session, rec1.id, user_id=u2.id))

                # Balances remain strictly separated
                self.assertEqual(await get_user_balance(session, u1.id), Decimal("1000.00"))
                self.assertEqual(await get_user_balance(session, u2.id), Decimal("-50.00"))
                self.assertIsNotNone(await get_transaction_by_id(session, tx2.id, user_id=u2.id))

                # Verify WebApp HMAC authentication rejects missing or forged initData
                self.assertIsNone(verify_telegram_init_data("", "fake:token"))
                self.assertIsNone(verify_telegram_init_data("user=%7B%22id%22%3A800001%7D&hash=deadbeef", "fake:token"))

            await eng.dispose()

    async def test_04_duplicate_telegram_update_idempotency(self) -> None:
        """
        Тест 4 — защита от дублирования:
        1. Отправить одно и то же событие дважды (через ReliabilityMiddleware и через idempotency_key).
        2. Убедиться, что создаётся только одна запись.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test4_idempotency.db"
            eng = _make_sqlite_engine(db_path)
            await _init_test_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)

            async with sf() as session:
                u = await create_or_update_user(
                    session,
                    telegram_id=800004,
                    name="Idem User",
                    phone="+49004",
                    country_code="DE",
                    country_name="Germany",
                    currency="EUR",
                    tz_name="Europe/Berlin",
                )
                # 1. Duplicate idempotency_key at CRUD level
                first_tx = await add_transaction(
                    session,
                    u.id,
                    "expense",
                    Decimal("25.00"),
                    "EUR",
                    "Обед",
                    idempotency_key="msg:800004:991",
                )
                second_tx = await add_transaction(
                    session,
                    u.id,
                    "expense",
                    Decimal("25.00"),
                    "EUR",
                    "Обед",
                    idempotency_key="msg:800004:991",
                )
                self.assertEqual(first_tx.id, second_tx.id)
                _, total = await get_user_transactions(session, u.id, limit=10)
                self.assertEqual(total, 1)

            # 2. Duplicate Telegram update_id at middleware level
            middleware = ReliabilityMiddleware(session_factory=sf)
            handler_mock = AsyncMock(return_value="ok")
            fake_user = SimpleNamespace(id=800004, language_code="ru")
            fake_msg = SimpleNamespace(from_user=fake_user, answer=AsyncMock())
            fake_update = SimpleNamespace(
                update_id=555001,
                message=fake_msg,
                callback_query=None,
            )

            await middleware(handler_mock, fake_update, {})
            await middleware(handler_mock, fake_update, {})

            self.assertEqual(handler_mock.await_count, 1)
            await eng.dispose()

    async def test_05_db_failure_never_sends_false_confirmation(self) -> None:
        """
        Тест 5 — ошибка базы данных во время сохранения:
        1. Смоделировать ошибку записи в БД.
        2. Убедиться, что бот НЕ отправляет ложное подтверждение сохранения и баланс не меняется.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test5_dbfail.db"
            eng = _make_sqlite_engine(db_path)
            await _init_test_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)

            async with sf() as session:
                await create_or_update_user(
                    session,
                    telegram_id=800005,
                    name="FailSafe User",
                    phone="+49005",
                    country_code="DE",
                    country_name="Germany",
                    currency="EUR",
                    tz_name="Europe/Berlin",
                    language="ru",
                )

            fake_message = SimpleNamespace(
                from_user=SimpleNamespace(id=800005),
                chat=SimpleNamespace(id=800005),
                message_id=101,
                text="45.50 | Такси",
                answer=AsyncMock(),
            )
            fake_state = SimpleNamespace(clear=AsyncMock())

            with (
                patch("bot.handlers.transactions.async_session_factory", sf),
                patch(
                    "bot.handlers.transactions.add_transaction",
                    side_effect=sqlite3.OperationalError("simulated disk full"),
                ),
            ):
                await _handle_transaction_entry(fake_message, fake_state, default_type="expense")

            fake_message.answer.assert_awaited_once()
            sent_text = fake_message.answer.await_args.args[0]
            self.assertIn("Не удалось сохранить операцию", sent_text)
            self.assertNotIn("Расход сохранён", sent_text)

            async with sf() as session:
                u = await get_user_by_telegram_id(session, 800005)
                bal = await get_user_balance(session, u.id)
                self.assertEqual(bal, Decimal("0.00"))

            await eng.dispose()

    async def test_06_profile_update_preserves_history(self) -> None:
        """
        Тест 6 — изменение профиля:
        1. Изменить имя, телефон, страну, валюту, часовой пояс и язык.
        2. Проверить, что вся история транзакций и привязка к telegram_id сохранились.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test6_profile.db"
            eng = _make_sqlite_engine(db_path)
            await _init_test_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)

            async with sf() as session:
                u = await create_or_update_user(
                    session,
                    telegram_id=800006,
                    name="Initial Name",
                    phone="+49123",
                    country_code="DE",
                    country_name="Germany",
                    currency="EUR",
                    tz_name="Europe/Berlin",
                    language="ru",
                )
                await add_transaction(session, u.id, "income", Decimal("500.00"), "EUR", "Bonus")
                await add_transaction(session, u.id, "expense", Decimal("120.00"), "EUR", "Groceries")

                updated = await update_user_fields(
                    session,
                    telegram_id=800006,
                    name="Updated Name",
                    phone="+41791234567",
                    country_code="CH",
                    country_name="Switzerland",
                    currency="CHF",
                    timezone="Europe/Zurich",
                    language="en",
                )
                self.assertEqual(updated.id, u.id)
                self.assertEqual(updated.telegram_id, 800006)
                self.assertEqual(updated.name, "Updated Name")
                self.assertEqual(updated.currency, "CHF")
                self.assertEqual(updated.timezone, "Europe/Zurich")

                # Re-running create_or_update_user with existing user preserves profile
                safe_user = await create_or_update_user(
                    session,
                    telegram_id=800006,
                    name="Updated Name",
                    currency="CHF",
                    tz_name="Europe/Zurich",
                )
                self.assertEqual(safe_user.name, "Updated Name")
                self.assertEqual(safe_user.currency, "CHF")

                txs, total = await get_user_transactions(session, u.id, limit=10)
                self.assertEqual(total, 2)
                self.assertEqual(await get_user_balance(session, u.id), Decimal("380.00"))

            await eng.dispose()

    async def test_07_legacy_schema_migration_preserves_data(self) -> None:
        """
        Тест 7 — миграция схемы базы данных:
        1. Создать БД со старой схемой (без колонок category и idempotency_key) и заполнить данными.
        2. Применить новую миграцию (run_safe_migrations).
        3. Проверить, что старые записи не потерялись и корректно читаются новой моделью.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test7_legacy.db"
            # Create legacy v0 schema using raw sqlite3 without category / idempotency_key
            raw_conn = sqlite3.connect(str(db_path))
            raw_conn.executescript(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id BIGINT NOT NULL UNIQUE,
                    name VARCHAR(128) NOT NULL DEFAULT 'User',
                    phone VARCHAR(64),
                    country_code VARCHAR(8) NOT NULL DEFAULT 'DE',
                    country_name VARCHAR(128) NOT NULL DEFAULT 'Germany',
                    currency VARCHAR(8) NOT NULL DEFAULT 'EUR',
                    timezone VARCHAR(64) NOT NULL DEFAULT 'Europe/Berlin',
                    language VARCHAR(8) NOT NULL DEFAULT 'ru',
                    is_registered BOOLEAN NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL
                );
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    tx_type VARCHAR(16) NOT NULL,
                    amount NUMERIC(14, 2) NOT NULL,
                    currency VARCHAR(8) NOT NULL DEFAULT 'EUR',
                    description VARCHAR(512),
                    is_recurring BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL
                );
                INSERT INTO users (id, telegram_id, name, phone, country_code, country_name, currency, timezone, language, is_registered, created_at)
                VALUES (1, 800007, 'Legacy User', '+49777', 'DE', 'Germany', 'EUR', 'Europe/Berlin', 'ru', 1, '2026-01-15 10:00:00');
                INSERT INTO transactions (user_id, tx_type, amount, currency, description, is_recurring, created_at)
                VALUES (1, 'income', 1500.00, 'EUR', 'Legacy Salary', 0, '2026-01-15 10:05:00');
                INSERT INTO transactions (user_id, tx_type, amount, currency, description, is_recurring, created_at)
                VALUES (1, 'expense', 42.30, 'EUR', 'Legacy Cafe', 0, '2026-01-15 12:00:00');
                """
            )
            raw_conn.commit()
            raw_conn.close()

            # Now connect with current engine and run safe migrations
            eng = _make_sqlite_engine(db_path)
            await _init_test_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)

            async with sf() as session:
                u = await get_user_by_telegram_id(session, 800007)
                self.assertIsNotNone(u)
                self.assertEqual(u.name, "Legacy User")

                bal = await get_user_balance(session, u.id)
                self.assertEqual(bal, Decimal("1457.70"))

                txs, total = await get_user_transactions(session, u.id, limit=10)
                self.assertEqual(total, 2)
                self.assertEqual(txs[0].category, "other")

                # New transactions with category & idempotency_key work seamlessly
                new_tx = await add_transaction(
                    session,
                    u.id,
                    "expense",
                    Decimal("7.70"),
                    "EUR",
                    "Метро",
                    idempotency_key="legacy:new:1",
                )
                self.assertEqual(new_tx.category, "transport")
                self.assertEqual(await get_user_balance(session, u.id), Decimal("1450.00"))

            await eng.dispose()

    async def test_08_recurring_operations_restart_and_idempotency(self) -> None:
        """
        Тест 8 — регулярные операции:
        1. Создать регулярную операцию.
        2. Перезапустить сервер в день списания и вызвать обработчик повторно.
        3. Проверить, что операция не потерялась и не списалась дважды.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test8_recurring.db"
            eng = _make_sqlite_engine(db_path)
            await _init_test_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)

            async with sf() as session:
                u = await create_or_update_user(
                    session,
                    telegram_id=800008,
                    name="Rec User",
                    phone="+49008",
                    country_code="DE",
                    country_name="Germany",
                    currency="EUR",
                    tz_name="UTC",
                )
                rec = await create_recurring_transaction(
                    session=session,
                    user_id=u.id,
                    title="Gym Membership",
                    amount=Decimal("29.99"),
                    currency="EUR",
                    tx_type="expense",
                    period="daily",
                    next_run_date="2026-11-10",
                )

                # First run on due date creates 1 transaction
                created_1 = await process_due_recurring_for_user(
                    session, u, current_local_date="2026-11-10"
                )
                self.assertEqual(len(created_1), 1)

                # Second run on the same day creates 0 transactions
                created_2 = await process_due_recurring_for_user(
                    session, u, current_local_date="2026-11-10"
                )
                self.assertEqual(len(created_2), 0)

                # Even if last run date is rewound, idempotency_key prevents duplicate
                rec.next_run_date = "2026-11-10"
                await session.commit()

                created_3 = await process_due_recurring_for_user(
                    session, u, current_local_date="2026-11-10"
                )
                self.assertEqual(len(created_3), 0)

                _, total = await get_user_transactions(session, u.id, limit=10)
                self.assertEqual(total, 1)
                self.assertEqual(await get_user_balance(session, u.id), Decimal("-29.99"))

            await eng.dispose()

    async def test_09_concurrent_rapid_requests(self) -> None:
        """
        Тест 9 — конкурентные запросы:
        1. Отправить серию быстрых сообщений подряд.
        2. Проверить, что все операции обработаны корректно без гонок и блокировок.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test9_concurrency.db"
            eng = _make_sqlite_engine(db_path)
            await _init_test_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)

            async with sf() as session:
                u = await create_or_update_user(
                    session,
                    telegram_id=800009,
                    name="Fast User",
                    phone="+49009",
                    country_code="DE",
                    country_name="Germany",
                    currency="EUR",
                    tz_name="Europe/Berlin",
                )
                uid = u.id

            async def _rapid_worker(idx: int) -> None:
                async with sf() as s:
                    await add_transaction(
                        s,
                        user_id=uid,
                        tx_type="expense",
                        amount=Decimal("1.10"),
                        currency="EUR",
                        description=f"Rapid #{idx}",
                        idempotency_key=f"rapid:800009:{idx}",
                    )

            await asyncio.gather(*[_rapid_worker(i) for i in range(20)])

            async with sf() as session:
                bal = await get_user_balance(session, uid)
                self.assertEqual(bal, Decimal("-22.00"))
                _, total = await get_user_transactions(session, uid, limit=50)
                self.assertEqual(total, 20)

            await eng.dispose()

    async def test_10_backup_and_restore_verification(self) -> None:
        """
        Тест 10 — восстановление из резервной копии:
        1. Создать резервную копию базы данных.
        2. Проверить контрольную сумму SHA-256 и PRAGMA integrity_check.
        3. Восстановить базу в тестовом окружении и проверить 100% сохранность данных.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source_db = tmp_path / "source_finance.db"
            backup_dir = tmp_path / "backups"
            restored_db = tmp_path / "restored_finance.db"

            eng = _make_sqlite_engine(source_db)
            await _init_test_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)

            async with sf() as session:
                u = await create_or_update_user(
                    session,
                    telegram_id=800010,
                    name="Backup User",
                    phone="+49010",
                    country_code="DE",
                    country_name="Germany",
                    currency="EUR",
                    tz_name="Europe/Berlin",
                )
                await add_transaction(session, u.id, "income", Decimal("3000.00"), "EUR", "Salary")
                await add_transaction(session, u.id, "expense", Decimal("750.25"), "EUR", "Rent")

            await eng.dispose()

            # 1. Create backup
            meta = create_database_backup(
                source_db_path=source_db,
                backup_dir=backup_dir,
                tag="unit_test",
            )
            self.assertIsNotNone(meta)
            self.assertTrue(meta.backup_path.exists())
            self.assertTrue(meta.checksum_path.exists())

            # 2. Verify backup integrity
            verified_meta = verify_backup_integrity(meta.backup_path)
            self.assertEqual(verified_meta.sha256, meta.sha256)
            self.assertEqual(verified_meta.users_count, 1)
            self.assertEqual(verified_meta.transactions_count, 2)

            # 3. Restore backup into an isolated database file
            restored_meta = restore_database_from_backup(
                backup_path=meta.backup_path,
                target_db_path=restored_db,
                safety_backup_dir=backup_dir,
            )
            self.assertIsNotNone(restored_meta)
            self.assertTrue(restored_db.exists())

            # 4. Verify restored data matches 100%
            eng_restored = _make_sqlite_engine(restored_db)
            sf_restored = async_sessionmaker(eng_restored, expire_on_commit=False)
            async with sf_restored() as session:
                u_restored = await get_user_by_telegram_id(session, 800010)
                self.assertIsNotNone(u_restored)
                self.assertEqual(u_restored.name, "Backup User")
                bal = await get_user_balance(session, u_restored.id)
                self.assertEqual(bal, Decimal("2249.75"))
                _, total = await get_user_transactions(session, u_restored.id, limit=10)
                self.assertEqual(total, 2)

            await eng_restored.dispose()

    async def test_11_secret_redaction_in_logs(self) -> None:
        """
        Дополнительный тест безопасности: проверка фильтрации токенов из логов.
        """
        redactor = SecretRedactingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Calling https://api.telegram.org/bot9295705274:AAE5CdkSuW0xOkINMnopcwJYIqYEQsYyPJA/getMe",
            args=(),
            exc_info=None,
        )
        redactor.filter(record)
        self.assertNotIn("AAE5CdkSuW0xOkINMnopcwJYIqYEQsYyPJA", record.msg)
        self.assertIn("***REDACTED_TOKEN***", record.msg)


if __name__ == "__main__":
    unittest.main()
