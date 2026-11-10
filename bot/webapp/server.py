"""aiohttp server providing the Telegram Mini App (WebApp) UI and REST API."""

import csv
import hashlib
import hmac
import io
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qsl

from aiohttp import web

from bot.config import settings
from bot.database.crud import (
    add_transaction,
    advance_date,
    create_or_update_user,
    create_recurring_transaction,
    delete_recurring_transaction,
    delete_transaction,
    delete_user_account,
    get_all_registered_users,
    get_recurring_by_id,
    get_user_by_telegram_id,
    get_user_recurring_transactions,
    get_user_statistics,
    get_user_transactions,
    process_due_recurring_for_user,
    to_local_datetime,
    toggle_recurring_transaction,
    update_transaction,
    update_user_fields,
)
from bot.database.models import User
from bot.database.session import async_session_factory
from bot.services.currencies import CURRENCIES, FEATURED_CURRENCY_CODES, format_money
from bot.services.geo import COUNTRIES, POPULAR_TIMEZONES, get_country_profile
from bot.services.parser import parse_transaction_message

STATIC_DIR = Path(__file__).resolve().parent / "static"


def verify_telegram_init_data(init_data: str, bot_token: str) -> Optional[int]:
    """Validate Telegram WebApp initData HMAC-SHA256 and return telegram user id."""
    if not init_data or not bot_token:
        return None
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(calculated_hash, received_hash):
            return None
        user_json = parsed.get("user")
        if user_json:
            user_data = json.loads(user_json)
            return int(user_data["id"])
    except Exception:
        return None
    return None


async def _resolve_user(request: web.Request, session) -> User:
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    tg_id = verify_telegram_init_data(init_data, settings.bot_token)

    if not tg_id:
        uid_param = request.query.get("uid") or request.headers.get("X-Telegram-User-Id")
        if uid_param and str(uid_param).isdigit():
            tg_id = int(uid_param)

    if tg_id:
        user = await get_user_by_telegram_id(session, tg_id)
        if user:
            return user

    # If no specific uid passed in browser preview, pick the first registered user
    users = await get_all_registered_users(session)
    if users and not tg_id:
        return users[0]

    demo_id = tg_id or 100001
    existing_demo = await get_user_by_telegram_id(session, demo_id)
    if existing_demo:
        return existing_demo

    user = await create_or_update_user(
        session=session,
        telegram_id=demo_id,
        name="Alex",
        phone="+49 170 1234567",
        country_code="DE",
        country_name="Germany",
        currency="EUR",
        tz_name="Europe/Berlin",
        language="ru",
        is_registered=True,
    )

    # Seed initial demo transactions matching the specification screenshot (€1,245.50 balance)
    if demo_id == 100001:
        await add_transaction(session, user.id, "income", "2000.00", "EUR", "Зарплата")
        await add_transaction(session, user.id, "expense", "724.50", "EUR", "Аренда квартиры и счета")
        await add_transaction(session, user.id, "expense", "25.00", "EUR", "Продукты")
        await add_transaction(session, user.id, "expense", "5.00", "EUR", "Обед в McDonald's")

        next_month = advance_date(date.today().isoformat(), "monthly")
        await create_recurring_transaction(
            session, user.id, "Зарплата", "2000.00", "EUR", "income", "monthly", next_month
        )
        await create_recurring_transaction(
            session, user.id, "Аренда квартиры", "650.00", "EUR", "expense", "monthly", next_month
        )
        await create_recurring_transaction(
            session, user.id, "Интернет и подписки", "45.00", "EUR", "expense", "monthly", next_month
        )

    return user


async def handle_index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_DIR / "index.html")


