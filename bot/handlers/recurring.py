"""Recurring incomes and expenses handlers."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Tuple

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.crud import (
    create_recurring_transaction,
    delete_recurring_transaction,
    get_recurring_by_id,
    get_user_by_telegram_id,
    get_user_recurring_transactions,
    local_now,
    process_due_recurring_for_user,
    toggle_recurring_transaction,
)
from bot.database.models import User
from bot.database.session import async_session_factory
from bot.i18n.translations import period_label, t
from bot.keyboards.inline import (
    recurring_date_kb,
    recurring_detail_kb,
    recurring_menu_kb,
    recurring_period_kb,
    recurring_presets_kb,
)
from bot.services.currencies import format_money
from bot.states.forms import RecurringStates

router = Router(name="recurring")


def _format_iso_date(iso_str: str) -> str:
    try:
        return date.fromisoformat(iso_str).strftime("%d.%m.%Y")
    except Exception:
        return iso_str


async def _render_recurring_menu(session, user: User):
    await process_due_recurring_for_user(session, user)
    items = await get_user_recurring_transactions(session, user.id)
    lang = user.language
    if not items:
        list_text = t("recurring_empty", lang)
    else:
        lines = []
        for idx, rec in enumerate(items, start=1):
            st = "✅" if rec.is_active else "⏸"
            amt = format_money(rec.amount, rec.currency, tx_type=rec.tx_type)
            p_lbl = period_label(rec.period, lang)
            d_lbl = _format_iso_date(rec.next_run_date)
            lines.append(f"{idx}. {st} <b>{rec.title}</b> — <code>{amt}</code> ({p_lbl}, след: {d_lbl})")
        list_text = "\n".join(lines)

    text = t("recurring_menu_title", lang, list_text=list_text)
    kb = recurring_menu_kb(items, lang=lang)
    return text, kb


@router.message(Command("recurring"))
async def cmd_recurring(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_registered:
            return
        text, kb = await _render_recurring_menu(session, user)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "menu:recurring")
async def cb_menu_recurring(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return
        text, kb = await _render_recurring_menu(session, user)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data.startswith("rec:add:"))
async def cb_rec_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    tx_type = callback.data.split(":")[-1]
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        lang = user.language
        await state.set_state(RecurringStates.waiting_title)
        await state.update_data(rec_tx_type=tx_type, rec_currency=user.currency, lang=lang)
        prompt_key = "rec_ask_title_income" if tx_type == "income" else "rec_ask_title_expense"
        await callback.message.edit_text(
            t(prompt_key, lang),
            reply_markup=recurring_presets_kb(tx_type, lang=lang),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(RecurringStates.waiting_title, F.data.startswith("rec:preset:"))
async def cb_rec_preset_title(callback: CallbackQuery, state: FSMContext) -> None:
    title = callback.data.split("rec:preset:")[-1]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    currency = data.get("rec_currency", "EUR")
    await state.update_data(rec_title=title)
    await state.set_state(RecurringStates.waiting_amount)
    await callback.message.edit_text(
        t("rec_ask_amount", lang, title=title, currency=currency),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(RecurringStates.waiting_title, F.text)
async def msg_rec_custom_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()[:100]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    currency = data.get("rec_currency", "EUR")
    await state.update_data(rec_title=title)
    await state.set_state(RecurringStates.waiting_amount)
    await message.answer(
        t("rec_ask_amount", lang, title=title, currency=currency),
        parse_mode="HTML",
    )


@router.message(RecurringStates.waiting_amount, F.text)
async def msg_rec_amount(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    title = data.get("rec_title", "")
    raw = message.text.strip().replace(",", ".").lstrip("+-−–€$£₽₺¥ ")
    try:
        amt = Decimal(raw).quantize(Decimal("0.01"))
        if amt <= 0:
            raise ValueError()
    except (InvalidOperation, ValueError):
        await message.answer(t("invalid_tx_input", lang), parse_mode="HTML")
        return

    await state.update_data(rec_amount=str(amt))
    await state.set_state(RecurringStates.waiting_period)
    await message.answer(
        t("rec_ask_period", lang, title=title),
        reply_markup=recurring_period_kb(lang),
        parse_mode="HTML",
    )


@router.callback_query(RecurringStates.waiting_period, F.data.startswith("rec:period:"))
async def cb_rec_period(callback: CallbackQuery, state: FSMContext) -> None:
    period = callback.data.split(":")[-1]
    await state.update_data(rec_period=period)
    await state.set_state(RecurringStates.waiting_date)

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        lang = user.language if user else "ru"
        today_local = local_now(user.timezone if user else "UTC").date()

    await callback.message.edit_text(
        t("rec_ask_date", lang),
        reply_markup=recurring_date_kb(today_local, lang=lang),
        parse_mode="HTML",
    )
    await callback.answer()


async def _finalize_recurring_creation(
    telegram_id: int, next_iso_date: str, state: FSMContext
) -> Tuple[str, object]:
    data = await state.get_data()
    title = data.get("rec_title", "Операция")
    amount = Decimal(data.get("rec_amount", "0.00"))
    tx_type = data.get("rec_tx_type", "expense")
    period = data.get("rec_period", "monthly")

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        lang = user.language
        rec = await create_recurring_transaction(
            session=session,
            user_id=user.id,
            title=title,
            amount=amount,
            currency=user.currency,
            tx_type=tx_type,
            period=period,
            next_run_date=next_iso_date,
        )
        # If the user scheduled it for today or earlier, process immediately
        await process_due_recurring_for_user(session, user)
        await state.clear()
        confirm_text = t(
            "rec_created",
            lang,
            title=rec.title,
            amount=format_money(rec.amount, rec.currency, tx_type=rec.tx_type),
            period=period_label(rec.period, lang),
            next_date=_format_iso_date(rec.next_run_date),
        )
        menu_text, kb = await _render_recurring_menu(session, user)
        return f"{confirm_text}\n\n{menu_text}", kb


@router.callback_query(RecurringStates.waiting_date, F.data.startswith("rec:date:"))
async def cb_rec_date_quick(callback: CallbackQuery, state: FSMContext) -> None:
    iso_date = callback.data.split("rec:date:")[-1]
    full_text, kb = await _finalize_recurring_creation(callback.from_user.id, iso_date, state)
    await callback.message.edit_text(full_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.message(RecurringStates.waiting_date, F.text)
async def msg_rec_date_manual(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    parsed_date = None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            parsed_date = datetime.strptime(raw, fmt).date()
            break
        except ValueError:
            continue

    if not parsed_date:
        data = await state.get_data()
        lang = data.get("lang", "ru")
        await message.answer(t("rec_ask_date", lang), parse_mode="HTML")
        return

    full_text, kb = await _finalize_recurring_creation(
        message.from_user.id, parsed_date.isoformat(), state
    )
    await message.answer(full_text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("rec:view:"))
async def cb_rec_view(callback: CallbackQuery) -> None:
    rec_id = int(callback.data.split(":")[-1])
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        rec = await get_recurring_by_id(session, rec_id, user_id=user.id)
        if not rec:
            await callback.answer()
            return
        lang = user.language
        text = t(
            "rec_detail",
            lang,
            rec_id=rec.id,
            title=rec.title,
            type_label=t("type_income" if rec.tx_type == "income" else "type_expense", lang),
            amount=format_money(rec.amount, rec.currency, tx_type=rec.tx_type),
            period=period_label(rec.period, lang),
            next_date=_format_iso_date(rec.next_run_date),
            status=t("status_active" if rec.is_active else "status_paused", lang),
        )
        await callback.message.edit_text(
            text,
            reply_markup=recurring_detail_kb(rec.id, lang),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data.startswith("rec:toggle:"))
async def cb_rec_toggle(callback: CallbackQuery) -> None:
    rec_id = int(callback.data.split(":")[-1])
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        rec = await toggle_recurring_transaction(session, rec_id, user_id=user.id)
        if not rec:
            await callback.answer()
            return
        lang = user.language
        text = t(
            "rec_detail",
            lang,
            rec_id=rec.id,
            title=rec.title,
            type_label=t("type_income" if rec.tx_type == "income" else "type_expense", lang),
            amount=format_money(rec.amount, rec.currency, tx_type=rec.tx_type),
            period=period_label(rec.period, lang),
            next_date=_format_iso_date(rec.next_run_date),
            status=t("status_active" if rec.is_active else "status_paused", lang),
        )
        await callback.message.edit_text(
            text,
            reply_markup=recurring_detail_kb(rec.id, lang),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data.startswith("rec:del:"))
async def cb_rec_delete(callback: CallbackQuery) -> None:
    rec_id = int(callback.data.split(":")[-1])
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        await delete_recurring_transaction(session, rec_id, user_id=user.id)
        await callback.answer(t("rec_deleted", user.language))
        text, kb = await _render_recurring_menu(session, user)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
