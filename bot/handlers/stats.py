"""Statistics view handlers."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.database.crud import (
    get_user_by_telegram_id,
    get_user_statistics,
    process_due_recurring_for_user,
)
from bot.database.models import User
from bot.database.session import async_session_factory
from bot.i18n.translations import t
from bot.keyboards.inline import back_to_menu_kb
from bot.services.currencies import format_money
from bot.services.geo import format_timezone_with_offset

router = Router(name="stats")


async def _build_stats_text(session, user: User) -> str:
    await process_due_recurring_for_user(session, user)
    stats = await get_user_statistics(session, user)
    lang = user.language
    cur = user.currency

    return t(
        "stats_card",
        lang,
        balance=format_money(stats.balance, cur),
        today_expense=format_money(stats.today_expense, cur, tx_type="expense"),
        week_expense=format_money(stats.week_expense, cur, tx_type="expense"),
        month_expense=format_money(stats.month_expense, cur, tx_type="expense"),
        total_expense=format_money(stats.total_expense, cur, tx_type="expense"),
        today_income=format_money(stats.today_income, cur, tx_type="income"),
        week_income=format_money(stats.week_income, cur, tx_type="income"),
        month_income=format_money(stats.month_income, cur, tx_type="income"),
        total_income=format_money(stats.total_income, cur, tx_type="income"),
        net_diff=format_money(stats.net_diff, cur, signed=True),
        timezone=format_timezone_with_offset(user.timezone),
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_registered:
            return
        text = await _build_stats_text(session, user)
        await message.answer(
            text,
            reply_markup=back_to_menu_kb(user.language),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "menu:stats")
async def cb_menu_stats(callback: CallbackQuery) -> None:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return
        text = await _build_stats_text(session, user)
        await callback.message.edit_text(
            text,
            reply_markup=back_to_menu_kb(user.language),
            parse_mode="HTML",
        )
        await callback.answer()

