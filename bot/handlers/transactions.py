"""Transaction logging (verified DB commit before confirmation), history, edit, delete, and category handlers."""

import logging
import math
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.crud import (
    add_transaction,
    delete_transaction,
    get_transaction_by_id,
    get_user_balance,
    get_user_by_telegram_id,
    get_user_transactions,
    to_local_datetime,
    update_transaction,
)
from bot.database.models import Transaction, User
from bot.database.session import async_session_factory
from bot.handlers.menu import (
    EXPENSE_BTN_TEXTS,
    HISTORY_BTN_TEXTS,
    INCOME_BTN_TEXTS,
    MENU_BTN_TEXTS,
    PROFILE_BTN_TEXTS,
    STATS_BTN_TEXTS,
    build_main_menu_payload,
)
from bot.i18n.translations import t
from bot.keyboards.inline import (
    add_tx_category_kb,
    back_to_menu_kb,
    category_picker_kb,
    history_list_kb,
    safe_edit_text,
    selected_new_cat_kb,
    tx_detail_kb,
    tx_edit_kb,
    tx_saved_kb,
)
from bot.services.categories import detect_category, get_category_label
from bot.services.currencies import format_money
from bot.services.parser import parse_transaction_message
from bot.states.forms import TransactionStates

logger = logging.getLogger(__name__)
router = Router(name="transactions")
HISTORY_PAGE_SIZE = 6

ALL_NAV_TEXTS = (
    MENU_BTN_TEXTS
    | EXPENSE_BTN_TEXTS
    | INCOME_BTN_TEXTS
    | STATS_BTN_TEXTS
    | HISTORY_BTN_TEXTS
    | PROFILE_BTN_TEXTS
)


def _format_tx_confirmation(tx: Transaction, user: User, new_balance) -> str:
    lang = user.language
    local_dt = to_local_datetime(tx.created_at, user.timezone)
    cat_code = getattr(tx, "category", "other")
    cat_label = get_category_label(cat_code, lang=lang, tx_type=tx.tx_type)
    if tx.description:
        desc = f"{tx.description} ({cat_label})"
    else:
        desc = cat_label
    tpl_key = "expense_saved" if tx.tx_type == "expense" else "income_saved"
    return t(
        tpl_key,
        lang,
        formatted_amount=format_money(tx.amount, tx.currency, tx_type=tx.tx_type),
        description=desc,
        date=local_dt.strftime("%d.%m.%Y"),
        time=local_dt.strftime("%H:%M"),
        balance=format_money(new_balance, user.currency),
    )


def _build_tx_detail_text(tx: Transaction, user: User) -> str:
    lang = user.language
    local_dt = to_local_datetime(tx.created_at, user.timezone)
    cat_code = getattr(tx, "category", "other")
    cat_label = get_category_label(cat_code, lang=lang, tx_type=tx.tx_type)
    base_desc = tx.description or cat_label
    return t(
        "tx_detail_view",
        lang,
        tx_id=tx.id,
        type_label=f"{t('type_expense' if tx.tx_type == 'expense' else 'type_income', lang)} ({cat_label})",
        formatted_amount=format_money(tx.amount, tx.currency, tx_type=tx.tx_type),
        currency=tx.currency,
        description=base_desc,
        date=local_dt.strftime("%d.%m.%Y"),
        time=local_dt.strftime("%H:%M"),
    )


@router.callback_query(F.data == "menu:add_expense")
async def cb_add_expense_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return
        await state.set_state(TransactionStates.waiting_expense)
        await safe_edit_text(
            callback.message,
            t("prompt_add_expense", user.language),
            reply_markup=add_tx_category_kb(tx_type="expense", lang=user.language),
        )
        await callback.answer()


@router.callback_query(F.data == "menu:add_income")
async def cb_add_income_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return
        await state.set_state(TransactionStates.waiting_income)
        await safe_edit_text(
            callback.message,
            t("prompt_add_income", user.language),
            reply_markup=add_tx_category_kb(tx_type="income", lang=user.language),
        )
        await callback.answer()