async def handle_dashboard(request: web.Request) -> web.Response:
    async with async_session_factory() as session:
        user = await _resolve_user(request, session)
        await process_due_recurring_for_user(session, user)
        stats = await get_user_statistics(session, user)
        txs, total_txs = await get_user_transactions(session, user.id, limit=50, offset=0)
        recurring = await get_user_recurring_transactions(session, user.id)

        cur = user.currency
        tx_list = []
        for tx in txs:
            dt_local = to_local_datetime(tx.created_at, user.timezone)
            tx_list.append(
                {
                    "id": tx.id,
                    "tx_type": tx.tx_type,
                    "amount": float(tx.amount),
                    "formatted_amount": format_money(tx.amount, tx.currency, tx_type=tx.tx_type),
                    "currency": tx.currency,
                    "description": tx.description,
                    "date": dt_local.strftime("%d.%m.%Y"),
                    "time": dt_local.strftime("%H:%M"),
                }
            )

        rec_list = []
        for rec in recurring:
            try:
                next_fmt = date.fromisoformat(rec.next_run_date).strftime("%d.%m.%Y")
            except Exception:
                next_fmt = rec.next_run_date
            rec_list.append(
                {
                    "id": rec.id,
                    "title": rec.title,
                    "amount": float(rec.amount),
                    "formatted_amount": format_money(rec.amount, rec.currency, tx_type=rec.tx_type),
                    "currency": rec.currency,
                    "tx_type": rec.tx_type,
                    "period": rec.period,
                    "next_run_date": rec.next_run_date,
                    "next_date_formatted": next_fmt,
                    "is_active": rec.is_active,
                }
            )

        reg_local = to_local_datetime(user.created_at, user.timezone)
        payload = {
            "user": {
                "telegram_id": user.telegram_id,
                "name": user.name,
                "phone": user.phone or "",
                "country_code": user.country_code,
                "currency": user.currency,
                "timezone": user.timezone,
                "language": user.language,
                "notify_recurring": user.notify_recurring,
                "daily_reminder": user.daily_reminder,
                "reminder_hour": user.reminder_hour,
                "registered_date": reg_local.strftime("%d.%m.%Y"),
            },
            "stats": {
                "balance": float(stats.balance),
                "formatted_balance": format_money(stats.balance, cur),
                "month_income": float(stats.month_income),
                "formatted_month_income": format_money(stats.month_income, cur, tx_type="income"),
                "month_expense": float(stats.month_expense),
                "formatted_month_expense": format_money(stats.month_expense, cur, tx_type="expense"),
                "today_expense": float(stats.today_expense),
                "formatted_today_expense": format_money(stats.today_expense, cur, tx_type="expense"),
                "today_income": float(stats.today_income),
                "formatted_today_income": format_money(stats.today_income, cur, tx_type="income"),
                "week_expense": float(stats.week_expense),
                "formatted_week_expense": format_money(stats.week_expense, cur, tx_type="expense"),
                "week_income": float(stats.week_income),
                "formatted_week_income": format_money(stats.week_income, cur, tx_type="income"),
                "total_income": float(stats.total_income),
                "formatted_total_income": format_money(stats.total_income, cur, tx_type="income"),
                "total_expense": float(stats.total_expense),
                "formatted_total_expense": format_money(stats.total_expense, cur, tx_type="expense"),
                "net_diff": float(stats.net_diff),
                "formatted_net_diff": format_money(stats.net_diff, cur, signed=True),
            },
            "transactions": tx_list,
            "total_transactions": total_txs,
            "recurring": rec_list,
            "catalog": {
                "currencies": [
                    {
                        "code": code,
                        "symbol": CURRENCIES[code].symbol,
                        "name_ru": CURRENCIES[code].name_ru,
                        "name_en": CURRENCIES[code].name_en,
                    }
                    for code in FEATURED_CURRENCY_CODES
                ],
                "countries": [
                    {
                        "code": c.code,
                        "flag": c.flag,
                        "name_ru": c.name_ru,
                        "name_en": c.name_en,
                        "currency": c.currency,
                        "timezone": c.default_timezone,
                    }
                    for c in COUNTRIES.values()
                ],
                "timezones": POPULAR_TIMEZONES,
            },
        }
        return web.json_response(payload)


