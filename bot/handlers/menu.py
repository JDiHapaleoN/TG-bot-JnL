"""Main menu rendering and persistent Reply Keyboard navigation handlers."""

from typing import Tuple

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud import (
    get_user_by_telegram_id,
    get_user_statistics,
    process_due_recurring_for_user,
)
from bot.database.models import User
from bot.database.session import async_session_factory
from bot.i18n.translations import t
from bot.keyboards.inline import (
    back_to_menu_kb,
    main_menu_kb,
    persistent_reply_kb,
    profile_settings_kb,
)
from bot.services.currencies import format_money
from bot.states.forms import TransactionStates

router = Router(name="menu")

MENU_BTN_TEXTS = {t("kb_menu", "ru"), t("kb_menu", "en")}
EXPENSE_BTN_TEXTS = {t("kb_expense", "ru"), t("kb_expense", "en")}
INCOME_BTN_TEXTS = {t("kb_income", "ru"), t("kb_income", "en")}
STATS_BTN_TEXTS = {t("kb_stats", "ru"), t("kb_stats", "en")}
HISTORY_BTN_TEXTS = {t("kb_history", "ru"), t("kb_history", "en")}
PROFILE_BTN_TEXTS = {t("kb_profile", "ru"), t("kb_profile", "en")}


async def build_main_menu_payload(
    session: AsyncSession, user: User
) -> Tuple[str, InlineKeyboardMarkup]:
    await process_due_recurring_for_user(session, user)
    stats = await get_user_statistics(session, user)
    lang = user.language

    text = t(
        "main_menu_card",
        lang,
        balance=format_money(stats.balance, user.currency),
        month_income=format_money(stats.month_income, user.currency, tx_type="income"),
        month_expense=format_money(stats.month_expense, user.currency, tx_type="expense"),
    )
    kb = main_menu_kb(lang=lang, telegram_id=user.telegram_id)
    return text, kb


@router.message(Command("menu"))
@router.message(F.text.in_(MENU_BTN_TEXTS))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_registered:
            from bot.handlers.start import start_registration_flow

            await start_registration_flow(message, state)
            return

        text, kb = await build_main_menu_payload(session, user)
        await message.answer(
            text,
            reply_markup=kb,
            parse_mode="HTML",
        )


@router.message(F.text.in_(EXPENSE_BTN_TEXTS))
async def msg_kb_expense(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_registered:
            from bot.handlers.start import start_registration_flow

            await start_registration_flow(message, state)
            return
        await state.set_state(TransactionStates.waiting_expense)
        await message.answer(
            t("prompt_add_expense", user.language),
            reply_markup=back_to_menu_kb(user.language),
            parse_mode="HTML",
        )


@router.message(F.text.in_(INCOME_BTN_TEXTS))
async def msg_kb_income(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_registered:
            from bot.handlers.start import start_registration_flow

            await start_registration_flow(message, state)
            return
        await state.set_state(TransactionStates.waiting_income)
        await message.answer(
            t("prompt_add_income", user.language),
            reply_markup=back_to_menu_kb(user.language),
            parse_mode="HTML",
        )


@router.message(F.text.in_(STATS_BTN_TEXTS))
async def msg_kb_stats(message: Message, state: FSMContext) -> None:
    await state.clear()
    from bot.handlers.stats import cmd_stats

    await cmd_stats(message)


@router.message(F.text.in_(HISTORY_BTN_TEXTS))
async def msg_kb_history(message: Message, state: FSMContext) -> None:
    from bot.handlers.transactions import cmd_history

    await cmd_history(message, state)


@router.message(F.text.in_(PROFILE_BTN_TEXTS))
async def msg_kb_profile(message: Message, state: FSMContext) -> None:
    from bot.handlers.profile import cmd_profile

    await cmd_profile(message, state)


@router.callback_query(F.data == "menu:home")
async def cb_menu_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return

        text, kb = await build_main_menu_payload(session, user)
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await callback.message.answer(
                text,
                reply_markup=persistent_reply_kb(user.language),
                parse_mode="HTML",
            )
        await callback.answer()
