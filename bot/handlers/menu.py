"""Main menu rendering and navigation handlers."""

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
from bot.keyboards.inline import main_menu_kb
from bot.services.currencies import format_money

router = Router(name="menu")


async def build_main_menu_payload(
    session: AsyncSession, user: User
) -> Tuple[str, InlineKeyboardMarkup]:
    # Process any due recurring transactions transparently when opening main menu
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
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_registered:
            from bot.handlers.start import start_registration_flow

            await start_registration_flow(message, state)
            return

        text, kb = await build_main_menu_payload(session, user)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


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
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