async def handle_add_tx(request: web.Request) -> web.Response:
    data = await request.json()
    async with async_session_factory() as session:
        user = await _resolve_user(request, session)
        quick_text = data.get("quick_text")
        default_type = data.get("tx_type", "expense")

        if quick_text:
            parsed = parse_transaction_message(str(quick_text), default_type=default_type)
            if not parsed:
                return web.json_response({"error": "Invalid amount format"}, status=400)
            tx_type = parsed.tx_type
            amount = parsed.amount
            description = parsed.description
        else:
            raw_amt = str(data.get("amount", "")).replace(",", ".").strip()
            try:
                amount = Decimal(raw_amt).quantize(Decimal("0.01"))
                if amount <= 0:
                    raise ValueError()
            except Exception:
                return web.json_response({"error": "Invalid amount"}, status=400)
            tx_type = default_type if default_type in ("expense", "income") else "expense"
            description = str(data.get("description", "")).strip()

        tx = await add_transaction(
            session=session,
            user_id=user.id,
            tx_type=tx_type,
            amount=amount,
            currency=user.currency,
            description=description,
        )
        stats = await get_user_statistics(session, user)
        dt_local = to_local_datetime(tx.created_at, user.timezone)
        return web.json_response(
            {
                "ok": True,
                "transaction": {
                    "id": tx.id,
                    "tx_type": tx.tx_type,
                    "formatted_amount": format_money(tx.amount, tx.currency, tx_type=tx.tx_type),
                    "description": tx.description,
                    "date": dt_local.strftime("%d.%m.%Y"),
                    "time": dt_local.strftime("%H:%M"),
                    "formatted_balance": format_money(stats.balance, user.currency),
                },
            }
        )


async def handle_update_tx(request: web.Request) -> web.Response:
    tx_id = int(request.match_info["id"])
    data = await request.json()
    async with async_session_factory() as session:
        user = await _resolve_user(request, session)
        tx = await update_transaction(
            session,
            tx_id=tx_id,
            user_id=user.id,
            amount=data.get("amount"),
            description=data.get("description"),
            tx_type=data.get("tx_type"),
        )
        if not tx:
            return web.json_response({"error": "Not found"}, status=404)
        return web.json_response({"ok": True})


async def handle_delete_tx(request: web.Request) -> web.Response:
    tx_id = int(request.match_info["id"])
    async with async_session_factory() as session:
        user = await _resolve_user(request, session)
        deleted = await delete_transaction(session, tx_id=tx_id, user_id=user.id)
        if not deleted:
            return web.json_response({"error": "Not found"}, status=404)
        return web.json_response({"ok": True})


async def handle_add_recurring(request: web.Request) -> web.Response:
    data = await request.json()
    async with async_session_factory() as session:
        user = await _resolve_user(request, session)
        title = str(data.get("title", "")).strip()
        raw_amt = str(data.get("amount", "")).replace(",", ".").strip()
        tx_type = data.get("tx_type", "expense")
        period = data.get("period", "monthly")
        next_date = data.get("next_run_date") or date.today().isoformat()

        if not title:
            return web.json_response({"error": "Title required"}, status=400)
        try:
            amt = Decimal(raw_amt).quantize(Decimal("0.01"))
            if amt <= 0:
                raise ValueError()
        except Exception:
            return web.json_response({"error": "Invalid amount"}, status=400)

        await create_recurring_transaction(
            session=session,
            user_id=user.id,
            title=title,
            amount=amt,
            currency=user.currency,
            tx_type=tx_type,
            period=period,
            next_run_date=next_date,
        )
        await process_due_recurring_for_user(session, user)
        return web.json_response({"ok": True})


async def handle_update_recurring(request: web.Request) -> web.Response:
    rec_id = int(request.match_info["id"])
    data = await request.json()
    async with async_session_factory() as session:
        user = await _resolve_user(request, session)
        rec = await get_recurring_by_id(session, rec_id, user_id=user.id)
        if not rec:
            return web.json_response({"error": "Not found"}, status=404)
        if "title" in data and str(data["title"]).strip():
            rec.title = str(data["title"]).strip()[:120]
        if "amount" in data and data["amount"] is not None:
            try:
                rec.amount = abs(Decimal(str(data["amount"]).replace(",", ".")).quantize(Decimal("0.01")))
            except Exception:
                return web.json_response({"error": "Invalid amount"}, status=400)
        if "period" in data and data["period"] in ("daily", "weekly", "monthly", "yearly"):
            rec.period = data["period"]
        if "next_run_date" in data and data["next_run_date"]:
            rec.next_run_date = str(data["next_run_date"])
        await session.commit()
        return web.json_response({"ok": True})


