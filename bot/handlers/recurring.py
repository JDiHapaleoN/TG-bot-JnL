"""Recurring incomes and expenses handlers with full creation and editing workflows."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple

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
    update_recurring_transaction,
)
from bot.database.models import RecurringTransaction, User
from bot.database.session import async_session_factory
from bot.handlers.menu import (
    EXPENSE_BTN_TEXTS,
    HISTORY_BTN_TEXTS,
    INCOME_BTN_TEXTS,
    MENU_BTN_TEXTS,
    PROFILE_BTN_TEXTS,
    STATS_BTN_TEXTS,
)
from bot.i18n.translations import period_label, t
from bot.keyboards.inline import (
    recurring_cancel_kb,
    recurring_date_kb,
    recurring_detail_kb,
    recurring_menu_kb,
    recurring_period_kb,
    recurring_presets_kb,
    safe_edit_text,
)
from bot.services.currencies import format_money
from bot.services.parser import parse_transaction_message
from bot.states.forms import RecurringStates

router = Router(name="recurring")

ALL_NAV_TEXTS = (
    MENU_BTN_TEXTS
    | EXPENSE_BTN_TEXTS
    | INCOME_BTN_TEXTS
    | STATS_BTN_TEXTS
    | HISTORY_BTN_TEXTS
    | PROFILE_BTN_TEXTS
)

_NUMBER_EXTRACT_RE = re.compile(r"(\d+(?:[.,]\d{1,2})?)")


def _format_iso_date(iso_str: str) -> str:
    try:
        return date.fromisoformat(iso_str).strftime("%d.%m.%Y")
    except Exception:
        return iso_str


def _parse_recurring_amount(text: str) -> Optional[Decimal]:
    """Parse monetary amount from user input, allowing currency symbols or trailing notes."""
    parsed = parse_transaction_message(text)
    if parsed is not None:
        return parsed.amount
    cleaned = (text or "").strip()
    if cleaned.startswith("-") or cleaned.startswith("−"):
        return None
    m = _NUMBER_EXTRACT_RE.search(cleaned)
    if not m:
        return None
    try:
        amt = Decimal(m.group(1).replace(",", ".")).quantize(Decimal("0.01"))
        if Decimal("0.01") <= amt <= Decimal("999999999.99"):
            return amt
    except (InvalidOperation, ValueError):
        pass
    return None


def _parse_input_date(raw: str) -> Optional[date]:
    cleaned = (raw or "").strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _build_rec_detail_text(rec: RecurringTransaction, lang: str) -> str:
    return t(
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
            lines.append(
                f"{idx}. {st} <b>{rec.title}</b> — <code>{amt}</code> ({p_lbl}, след: {d_lbl})"
            )
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
        await safe_edit_text(callback.message, text, reply_markup=kb)
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
        await state.update_data(
            rec_tx_type=tx_type, rec_currency=user.currency, lang=lang
        )
        prompt_key = (
            "rec_ask_title_income" if tx_type == "income" else "rec_ask_title_expense"
        )
        await safe_edit_text(
            callback.message,
            t(prompt_key, lang),
            reply_markup=recurring_presets_kb(tx_type, lang=lang),
        )
        await callback.answer()


@router.callback_query(F.data.startswith("rec:preset:"))
async def cb_rec_preset_title(callback: CallbackQuery, state: FSMContext) -> None:
    title = callback.data.split("rec:preset:")[-1]
    data = await state.get_data()
    lang = data.get("lang")
    currency = data.get("rec_currency")
    tx_type = data.get("rec_tx_type")

    if not lang or not currency:
        async with async_session_factory() as session:
            user = await get_user_by_telegram_id(session, callback.from_user.id)
            lang = user.language if user else "ru"
            currency = user.currency if user else "EUR"

    if not tx_type:
        income_presets = {"Зарплата", "Стипендия", "Арендный доход", "Salary", "Stipend", "Rental Income"}
        tx_type = "income" if title in income_presets else "expense"

    await state.update_data(
        rec_title=title, rec_tx_type=tx_type, rec_currency=currency, lang=lang
    )
    await state.set_state(RecurringStates.waiting_amount)
    await safe_edit_text(
        callback.message,
        t("rec_ask_amount", lang, title=title, currency=currency),
        reply_markup=recurring_cancel_kb(lang),
    )
    await callback.answer()


@router.message(
    RecurringStates.waiting_title,
    F.text,
    ~F.text.in_(ALL_NAV_TEXTS),
    ~F.text.startswith("/"),
)
async def msg_rec_custom_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()[:100]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    currency = data.get("rec_currency", "EUR")
    await state.update_data(rec_title=title)
    await state.set_state(RecurringStates.waiting_amount)
    await message.answer(
        t("rec_ask_amount", lang, title=title, currency=currency),
        reply_markup=recurring_cancel_kb(lang),
        parse_mode="HTML",
    )


@router.message(
    RecurringStates.waiting_amount,
    F.text,
    ~F.text.in_(ALL_NAV_TEXTS),
    ~F.text.startswith("/"),
)
async def msg_rec_amount(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    title = data.get("rec_title", "Операция")
    amt = _parse_recurring_amount(message.text)
    if amt is None:
        await message.answer(
            t("invalid_tx_input", lang),
            reply_markup=recurring_cancel_kb(lang),
            parse_mode="HTML",
        )
        return

    await state.update_data(rec_amount=str(amt))
    await state.set_state(RecurringStates.waiting_period)
    await message.answer(
        t("rec_ask_period", lang, title=title),
        reply_markup=recurring_period_kb(lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("rec:period:"))
async def cb_rec_period(callback: CallbackQuery, state: FSMContext) -> None:
    period = callback.data.split(":")[-1]
    await state.update_data(rec_period=period)
    await state.set_state(RecurringStates.waiting_date)

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        lang = user.language if user else "ru"
        today_local = local_now(user.timezone if user else "UTC").date()

    await safe_edit_text(
        callback.message,
        t("rec_ask_date", lang),
        reply_markup=recurring_date_kb(today_local, lang=lang),
    )
    await callback.answer()


async def _finalize_recurring_creation(
    telegram_id: int, next_iso_date: str, state: FSMContext
) -> Optional[Tuple[str, object]]:
    data = await state.get_data()
    title = data.get("rec_title", "Операция")
    raw_amt = data.get("rec_amount")
    if not raw_amt:
        return None
    amount = Decimal(str(raw_amt))
    tx_type = data.get("rec_tx_type", "expense")
    period = data.get("rec_period", "monthly")

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return None
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


@router.callback_query(F.data.startswith("rec:date:"))
async def cb_rec_date_quick(callback: CallbackQuery, state: FSMContext) -> None:
    iso_date = callback.data.split("rec:date:")[-1]
    res = await _finalize_recurring_creation(callback.from_user.id, iso_date, state)
    if res is None:
        async with async_session_factory() as session:
            user = await get_user_by_telegram_id(session, callback.from_user.id)
            if user:
                text, kb = await _render_recurring_menu(session, user)
                await safe_edit_text(callback.message, text, reply_markup=kb)
        await callback.answer()
        return

    full_text, kb = res
    await safe_edit_text(callback.message, full_text, reply_markup=kb)
    await callback.answer()


@router.message(
    RecurringStates.waiting_date,
    F.text,
    ~F.text.in_(ALL_NAV_TEXTS),
    ~F.text.startswith("/"),
)
async def msg_rec_date_manual(message: Message, state: FSMContext) -> None:
    parsed_date = _parse_input_date(message.text)
    if not parsed_date:
        data = await state.get_data()
        lang = data.get("lang", "ru")
        await message.answer(
            t("rec_ask_date", lang),
            reply_markup=recurring_cancel_kb(lang),
            parse_mode="HTML",
        )
        return

    res = await _finalize_recurring_creation(
        message.from_user.id, parsed_date.isoformat(), state
    )
    if res is None:
        return
    full_text, kb = res
    await message.answer(full_text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("rec:view:"))
async def cb_rec_view(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
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
        await safe_edit_text(
            callback.message,
            _build_rec_detail_text(rec, lang),
            reply_markup=recurring_detail_kb(rec.id, lang),
        )
        await callback.answer()


@router.callback_query(F.data.startswith("rec:edit:amount:"))
async def cb_rec_edit_amount(callback: CallbackQuery, state: FSMContext) -> None:
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
        await state.set_state(RecurringStates.editing_amount)
        await state.update_data(edit_rec_id=rec.id, lang=user.language)
        await safe_edit_text(
            callback.message,
            t(
                "rec_edit_amount_prompt",
                user.language,
                title=rec.title,
                currency=rec.currency,
            ),
            reply_markup=recurring_cancel_kb(
                user.language, back_cb=f"rec:view:{rec.id}"
            ),
        )
        await callback.answer()


@router.message(
    RecurringStates.editing_amount,
    F.text,
    ~F.text.in_(ALL_NAV_TEXTS),
    ~F.text.startswith("/"),
)
async def msg_rec_edit_amount(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    rec_id = data.get("edit_rec_id")
    lang = data.get("lang", "ru")
    amt = _parse_recurring_amount(message.text)
    if amt is None or not rec_id:
        await message.answer(
            t("invalid_tx_input", lang),
            reply_markup=recurring_cancel_kb(
                lang, back_cb=f"rec:view:{rec_id}" if rec_id else "menu:recurring"
            ),
            parse_mode="HTML",
        )
        return

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            return
        rec = await update_recurring_transaction(
            session, rec_id=int(rec_id), user_id=user.id, amount=amt
        )
        await state.clear()
        if not rec:
            return
        await message.answer(
            f"{t('rec_updated', user.language)}\n\n{_build_rec_detail_text(rec, user.language)}",
            reply_markup=recurring_detail_kb(rec.id, user.language),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("rec:edit:title:"))
async def cb_rec_edit_title(callback: CallbackQuery, state: FSMContext) -> None:
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
        await state.set_state(RecurringStates.editing_title)
        await state.update_data(edit_rec_id=rec.id, lang=user.language)
        await safe_edit_text(
            callback.message,
            t("rec_edit_title_prompt", user.language, title=rec.title),
            reply_markup=recurring_presets_kb(
                rec.tx_type,
                lang=user.language,
                prefix=f"rec:settitle:{rec.id}",
                back_cb=f"rec:view:{rec.id}",
            ),
        )
        await callback.answer()


@router.callback_query(F.data.startswith("rec:settitle:"))
async def cb_rec_set_title(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = callback.data.split(":", 3)
    if len(parts) < 4:
        await callback.answer()
        return
    rec_id = int(parts[2])
    new_title = parts[3]
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        rec = await update_recurring_transaction(
            session, rec_id=rec_id, user_id=user.id, title=new_title
        )
        if not rec:
            await callback.answer()
            return
        await safe_edit_text(
            callback.message,
            _build_rec_detail_text(rec, user.language),
            reply_markup=recurring_detail_kb(rec.id, user.language),
        )
        await callback.answer(t("rec_updated", user.language))


@router.message(
    RecurringStates.editing_title,
    F.text,
    ~F.text.in_(ALL_NAV_TEXTS),
    ~F.text.startswith("/"),
)
async def msg_rec_edit_title(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    rec_id = data.get("edit_rec_id")
    new_title = message.text.strip()[:100]
    if not rec_id or not new_title:
        return
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            return
        rec = await update_recurring_transaction(
            session, rec_id=int(rec_id), user_id=user.id, title=new_title
        )
        await state.clear()
        if not rec:
            return
        await message.answer(
            f"{t('rec_updated', user.language)}\n\n{_build_rec_detail_text(rec, user.language)}",
            reply_markup=recurring_detail_kb(rec.id, user.language),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("rec:edit:period:"))
async def cb_rec_edit_period(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
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
        await safe_edit_text(
            callback.message,
            t("rec_edit_period_prompt", user.language, title=rec.title),
            reply_markup=recurring_period_kb(
                lang=user.language,
                prefix=f"rec:setperiod:{rec.id}",
                back_cb=f"rec:view:{rec.id}",
            ),
        )
        await callback.answer()


@router.callback_query(F.data.startswith("rec:setperiod:"))
async def cb_rec_set_period(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = callback.data.split(":")
    rec_id = int(parts[2])
    new_period = parts[3]
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        rec = await update_recurring_transaction(
            session, rec_id=rec_id, user_id=user.id, period=new_period
        )
        if not rec:
            await callback.answer()
            return
        await safe_edit_text(
            callback.message,
            _build_rec_detail_text(rec, user.language),
            reply_markup=recurring_detail_kb(rec.id, user.language),
        )
        await callback.answer(t("rec_updated", user.language))


@router.callback_query(F.data.startswith("rec:edit:date:"))
async def cb_rec_edit_date(callback: CallbackQuery, state: FSMContext) -> None:
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
        today_local = local_now(user.timezone).date()
        await state.set_state(RecurringStates.editing_date)
        await state.update_data(edit_rec_id=rec.id, lang=user.language)
        await safe_edit_text(
            callback.message,
            t("rec_edit_date_prompt", user.language, title=rec.title),
            reply_markup=recurring_date_kb(
                today_local,
                lang=user.language,
                prefix=f"rec:setdate:{rec.id}",
                back_cb=f"rec:view:{rec.id}",
            ),
        )
        await callback.answer()


@router.callback_query(F.data.startswith("rec:setdate:"))
async def cb_rec_set_date(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = callback.data.split(":")
    rec_id = int(parts[2])
    iso_date = parts[3]
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        rec = await update_recurring_transaction(
            session, rec_id=rec_id, user_id=user.id, next_run_date=iso_date
        )
        if not rec:
            await callback.answer()
            return
        await process_due_recurring_for_user(session, user)
        await session.refresh(rec)
        await safe_edit_text(
            callback.message,
            _build_rec_detail_text(rec, user.language),
            reply_markup=recurring_detail_kb(rec.id, user.language),
        )
        await callback.answer(t("rec_updated", user.language))


@router.message(
    RecurringStates.editing_date,
    F.text,
    ~F.text.in_(ALL_NAV_TEXTS),
    ~F.text.startswith("/"),
)
async def msg_rec_edit_date(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    rec_id = data.get("edit_rec_id")
    lang = data.get("lang", "ru")
    parsed_date = _parse_input_date(message.text)
    if not parsed_date or not rec_id:
        await message.answer(
            t("rec_ask_date", lang),
            reply_markup=recurring_cancel_kb(
                lang, back_cb=f"rec:view:{rec_id}" if rec_id else "menu:recurring"
            ),
            parse_mode="HTML",
        )
        return

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            return
        rec = await update_recurring_transaction(
            session,
            rec_id=int(rec_id),
            user_id=user.id,
            next_run_date=parsed_date.isoformat(),
        )
        await state.clear()
        if not rec:
            return
        await process_due_recurring_for_user(session, user)
        await session.refresh(rec)
        await message.answer(
            f"{t('rec_updated', user.language)}\n\n{_build_rec_detail_text(rec, user.language)}",
            reply_markup=recurring_detail_kb(rec.id, user.language),
            parse_mode="HTML",
        )


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
        await safe_edit_text(
            callback.message,
            _build_rec_detail_text(rec, lang),
            reply_markup=recurring_detail_kb(rec.id, lang),
        )
        await callback.answer(
            t("status_active" if rec.is_active else "status_paused", lang)
        )


@router.callback_query(F.data.startswith("rec:del:"))
async def cb_rec_delete(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    rec_id = int(callback.data.split(":")[-1])
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        await delete_recurring_transaction(session, rec_id, user_id=user.id)
        await callback.answer(t("rec_deleted", user.language))
        text, kb = await _render_recurring_menu(session, user)
        await safe_edit_text(callback.message, text, reply_markup=kb)
