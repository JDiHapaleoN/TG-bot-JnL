"""End-to-end tests for aiogram Dispatcher routers, button drill-down workflows, and WebApp server."""

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.database.crud import (
    add_transaction,
    create_or_update_user,
    get_recurring_by_id,
    get_transaction_by_id,
    get_user_by_telegram_id,
    get_user_recurring_transactions,
)
from bot.database.session import configure_sqlite_engine, init_db
from bot.handlers import profile, recurring, start, transactions
from bot.webapp.server import create_webapp
from main import build_dispatcher


class FakeFSMContext:
    """In-memory FSMContext replacement for testing multi-step button and message flows."""

    def __init__(self):
        self._state = None
        self._data = {}

    async def get_state(self):
        return self._state

    async def set_state(self, state):
        if state is None:
            self._state = None
        elif hasattr(state, "state"):
            self._state = state.state
        else:
            self._state = str(state)

    async def get_data(self):
        return dict(self._data)

    async def update_data(self, **kwargs):
        self._data.update(kwargs)
        return dict(self._data)

    async def clear(self):
        self._state = None
        self._data.clear()


def _make_message(tg_id: int, text: str = "", full_name: str = "Test User"):
    msg = SimpleNamespace(
        from_user=SimpleNamespace(
            id=tg_id, full_name=full_name, language_code="ru"
        ),
        chat=SimpleNamespace(id=tg_id),
        message_id=101,
        text=text,
        contact=None,
        location=None,
    )
    msg.answer = AsyncMock(return_value=SimpleNamespace(delete=AsyncMock()))
    msg.edit_text = AsyncMock()
    msg.answer_document = AsyncMock()
    return msg


def _make_callback(tg_id: int, data: str, full_name: str = "Test User"):
    msg = _make_message(tg_id, full_name=full_name)
    cb = SimpleNamespace(
        from_user=SimpleNamespace(
            id=tg_id, full_name=full_name, language_code="ru"
        ),
        data=data,
        message=msg,
        answer=AsyncMock(),
    )
    return cb