async def handle_toggle_recurring(request: web.Request) -> web.Response:
    rec_id = int(request.match_info["id"])
    async with async_session_factory() as session:
        user = await _resolve_user(request, session)
        rec = await toggle_recurring_transaction(session, rec_id=rec_id, user_id=user.id)
        if not rec:
            return web.json_response({"error": "Not found"}, status=404)
        return web.json_response({"ok": True, "is_active": rec.is_active})


async def handle_delete_recurring(request: web.Request) -> web.Response:
    rec_id = int(request.match_info["id"])
    async with async_session_factory() as session:
        user = await _resolve_user(request, session)
        deleted = await delete_recurring_transaction(session, rec_id=rec_id, user_id=user.id)
        if not deleted:
            return web.json_response({"error": "Not found"}, status=404)
        return web.json_response({"ok": True})


async def handle_update_profile(request: web.Request) -> web.Response:
    data = await request.json()
    async with async_session_factory() as session:
        user = await _resolve_user(request, session)
        updates = {}
        for field in (
            "name",
            "phone",
            "country_code",
            "currency",
            "timezone",
            "language",
            "notify_recurring",
            "daily_reminder",
            "reminder_hour",
        ):
            if field in data and data[field] is not None:
                updates[field] = data[field]
        if "reminder_hour" in updates:
            updates["reminder_hour"] = max(0, min(23, int(updates["reminder_hour"])))
        if "country_code" in updates:
            prof = get_country_profile(updates["country_code"])
            updates["country_name"] = prof.name_en

        await update_user_fields(session, user.telegram_id, **updates)
        return web.json_response({"ok": True})


async def handle_delete_profile(request: web.Request) -> web.Response:
    async with async_session_factory() as session:
        user = await _resolve_user(request, session)
        await delete_user_account(session, user.telegram_id)
        return web.json_response({"ok": True})


async def handle_export_csv(request: web.Request) -> web.Response:
    async with async_session_factory() as session:
        user = await _resolve_user(request, session)
        txs, _ = await get_user_transactions(session, user.id, limit=5000, offset=0)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Date", "Time", "Type", "Amount", "Currency", "Description"])
        for tx in txs:
            dt_local = to_local_datetime(tx.created_at, user.timezone)
            writer.writerow(
                [
                    tx.id,
                    dt_local.strftime("%Y-%m-%d"),
                    dt_local.strftime("%H:%M:%S"),
                    tx.tx_type,
                    f"{tx.amount:.2f}",
                    tx.currency,
                    tx.description,
                ]
            )
        csv_bytes = output.getvalue().encode("utf-8-sig")
        return web.Response(
            body=csv_bytes,
            content_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="finance_history.csv"'},
        )


def create_webapp() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/dashboard", handle_dashboard)
    app.router.add_post("/api/transactions", handle_add_tx)
    app.router.add_put("/api/transactions/{id}", handle_update_tx)
    app.router.add_delete("/api/transactions/{id}", handle_delete_tx)
    app.router.add_post("/api/recurring", handle_add_recurring)
    app.router.add_put("/api/recurring/{id}", handle_update_recurring)
    app.router.add_post("/api/recurring/{id}/toggle", handle_toggle_recurring)
    app.router.add_delete("/api/recurring/{id}", handle_delete_recurring)
    app.router.add_put("/api/profile", handle_update_profile)
    app.router.add_delete("/api/profile", handle_delete_profile)
    app.router.add_get("/api/export.csv", handle_export_csv)
    app.router.add_static("/static", STATIC_DIR, show_index=False)
    return app
