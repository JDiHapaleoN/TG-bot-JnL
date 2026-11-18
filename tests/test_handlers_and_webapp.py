"""End-to-end tests for aiogram Dispatcher routers, button drill-down workflows, store categories, Cash/Card, German (DE) localization, and Partner Mode."""

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.database.crud import (
    ensure_user_partner_code,
    get_recurring_by_id,
    get_transaction_by_id,
    get_user_by_telegram_id,
    get_user_recurring_transactions,
    get_user_statistics,
)
from bot.database.session import configure_sqlite_engine, init_db
from bot.handlers import menu, partner, profile, recurring, start, stats, transactions
from bot.services.categories import detect_category
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


def _make_message(
    tg_id: int, text: str = "", full_name: str = "Test User", bot_mock=None
):
    msg = SimpleNamespace(
        from_user=SimpleNamespace(
            id=tg_id, full_name=full_name, language_code="ru"
        ),
        chat=SimpleNamespace(id=tg_id),
        message_id=101,
        text=text,
        contact=None,
        location=None,
        bot=bot_mock or SimpleNamespace(send_message=AsyncMock()),
    )
    msg.answer = AsyncMock(return_value=SimpleNamespace(delete=AsyncMock()))
    msg.edit_text = AsyncMock()
    msg.answer_document = AsyncMock()
    return msg


def _make_callback(
    tg_id: int, data: str, full_name: str = "Test User", bot_mock=None
):
    msg = _make_message(tg_id, full_name=full_name, bot_mock=bot_mock)
    cb = SimpleNamespace(
        from_user=SimpleNamespace(
            id=tg_id, full_name=full_name, language_code="ru"
        ),
        data=data,
        message=msg,
        bot=msg.bot,
        answer=AsyncMock(),
    )
    return cb