class TestAppWiringAndWorkflows(unittest.IsolatedAsyncioTestCase):
    def test_build_dispatcher(self):
        dp = build_dispatcher()
        self.assertIsNotNone(dp)
        self.assertEqual(len(dp.sub_routers), 6)

    def test_create_webapp(self):
        app = create_webapp()
        self.assertIsNotNone(app)
        routes = [r.resource.canonical for r in app.router.routes() if r.resource]
        self.assertIn("/", routes)
        self.assertIn("/api/dashboard", routes)
        self.assertIn("/api/transactions", routes)
        self.assertIn("/api/recurring", routes)
        self.assertIn("/api/profile", routes)

    async def test_all_button_drilldown_workflows_persist_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "workflows.db"
            eng = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
            configure_sqlite_engine(eng)
            await init_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)

            with (
                patch("bot.handlers.start.async_session_factory", sf),
                patch("bot.handlers.menu.async_session_factory", sf),
                patch("bot.handlers.profile.async_session_factory", sf),
                patch("bot.handlers.recurring.async_session_factory", sf),
                patch("bot.handlers.transactions.async_session_factory", sf),
            ):
                tg_id = 910001
                state = FakeFSMContext()

                # 1. Registration drill-down: edit country -> edit currency -> edit tz -> confirm
                await start.cb_reg_language(_make_callback(tg_id, "reg:lang:ru"), state)
                await start.msg_reg_name(_make_message(tg_id, "Алексей"), state)
                await start.msg_reg_phone_text(_make_message(tg_id, "Пропустить"), state)
                await start.msg_reg_location_manual(
                    _make_message(tg_id, "🌍 Выбрать страну вручную"), state
                )
                await start.cb_reg_country_selected(
                    _make_callback(tg_id, "reg:country:DE"), state
                )
                await start.cb_reg_confirm(_make_callback(tg_id, "reg:confirm"), state)

                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    self.assertEqual(u.name, "Алексей")
                    self.assertEqual(u.country_code, "DE")
                    self.assertEqual(u.currency, "EUR")

                # 1b. Clicking reg:edit_country -> reg:country:US -> reg:confirm on an existing user
                # MUST apply the user's selected country/currency changes!
                await start.cb_reg_edit_country(
                    _make_callback(tg_id, "reg:edit_country"), state
                )
                await start.cb_reg_country_selected(
                    _make_callback(tg_id, "reg:country:US"), state
                )
                await start.cb_reg_confirm(_make_callback(tg_id, "reg:confirm"), state)

                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    self.assertEqual(u.country_code, "US")
                    self.assertEqual(u.currency, "USD")

                # 1c. Clicking old reg:confirm with empty state does NOT overwrite user profile
                await state.clear()
                await start.cb_reg_confirm(_make_callback(tg_id, "reg:confirm"), state)
                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    self.assertEqual(u.name, "Алексей")
                    self.assertEqual(u.currency, "USD")

                # 2. Add expense via quick category drill-down:
                # menu:add_expense -> tx:newcat:expense:food -> send "18.50"
                await transactions.cb_add_expense_prompt(
                    _make_callback(tg_id, "menu:add_expense"), state
                )
                await transactions.cb_new_tx_category_selected(
                    _make_callback(tg_id, "tx:newcat:expense:food"), state
                )
                await transactions.msg_guided_expense(
                    _make_message(tg_id, "18.50"), state
                )

                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    tx = await get_transaction_by_id(s, 1, user_id=u.id)
                    self.assertIsNotNone(tx)
                    self.assertEqual(tx.amount, Decimal("18.50"))
                    self.assertEqual(tx.category, "food")
                    self.assertEqual(tx.currency, "USD")

                # 3. History -> View Transaction -> Change Category -> Edit Amount Only -> Edit Desc Only -> Flip Type
                await transactions.cb_tx_view(
                    _make_callback(tg_id, "tx:view:1:0"), state
                )
                await transactions.cb_tx_pick_category(
                    _make_callback(tg_id, "tx:cat:1:0"), state
                )
                await transactions.cb_tx_set_category(
                    _make_callback(tg_id, "tx:setcat:1:transport:0"), state
                )
                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    tx = await get_transaction_by_id(s, 1, user_id=u.id)
                    self.assertEqual(tx.category, "transport")

                # Edit description only (without changing amount)
                await transactions.cb_tx_edit_start(
                    _make_callback(tg_id, "tx:edit:1:0"), state
                )
                await transactions.msg_tx_edit_save(
                    _make_message(tg_id, "Такси в центр"), state
                )
                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    tx = await get_transaction_by_id(s, 1, user_id=u.id)
                    self.assertEqual(tx.amount, Decimal("18.50"))
                    self.assertEqual(tx.description, "Такси в центр")

                # Edit amount only (without wiping out description!)
                await transactions.cb_tx_edit_start(
                    _make_callback(tg_id, "tx:edit:1:0"), state
                )
                await transactions.msg_tx_edit_save(
                    _make_message(tg_id, "24.00"), state
                )
                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    tx = await get_transaction_by_id(s, 1, user_id=u.id)
                    self.assertEqual(tx.amount, Decimal("24.00"))
                    self.assertEqual(tx.description, "Такси в центр")
                    self.assertEqual(tx.category, "transport")

                # Flip type (expense -> income)
                await transactions.cb_tx_flip_type(
                    _make_callback(tg_id, "tx:flip:1:0"), state
                )
                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    tx = await get_transaction_by_id(s, 1, user_id=u.id)
                    self.assertEqual(tx.tx_type, "income")

                # 4. Recurring operation creation (including trailing currency symbol in amount) + full editing
                await recurring.cb_rec_add_start(
                    _make_callback(tg_id, "rec:add:expense"), state
                )
                # Simulate state reset before clicking preset button
                await state.clear()
                await recurring.cb_rec_preset_title(
                    _make_callback(tg_id, "rec:preset:Аренда квартиры"), state
                )
                await recurring.msg_rec_amount(
                    _make_message(tg_id, "500 $"), state
                )
                await recurring.cb_rec_period(
                    _make_callback(tg_id, "rec:period:monthly"), state
                )
                await recurring.cb_rec_date_quick(
                    _make_callback(tg_id, "rec:date:2026-12-01"), state
                )

                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    recs = await get_user_recurring_transactions(s, u.id)
                    self.assertEqual(len(recs), 1)
                    rec_id = recs[0].id
                    self.assertEqual(recs[0].title, "Аренда квартиры")
                    self.assertEqual(recs[0].amount, Decimal("500.00"))
                    self.assertEqual(recs[0].period, "monthly")
                    self.assertEqual(recs[0].next_run_date, "2026-12-01")

                # Edit recurring amount, title, period, and date via drill-down buttons
                await recurring.cb_rec_edit_amount(
                    _make_callback(tg_id, f"rec:edit:amount:{rec_id}"), state
                )
                await recurring.msg_rec_edit_amount(
                    _make_message(tg_id, "650.00 USD"), state
                )
                await recurring.cb_rec_set_title(
                    _make_callback(tg_id, f"rec:settitle:{rec_id}:Интернет и ТВ"), state
                )
                await recurring.cb_rec_set_period(
                    _make_callback(tg_id, f"rec:setperiod:{rec_id}:weekly"), state
                )
                await recurring.cb_rec_set_date(
                    _make_callback(tg_id, f"rec:setdate:{rec_id}:2026-12-15"), state
                )

                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    rec = await get_recurring_by_id(s, rec_id, user_id=u.id)
                    self.assertEqual(rec.amount, Decimal("650.00"))
                    self.assertEqual(rec.title, "Интернет и ТВ")
                    self.assertEqual(rec.period, "weekly")
                    self.assertEqual(rec.next_run_date, "2026-12-15")

                # 5. Profile drill-downs: country change syncs currency & timezone across transactions/recurring,
                # phone skip does not save "Пропустить", reminder hour updates
                await profile.cb_prof_edit_phone(
                    _make_callback(tg_id, "prof:edit:phone"), state
                )
                await profile.msg_prof_new_phone_text(
                    _make_message(tg_id, "Пропустить"), state
                )
                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    self.assertIsNone(u.phone)

                await profile.cb_prof_country_selected(
                    _make_callback(tg_id, "prof:country:UZ"), state
                )
                await profile.cb_prof_rem_hour_selected(
                    _make_callback(tg_id, "prof:rem_hour:21"), state
                )

                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    self.assertEqual(u.country_code, "UZ")
                    self.assertEqual(u.currency, "UZS")
                    self.assertEqual(u.timezone, "Asia/Tashkent")
                    self.assertEqual(u.reminder_hour, 21)
                    tx = await get_transaction_by_id(s, 1, user_id=u.id)
                    rec = await get_recurring_by_id(s, rec_id, user_id=u.id)
                    self.assertEqual(tx.currency, "UZS")
                    self.assertEqual(rec.currency, "UZS")

            await eng.dispose()


if __name__ == "__main__":
    unittest.main()
