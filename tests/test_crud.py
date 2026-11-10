"""Async database CRUD, balance, statistics, and recurring transaction tests."""

from decimal import Decimal
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.database.crud import (
    add_transaction,
    create_or_update_user,
    create_recurring_transaction,
    delete_transaction,
    delete_user_account,
    get_user_balance,
    get_user_statistics,
    get_user_transactions,
    process_due_recurring_for_user,
    update_transaction,
)
from bot.database.models import Base


class TestDatabaseCRUD(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_user_transactions_balance_and_stats(self):
        async with self.session_factory() as session:
            user = await create_or_update_user(
                session,
                telegram_id=999001,
                name="Test User",
                phone="+491234567",
                country_code="DE",
                country_name="Germany",
                currency="EUR",
                tz_name="Europe/Berlin",
                language="ru",
            )

            # Add +2000 income and -754.50 expense (matching spec screenshot: balance 1245.50)
            await add_transaction(session, user.id, "income", "2000.00", "EUR", "Зарплата")
            tx_exp = await add_transaction(session, user.id, "expense", "754.50", "EUR", "Аренда и продукты")

            balance = await get_user_balance(session, user.id)
            self.assertEqual(balance, Decimal("1245.50"))

            stats = await get_user_statistics(session, user)
            self.assertEqual(stats.balance, Decimal("1245.50"))
            self.assertEqual(stats.month_income, Decimal("2000.00"))
            self.assertEqual(stats.month_expense, Decimal("754.50"))
            self.assertEqual(stats.net_diff, Decimal("1245.50"))

            # Edit transaction
            await update_transaction(
                session, tx_exp.id, user.id, amount="500.00", description="Аренда"
            )
            self.assertEqual(await get_user_balance(session, user.id), Decimal("1500.00"))

            # Delete transaction
            await delete_transaction(session, tx_exp.id, user.id)
            self.assertEqual(await get_user_balance(session, user.id), Decimal("2000.00"))

    async def test_recurring_transactions_execution(self):
        async with self.session_factory() as session:
            user = await create_or_update_user(
                session,
                telegram_id=999002,
                name="Recurring User",
                currency="EUR",
                tz_name="Europe/Berlin",
            )

            rec = await create_recurring_transaction(
                session=session,
                user_id=user.id,
                title="Интернет",
                amount="30.00",
                currency="EUR",
                tx_type="expense",
                period="monthly",
                next_run_date="2026-11-09",
            )

            executed = await process_due_recurring_for_user(
                session, user, current_local_date="2026-11-09"
            )
            self.assertEqual(len(executed), 1)
            self.assertEqual(rec.next_run_date, "2026-12-09")

            txs, total = await get_user_transactions(session, user.id)
            self.assertEqual(total, 1)
            self.assertEqual(txs[0].amount, Decimal("30.00"))

            # Account deletion cascade
            deleted = await delete_user_account(session, user.telegram_id)
            self.assertTrue(deleted)


if __name__ == "__main__":
    unittest.main()