class TestAppWiringAndWorkflows(unittest.IsolatedAsyncioTestCase):
    def test_build_dispatcher(self):
        dp = build_dispatcher()
        self.assertIsNotNone(dp)
        self.assertEqual(len(dp.sub_routers), 7)

    def test_create_webapp(self):
        app = create_webapp()
        self.assertIsNotNone(app)
        routes = [r.resource.canonical for r in app.router.routes() if r.resource]
        self.assertIn("/", routes)
        self.assertIn("/api/dashboard", routes)
        self.assertIn("/api/transactions", routes)
        self.assertIn("/api/recurring", routes)
        self.assertIn("/api/profile", routes)

    def test_store_and_brand_category_detection(self):
        # Supermarkets -> groceries
        for store in (
            "lidl",
            "rewe",
            "aldi",
            "netto",
            "penny",
            "edeka",
            "kaufland",
            "norma",
            "globus",
            "alnatura",
            "spar",
            "billa",
            "migros",
            "coop",
            "biedronka",
            "korzinka",
            "корзинка",
            "пятерочка",
            "вкусвилл",
        ):
            self.assertEqual(
                detect_category(f"Покупка в {store}", tx_type="expense"),
                "groceries",
                f"Expected groceries for {store}",
            )

        # Retail, home, electronics, drugstores -> shopping
        for store in (
            "ikea",
            "mediamarkt",
            "mediamrkt",
            "media markt",
            "saturn",
            "obi",
            "bauhaus",
            "hornbach",
            "tedi",
            "action",
            "dm",
            "rossmann",
            "müller",
            "zara",
            "h&m",
            "deichmann",
            "decathlon",
            "zalando",
            "amazon",
            "ozon",
            "wildberries",
        ):
            self.assertEqual(
                detect_category(store, tx_type="expense"),
                "shopping",
                f"Expected shopping for {store}",
            )

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
                patch("bot.handlers.partner.async_session_factory", sf),
                patch("bot.handlers.stats.async_session_factory", sf),
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
                    self.assertIsNotNone(u.partner_code)

                # 1b. Clicking reg:edit_country -> reg:country:US -> reg:confirm on an existing user
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

                # 2. Instant entry '6.1 lidl' + Cash/Card toggle on confirmation card and in Edit view
                msg_lidl = _make_message(tg_id, "6.1 lidl")
                msg_lidl.message_id = 201
                await transactions.msg_instant_transaction_entry(msg_lidl, state)

                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    tx = await get_transaction_by_id(s, 1, user_id=u.id)
                    self.assertIsNotNone(tx)
                    self.assertEqual(tx.amount, Decimal("6.10"))
                    self.assertEqual(tx.category, "groceries")
                    self.assertEqual(tx.payment_method, "card")

                # Switch payment method to Cash right from the confirmation menu (tx:pay:1:cash)
                await transactions.cb_tx_set_payment_method(
                    _make_callback(tg_id, "tx:pay:1:cash"), state
                )
                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    tx = await get_transaction_by_id(s, 1, user_id=u.id)
                    self.assertEqual(tx.payment_method, "cash")

                # Switch payment method back to Card from the Edit screen (tx:pay:1:card:0:edit)
                await transactions.cb_tx_edit_start(
                    _make_callback(tg_id, "tx:edit:1:0"), state
                )
                await transactions.cb_tx_set_payment_method(
                    _make_callback(tg_id, "tx:pay:1:card:0:edit"), state
                )
                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    tx = await get_transaction_by_id(s, 1, user_id=u.id)
                    self.assertEqual(tx.payment_method, "card")

                # 3. History -> View Transaction -> Change Category -> Edit Amount Only -> Edit Desc Only
                await transactions.cb_tx_view(
                    _make_callback(tg_id, "tx:view:1:0"), state
                )
                await transactions.cb_tx_pick_category(
                    _make_callback(tg_id, "tx:cat:1:0"), state
                )
                await transactions.cb_tx_set_category(
                    _make_callback(tg_id, "tx:setcat:1:shopping:0"), state
                )
                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    tx = await get_transaction_by_id(s, 1, user_id=u.id)
                    self.assertEqual(tx.category, "shopping")

                # Edit description only ("mediamrkt кабель") -> auto-updates description and keeps amount
                await transactions.cb_tx_edit_start(
                    _make_callback(tg_id, "tx:edit:1:0"), state
                )
                await transactions.msg_tx_edit_save(
                    _make_message(tg_id, "mediamrkt кабель"), state
                )
                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    tx = await get_transaction_by_id(s, 1, user_id=u.id)
                    self.assertEqual(tx.amount, Decimal("6.10"))
                    self.assertEqual(tx.description, "mediamrkt кабель")
                    self.assertEqual(tx.category, "shopping")

                # Edit amount only (without wiping out description!)
                await transactions.cb_tx_edit_start(
                    _make_callback(tg_id, "tx:edit:1:0"), state
                )
                await transactions.msg_tx_edit_save(
                    _make_message(tg_id, "19.99"), state
                )
                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    tx = await get_transaction_by_id(s, 1, user_id=u.id)
                    self.assertEqual(tx.amount, Decimal("19.99"))
                    self.assertEqual(tx.description, "mediamrkt кабель")

                # 4. German ('de') language selection in Profile and localized rendering
                await profile.cb_prof_toggle_setting(
                    _make_callback(tg_id, "prof:toggle:lang"), state
                )
                cb_de = _make_callback(tg_id, "prof:lang:de")
                await profile.cb_prof_set_language(cb_de, state)

                async with sf() as s:
                    u = await get_user_by_telegram_id(s, tg_id)
                    self.assertEqual(u.language, "de")
                    stats_text_de = await stats._build_stats_text(s, u)
                    self.assertIn("Finanzstatistik", stats_text_de)
                    self.assertIn("Karte:", stats_text_de)
                    self.assertIn("Bargeld:", stats_text_de)
                    self.assertIn("Einkaufen", stats_text_de)

                # 5. Partner Mode: register Partner 2, link permanently, verify expense alerts & partner tabs
                partner_tg_id = 910002
                partner_state = FakeFSMContext()
                await start.cb_reg_language(
                    _make_callback(partner_tg_id, "reg:lang:de"), partner_state
                )
                await start.msg_reg_name(
                    _make_message(partner_tg_id, "Мария"), partner_state
                )
                await start.msg_reg_phone_text(
                    _make_message(partner_tg_id, "Überspringen"), partner_state
                )
                await start.cb_reg_country_selected(
                    _make_callback(partner_tg_id, "reg:country:DE"), partner_state
                )
                await start.cb_reg_confirm(
                    _make_callback(partner_tg_id, "reg:confirm"), partner_state
                )

                async with sf() as s:
                    u2 = await get_user_by_telegram_id(s, partner_tg_id)
                    p2_code = await ensure_user_partner_code(s, u2)
                    self.assertTrue(p2_code.startswith("JNL-"))

                # User 1 opens Partner menu -> clicks Link -> enters User 2's partner_code
                await partner.cb_menu_partner(
                    _make_callback(tg_id, "menu:partner"), state
                )
                await partner.cb_partner_link_start(
                    _make_callback(tg_id, "partner:link_start"), state
                )
                bot_mock = SimpleNamespace(send_message=AsyncMock())
                await partner.msg_partner_code_entered(
                    _make_message(tg_id, p2_code, bot_mock=bot_mock), state
                )

                # Verify both accounts are permanently linked and Partner 2 received link notification
                self.assertEqual(bot_mock.send_message.await_count, 1)
                async with sf() as s:
                    u1 = await get_user_by_telegram_id(s, tg_id)
                    u2 = await get_user_by_telegram_id(s, partner_tg_id)
                    self.assertEqual(u1.partner_id, u2.id)
                    self.assertEqual(u2.partner_id, u1.id)

                # Partner 2 logs an income (+2500 Gehalt) and an expense (14.50 rewe)
                inc_msg = _make_message(partner_tg_id, "+2500 Gehalt", bot_mock=bot_mock)
                inc_msg.message_id = 301
                await transactions.msg_instant_transaction_entry(
                    inc_msg, partner_state
                )

                bot_mock.send_message.reset_mock()
                exp_msg = _make_message(partner_tg_id, "14.50 rewe", bot_mock=bot_mock)
                exp_msg.message_id = 302
                await transactions.msg_instant_transaction_entry(
                    exp_msg, partner_state
                )

                # User 1 receives real-time notification about Partner 2's expense in German ('de')!
                self.assertEqual(bot_mock.send_message.await_count, 1)
                notified_tg_id = bot_mock.send_message.call_args.args[0]
                notified_text = bot_mock.send_message.call_args.args[1]
                self.assertEqual(notified_tg_id, tg_id)
                self.assertIn("Мария", notified_text)
                self.assertIn("14.50", notified_text)
                self.assertIn("Lebensmittel", notified_text)
                self.assertIn("2,500.00", notified_text)

                # User 1 drills down into Partner Dashboard -> Partner Stats -> Partner History -> Partner Tx Detail
                cb_p_dash = _make_callback(tg_id, "menu:partner")
                await partner.cb_menu_partner(cb_p_dash, state)
                dash_rendered = cb_p_dash.message.edit_text.call_args.args[0]
                self.assertIn("Мария", dash_rendered)
                self.assertIn("2,500.00", dash_rendered)

                cb_p_stats = _make_callback(tg_id, "partner:stats")
                await partner.cb_partner_stats(cb_p_stats, state)
                p_stats_rendered = cb_p_stats.message.edit_text.call_args.args[0]
                self.assertIn("Мария", p_stats_rendered)
                self.assertIn("Lebensmittel", p_stats_rendered)

                cb_p_hist = _make_callback(tg_id, "partner:history:0")
                await partner.cb_partner_history(cb_p_hist, state)
                p_hist_rendered = cb_p_hist.message.edit_text.call_args.args[0]
                self.assertIn("rewe", p_hist_rendered)

                # Find Partner 2's transaction ID and open detail view
                async with sf() as s:
                    u2 = await get_user_by_telegram_id(s, partner_tg_id)
                    p2_stats = await get_user_statistics(s, u2)
                    self.assertEqual(p2_stats.month_income, Decimal("2500.00"))
                    self.assertEqual(p2_stats.month_expense, Decimal("14.50"))

                cb_p_tx = _make_callback(tg_id, "partner:tx:3:0")
                await partner.cb_partner_tx_detail(cb_p_tx, state)
                p_tx_rendered = cb_p_tx.message.edit_text.call_args.args[0]
                self.assertIn("rewe", p_tx_rendered)

                # 6. Recurring operation creation and full editing
                await recurring.cb_rec_add_start(
                    _make_callback(tg_id, "rec:add:expense"), state
                )
                await state.clear()
                await recurring.cb_rec_preset_title(
                    _make_callback(tg_id, "rec:preset:Miete"), state
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
                    self.assertEqual(recs[0].title, "Miete")
                    self.assertEqual(recs[0].amount, Decimal("500.00"))

                await recurring.cb_rec_edit_amount(
                    _make_callback(tg_id, f"rec:edit:amount:{rec_id}"), state
                )
                await recurring.msg_rec_edit_amount(
                    _make_message(tg_id, "650.00 USD"), state
                )
                await recurring.cb_rec_set_title(
                    _make_callback(tg_id, f"rec:settitle:{rec_id}:Internet"), state
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
                    self.assertEqual(rec.title, "Internet")
                    self.assertEqual(rec.period, "weekly")
                    self.assertEqual(rec.next_run_date, "2026-12-15")

            await eng.dispose()


if __name__ == "__main__":
    unittest.main()
