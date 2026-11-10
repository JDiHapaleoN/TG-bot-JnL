"""Transaction logging (2-second instant entry + guided), history, edit, and delete handlers."""

import math
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
from bot.i18n.translations import t
from bot.keyboards.inline import (
    back_to_menu_kb,
    history_list_kb,
    tx_detail_kb,
    tx_saved_kb,
)
from bot.services.currencies import format_money
from bot.services.parser import parse_transaction_message
from bot.states.forms import TransactionStates

router = Router(name="transactions")
HISTORY_PAGE_SIZE = 6


def _format_tx_confirmation(tx: Transaction, user: User, new_balance) -> str:
    lang = user.language
    local_dt = to_local_datetime(tx.created_at, user.timezone)
    desc = tx.description or (
        t("no_description_expense", lang)
        if tx.tx_type == "expense"
        else t("no_description_income", lang)
    )
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


@router.callback_query(F.data == "menu:add_expense")
async def cb_add_expense_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return
        await state.set_state(TransactionStates.waiting_expense)
        await callback.message.edit_text(
            t("prompt_add_expense", user.language),
            reply_markup=back_to_menu_kb(user.language),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data == "menu:add_income")
async def cb_add_income_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return
        await state.set_state(TransactionStates.waiting_income)
        await callback.message.edit_text(
            t("prompt_add_income", user.language),
            reply_markup=back_to_menu_kb(user.language),
            parse_mode="HTML",
        )
        await callback.answer()


async def _render_history_page(session, user: User, offset: int = 0):
    lang = user.language
    txs, total = await get_user_transactions(
        session, user.id, limit=HISTORY_PAGE_SIZE, offset=offset
    )
    if total == 0:
        return t("history_empty", lang), back_to_menu_kb(lang)

    total_pages = max(1, math.ceil(total / HISTORY_PAGE_SIZE))
    current_page = (offset // HISTORY_PAGE_SIZE) + 1
    lines = [
        t("history_title", lang, total=total, page=current_page, total_pages=total_pages),
        "",
    ]
    for tx in txs:
        local_dt = to_local_datetime(tx.created_at, user.timezone)
        amt_str = format_money(tx.amount, tx.currency, tx_type=tx.tx_type)
        desc = tx.description or (
            t("no_description_expense", lang)
            if tx.tx_type == "expense"
            else t("no_description_income", lang)
        )
        lines.append(
            f"• <b>{amt_str}</b> — {desc} <i>({local_dt.strftime('%d.%m %H:%M')})</i>"
        )

    kb = history_list_kb(txs, offset=offset, total=total, limit=HISTORY_PAGE_SIZE, lang=lang)
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
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data.startswith("tx:view:"))
async def cb_tx_view(callback: CallbackQuery) -> None:
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

        lang = user.language
        local_dt = to_local_datetime(tx.created_at, user.timezone)
        desc = tx.description or (
            t("no_description_expense", lang)
            if tx.tx_type == "expense"
            else t("no_description_income", lang)
        )
        text = t(
            "tx_detail_view",
            lang,
            tx_id=tx.id,
            type_label=t("type_expense" if tx.tx_type == "expense" else "type_income", lang),
            formatted_amount=format_money(tx.amount, tx.currency, tx_type=tx.tx_type),
            currency=tx.currency,
            description=desc,
            date=local_dt.strftime("%d.%m.%Y"),
            time=local_dt.strftime("%H:%M"),
        )
        await callback.message.edit_text(
            text,
            reply_markup=tx_detail_kb(tx.id, offset=offset, lang=lang),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data.startswith("tx:edit:"))
async def cb_tx_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    tx_id = int(callback.data.split(":")[-1])
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
        await state.update_data(edit_tx_id=tx.id, edit_default_type=tx.tx_type)
        desc = tx.description or (
            t("no_description_expense", lang)
            if tx.tx_type == "expense"
            else t("no_description_income", lang)
        )
        text = t(
            "prompt_edit_tx",
            lang,
            tx_id=tx.id,
            formatted_amount=format_money(tx.amount, tx.currency, tx_type=tx.tx_type),
            description=desc,
        )
        await callback.message.edit_text(
            text,
            reply_markup=back_to_menu_kb(lang),
            parse_mode="HTML",
        )
        await callback.answer()


@router.message(TransactionStates.editing_tx, F.text)
async def msg_tx_edit_save(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    tx_id = data.get("edit_tx_id")
    default_type = data.get("edit_default_type", "expense")

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            return
        parsed = parse_transaction_message(message.text, default_type=default_type)
        if not parsed:
            await message.answer(t("invalid_tx_input", user.language), parse_mode="HTML")
            return

        tx = await update_transaction(
            session,
            tx_id=tx_id,
            user_id=user.id,
            amount=parsed.amount,
            description=parsed.description,
            tx_type=parsed.tx_type,
        )
        await state.clear()
        if not tx:
            await message.answer(t("tx_not_found", user.language), parse_mode="HTML")
            return

        new_balance = await get_user_balance(session, user.id)
        desc = tx.description or (
            t("no_description_expense", user.language)
            if tx.tx_type == "expense"
            else t("no_description_income", user.language)
        )
        await message.answer(
            t(
                "tx_updated",
                user.language,
                formatted_amount=format_money(tx.amount, tx.currency, tx_type=tx.tx_type),
                description=desc,
                balance=format_money(new_balance, user.currency),
            ),
            reply_markup=tx_saved_kb(tx.id, lang=user.language),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("tx:del:"))
async def cb_tx_delete(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    tx_id = int(callback.data.split(":")[-1])
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
        await callback.message.edit_text(
            t(
                "tx_deleted",
                user.language,
                balance=format_money(new_balance, user.currency),
            ),
            reply_markup=back_to_menu_kb(user.language),
            parse_mode="HTML",
        )
        await callback.answer()


@router.message(TransactionStates.waiting_expense, F.text)
async def msg_guided_expense(message: Message, state: FSMContext) -> None:
    await _handle_transaction_entry(message, state, default_type="expense")


@router.message(TransactionStates.waiting_income, F.text)
async def msg_guided_income(message: Message, state: FSMContext) -> None:
    await _handle_transaction_entry(message, state, default_type="income")


@router.message(F.text)
async def msg_instant_transaction_entry(message: Message, state: FSMContext) -> None:
    """
    Core 2-3 second instant transaction logger!
    Any plain text message starting with a number or +/- amount is saved right away.
    """
    await _handle_transaction_entry(message, state, default_type="expense")


async def _handle_transaction_entry(
    message: Message, state: FSMContext, default_type: str = "expense"
) -> None:
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

        await state.clear()
        tx = await add_transaction(
            session=session,
            user_id=user.id,
            tx_type=parsed.tx_type,
            amount=parsed.amount,
            currency=user.currency,
            description=parsed.description,
        )
        new_balance = await get_user_balance(session, user.id)
        confirm_text = _format_tx_confirmation(tx, user, new_balance)
        await message.answer(
            confirm_text,
            reply_markup=tx_saved_kb(tx.id, lang=user.language),
            parse_mode="HTML",
        )