@router.callback_query(F.data.startswith("tx:newcat:"))
async def cb_new_tx_category_selected(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    if len(parts) < 4:
        await callback.answer()
        return
    tx_type = parts[2]
    cat_code = parts[3]

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return
        lang = user.language
        target_state = (
            TransactionStates.waiting_income
            if tx_type == "income"
            else TransactionStates.waiting_expense
        )
        await state.set_state(target_state)
        await state.update_data(pending_category=cat_code, pending_tx_type=tx_type)
        cat_label = get_category_label(cat_code, lang=lang, tx_type=tx_type)
        tpl_key = (
            "prompt_add_income_cat" if tx_type == "income" else "prompt_add_expense_cat"
        )
        await safe_edit_text(
            callback.message,
            t(tpl_key, lang, category=cat_label),
            reply_markup=selected_new_cat_kb(tx_type=tx_type, lang=lang),
        )
        await callback.answer()


async def _render_history_page(session, user: User, offset: int = 0):
    lang = user.language
    txs, total = await get_user_transactions(
        session, user.id, limit=HISTORY_PAGE_SIZE, offset=offset
    )
    if total == 0:
        return t("history_empty", lang), back_to_menu_kb(lang)

    if offset >= total and offset > 0:
        offset = max(0, ((total - 1) // HISTORY_PAGE_SIZE) * HISTORY_PAGE_SIZE)
        txs, total = await get_user_transactions(
            session, user.id, limit=HISTORY_PAGE_SIZE, offset=offset
        )

    total_pages = max(1, math.ceil(total / HISTORY_PAGE_SIZE))
    current_page = (offset // HISTORY_PAGE_SIZE) + 1
    lines = [
        t("history_title", lang, total=total, page=current_page, total_pages=total_pages),
        "",
    ]
    for tx in txs:
        local_dt = to_local_datetime(tx.created_at, user.timezone)
        amt_str = format_money(tx.amount, tx.currency, tx_type=tx.tx_type)
        cat_label = get_category_label(
            getattr(tx, "category", "other"), lang=lang, tx_type=tx.tx_type
        )
        desc = f"{tx.description} ({cat_label})" if tx.description else cat_label
        lines.append(
            f"• <b>{amt_str}</b> — {desc} <i>({local_dt.strftime('%d.%m %H:%M')})</i>"
        )

    kb = history_list_kb(
        txs, offset=offset, total=total, limit=HISTORY_PAGE_SIZE, lang=lang
    )
    return "\n".join(lines), kb


@router.message(Command("history"))
async def cmd_history(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_registered:
            return
        text, kb = await _render_history_page(session, user, offset=0)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("menu:history:"))
async def cb_menu_history(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    offset = int(callback.data.split(":")[-1])
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return
        text, kb = await _render_history_page(session, user, offset=offset)
        await safe_edit_text(callback.message, text, reply_markup=kb)
        await callback.answer()


@router.callback_query(F.data.startswith("tx:view:"))
async def cb_tx_view(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = callback.data.split(":")
    tx_id = int(parts[2])
    offset = int(parts[3]) if len(parts) > 3 else 0

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        tx = await get_transaction_by_id(session, tx_id, user_id=user.id)
        if not tx:
            await callback.answer(t("tx_not_found", user.language), show_alert=True)
            return

        await safe_edit_text(
            callback.message,
            _build_tx_detail_text(tx, user),
            reply_markup=tx_detail_kb(tx.id, offset=offset, lang=user.language),
        )
        await callback.answer()


@router.callback_query(F.data.startswith("tx:cat:"))
async def cb_tx_pick_category(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = callback.data.split(":")
    tx_id = int(parts[2])
    offset: Optional[int] = int(parts[3]) if len(parts) > 3 else None

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        tx = await get_transaction_by_id(session, tx_id, user_id=user.id)
        if not tx:
            await callback.answer(t("tx_not_found", user.language), show_alert=True)
            return
        await safe_edit_text(
            callback.message,
            t("choose_cat_prompt", user.language, tx_id=tx.id),
            reply_markup=category_picker_kb(
                tx.id, tx_type=tx.tx_type, lang=user.language, offset=offset
            ),
        )
        await callback.answer()


@router.callback_query(F.data.startswith("tx:setcat:"))
async def cb_tx_set_category(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = callback.data.split(":")
    tx_id = int(parts[2])
    cat_code = parts[3]
    offset: Optional[int] = int(parts[4]) if len(parts) > 4 else None

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        tx = await update_transaction(
            session, tx_id=tx_id, user_id=user.id, category=cat_code
        )
        if not tx:
            await callback.answer(t("tx_not_found", user.language), show_alert=True)
            return

        if offset is not None:
            await safe_edit_text(
                callback.message,
                _build_tx_detail_text(tx, user),
                reply_markup=tx_detail_kb(tx.id, offset=offset, lang=user.language),
            )
        else:
            new_balance = await get_user_balance(session, user.id)
            confirm_text = _format_tx_confirmation(tx, user, new_balance)
            await safe_edit_text(
                callback.message,
                confirm_text,
                reply_markup=tx_saved_kb(tx.id, lang=user.language),
            )

        cat_label = get_category_label(cat_code, lang=user.language, tx_type=tx.tx_type)
        await callback.answer(t("cat_updated", user.language, category=cat_label))


@router.callback_query(F.data.startswith("tx:flip:"))
async def cb_tx_flip_type(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = callback.data.split(":")
    tx_id = int(parts[2])
    offset: Optional[int] = int(parts[3]) if len(parts) > 3 else None

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        tx = await get_transaction_by_id(session, tx_id, user_id=user.id)
        if not tx:
            await callback.answer(t("tx_not_found", user.language), show_alert=True)
            return

        new_type = "income" if tx.tx_type == "expense" else "expense"
        new_cat = detect_category(tx.description or "", tx_type=new_type)
        tx = await update_transaction(
            session,
            tx_id=tx_id,
            user_id=user.id,
            tx_type=new_type,
            category=new_cat,
        )
        if offset is not None:
            await safe_edit_text(
                callback.message,
                _build_tx_detail_text(tx, user),
                reply_markup=tx_detail_kb(tx.id, offset=offset, lang=user.language),
            )
        else:
            new_balance = await get_user_balance(session, user.id)
            await safe_edit_text(
                callback.message,
                _format_tx_confirmation(tx, user, new_balance),
                reply_markup=tx_saved_kb(tx.id, lang=user.language),
            )
        await callback.answer(t("tx_type_flipped", user.language))


@router.callback_query(F.data.startswith("tx:edit:"))
async def cb_tx_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    tx_id = int(parts[2])
    offset: Optional[int] = int(parts[3]) if len(parts) > 3 else None

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        tx = await get_transaction_by_id(session, tx_id, user_id=user.id)
        if not tx:
            await callback.answer(t("tx_not_found", user.language), show_alert=True)
            return

        lang = user.language
        await state.set_state(TransactionStates.editing_tx)
        await state.update_data(
            edit_tx_id=tx.id, edit_default_type=tx.tx_type, edit_offset=offset
        )
        cat_label = get_category_label(
            getattr(tx, "category", "other"), lang=lang, tx_type=tx.tx_type
        )
        desc = f"{tx.description} ({cat_label})" if tx.description else cat_label
        text = t(
            "prompt_edit_tx",
            lang,
            tx_id=tx.id,
            formatted_amount=format_money(tx.amount, tx.currency, tx_type=tx.tx_type),
            description=desc,
        )
        await safe_edit_text(
            callback.message,
            text,
            reply_markup=tx_edit_kb(tx.id, offset=offset, lang=lang),
        )
        await callback.answer()


@router.message(
    TransactionStates.editing_tx,
    F.text,
    ~F.text.in_(ALL_NAV_TEXTS),
    ~F.text.startswith("/"),
)
async def msg_tx_edit_save(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    tx_id = data.get("edit_tx_id")
    default_type = data.get("edit_default_type", "expense")
    offset: Optional[int] = data.get("edit_offset")

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not tx_id:
            return
        existing_tx = await get_transaction_by_id(session, int(tx_id), user_id=user.id)
        if not existing_tx:
            await state.clear()
            await message.answer(t("tx_not_found", user.language), parse_mode="HTML")
            return

        raw_text = message.text.strip()
        parsed = parse_transaction_message(raw_text, default_type=default_type)

        if parsed is not None:
            # Keep existing description & category if user only sent a new amount
            new_desc = parsed.description if parsed.description else None
            tx = await update_transaction(
                session,
                tx_id=int(tx_id),
                user_id=user.id,
                amount=parsed.amount,
                description=new_desc,
                tx_type=parsed.tx_type,
            )
        else:
            # If user sent text without numbers (e.g. a new description), update description
            if raw_text.startswith("-") or raw_text.startswith("−") or raw_text == "0":
                await message.answer(
                    t("invalid_tx_input", user.language),
                    reply_markup=tx_edit_kb(int(tx_id), offset=offset, lang=user.language),
                    parse_mode="HTML",
                )
                return
            detected_cat = detect_category(raw_text, tx_type=existing_tx.tx_type)
            new_cat = (
                detected_cat
                if detected_cat not in ("other", "other_income")
                else existing_tx.category
            )
            tx = await update_transaction(
                session,
                tx_id=int(tx_id),
                user_id=user.id,
                description=raw_text[:255],
                category=new_cat,
            )

        await state.clear()
        if not tx:
            await message.answer(t("tx_not_found", user.language), parse_mode="HTML")
            return

        new_balance = await get_user_balance(session, user.id)
        cat_label = get_category_label(
            getattr(tx, "category", "other"), lang=user.language, tx_type=tx.tx_type
        )
        desc = f"{tx.description} ({cat_label})" if tx.description else cat_label
        kb = (
            tx_detail_kb(tx.id, offset=offset, lang=user.language)
            if offset is not None
            else tx_saved_kb(tx.id, lang=user.language)
        )
        await message.answer(
            t(
                "tx_updated",
                user.language,
                formatted_amount=format_money(tx.amount, tx.currency, tx_type=tx.tx_type),
                description=desc,
                balance=format_money(new_balance, user.currency),
            ),
            reply_markup=kb,
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("tx:del:"))
async def cb_tx_delete(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = callback.data.split(":")
    tx_id = int(parts[2])
    offset: Optional[int] = int(parts[3]) if len(parts) > 3 else None

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer()
            return
        deleted = await delete_transaction(session, tx_id=tx_id, user_id=user.id)
        if not deleted:
            await callback.answer(t("tx_not_found", user.language), show_alert=True)
            return
        new_balance = await get_user_balance(session, user.id)

        if offset is not None:
            hist_text, hist_kb = await _render_history_page(session, user, offset=offset)
            del_notice = t(
                "tx_deleted",
                user.language,
                balance=format_money(new_balance, user.currency),
            )
            await safe_edit_text(
                callback.message,
                f"{del_notice}\n\n{hist_text}",
                reply_markup=hist_kb,
            )
        else:
            await safe_edit_text(
                callback.message,
                t(
                    "tx_deleted",
                    user.language,
                    balance=format_money(new_balance, user.currency),
                ),
                reply_markup=back_to_menu_kb(user.language),
            )
        await callback.answer()


@router.message(
    TransactionStates.waiting_expense,
    F.text,
    ~F.text.in_(ALL_NAV_TEXTS),
    ~F.text.startswith("/"),
)
async def msg_guided_expense(message: Message, state: FSMContext) -> None:
    await _handle_transaction_entry(message, state, default_type="expense")


@router.message(
    TransactionStates.waiting_income,
    F.text,
    ~F.text.in_(ALL_NAV_TEXTS),
    ~F.text.startswith("/"),
)
async def msg_guided_income(message: Message, state: FSMContext) -> None:
    await _handle_transaction_entry(message, state, default_type="income")


@router.message(F.text.startswith("/"))
async def msg_unknown_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        lang = user.language if user else "ru"
        await message.answer(
            t("unknown_command", lang),
            reply_markup=back_to_menu_kb(lang),
            parse_mode="HTML",
        )


@router.message(F.text)
async def msg_instant_transaction_entry(message: Message, state: FSMContext) -> None:
    """
    Core 2-3 second instant transaction logger!
    Any plain text message starting with a number or +amount is validated,
    committed to the database first, verified, and only then confirmed.
    """
    await _handle_transaction_entry(message, state, default_type="expense")


async def _handle_transaction_entry(
    message: Message, state: FSMContext, default_type: str = "expense"
) -> None:
    data = await state.get_data() if hasattr(state, "get_data") else {}
    pending_category: Optional[str] = data.get("pending_category")

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_registered:
            from bot.handlers.start import start_registration_flow

            await start_registration_flow(message, state)
            return

        parsed = parse_transaction_message(message.text, default_type=default_type)
        if not parsed:
            await message.answer(
                t("invalid_tx_input", user.language),
                reply_markup=back_to_menu_kb(user.language),
                parse_mode="HTML",
            )
            return

        idem_key = None
        if message.chat and message.message_id:
            idem_key = f"msg:{message.chat.id}:{message.message_id}"

        try:
            tx = await add_transaction(
                session=session,
                user_id=user.id,
                tx_type=parsed.tx_type,
                amount=parsed.amount,
                currency=user.currency,
                description=parsed.description,
                category=pending_category,
                idempotency_key=idem_key,
            )
            if tx is None or tx.id is None:
                raise RuntimeError("Transaction was not persisted")
            new_balance = await get_user_balance(session, user.id)
        except Exception as exc:
            logger.error(
                "Failed to persist transaction for user=%s: %s",
                user.telegram_id,
                type(exc).__name__,
            )
            await message.answer(
                t("db_save_error", user.language),
                reply_markup=back_to_menu_kb(user.language),
                parse_mode="HTML",
            )
            return

        await state.clear()
        confirm_text = _format_tx_confirmation(tx, user, new_balance)
        await message.answer(
            confirm_text,
            reply_markup=tx_saved_kb(tx.id, lang=user.language),
            parse_mode="HTML",
        )


@router.callback_query()
async def cb_fallback_unhandled(callback: CallbackQuery, state: FSMContext) -> None:
    """Catch-all for any stale or unrecognized callback buttons so buttons never hang."""
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if user and user.is_registered:
            text, kb = await build_main_menu_payload(session, user)
            await safe_edit_text(callback.message, text, reply_markup=kb)
    await callback.answer()
