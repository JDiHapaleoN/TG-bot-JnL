"""Statistics view handlers with category breakdown."""

from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.crud import (
    get_user_by_telegram_id,
    get_user_statistics,
    process_due_recurring_for_user,
)
from bot.database.models import User
from bot.database.session import async_session_factory
from bot.i18n.translations import t
from bot.keyboards.inline import back_to_menu_kb, safe_edit_text
from bot.services.categories import get_category_label
from bot.services.currencies import format_money
from bot.services.geo import format_timezone_with_offset

router = Router(name="stats")


async def _build_stats_text(session, user: User) -> str:
    await process_due_recurring_for_user(session, user)
    stats = await get_user_statistics(session, user)
    lang = user.language
    cur = user.currency

    base = t(
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

    if stats.month_by_category and stats.month_expense > 0:
        header = (
            "\n\n🏷 <b>По категориям (за месяц):</b>"
            if lang == "ru"
            else "\n\n🏷 <b>By Category (This Month):</b>"
        )
        cat_lines = [header]
        sorted_cats = sorted(
            stats.month_by_category.items(), key=lambda kv: kv[1], reverse=True
        )
        for cat_code, amt in sorted_cats:
            pct = (amt / stats.month_expense) * 100
            label = get_category_label(cat_code, lang=lang, tx_type="expense")
            cat_lines.append(
                f"• {label}: <code>{format_money(amt, cur, tx_type='expense')}</code> ({pct:.0f}%)"
            )
        base += "\n".join(cat_lines)

    return base


@router.message(Command("stats"))
async def cmd_stats(message: Message, state: Optional[FSMContext] = None) -> None:
    if state is not None:
        await state.clear()
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
async def cb_menu_stats(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return
        text = await _build_stats_text(session, user)
        await safe_edit_text(
            callback.message,
            text,
            reply_markup=back_to_menu_kb(user.language),
        )
        await callback.answer()
