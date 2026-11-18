"""Partner Mode handlers: permanent account linking, real-time expense alerts, partner stats & history."""

import logging
import math
from typing import Optional, Tuple

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.database.crud import (
    ensure_user_partner_code,
    get_transaction_by_id,
    get_user_by_id,
    get_user_by_telegram_id,
    get_user_statistics,
    get_user_transactions,
    link_partners_permanently,
    process_due_recurring_for_user,
    to_local_datetime,
)
from bot.database.models import Transaction, User
from bot.database.session import async_session_factory
from bot.handlers.menu import ALL_NAV_TEXTS
from bot.handlers.stats import _build_stats_text
from bot.i18n.translations import payment_method_label, t
from bot.keyboards.inline import (
    partner_back_kb,
    partner_dashboard_kb,
    partner_history_list_kb,
    partner_link_cancel_kb,
    partner_tx_detail_kb,
    partner_unlinked_kb,
    safe_edit_text,
)
from bot.services.categories import get_category_label
from bot.services.currencies import format_money
from bot.states.forms import PartnerStates

logger = logging.getLogger(__name__)
router = Router(name="partner")
PARTNER_HISTORY_PAGE_SIZE = 6


async def notify_partner_about_expense(
    bot, session, user: User, tx: Transaction
) -> None:
    """
    Send a real-time notification to the linked partner when an expense is logged.
    Never raises exceptions to the caller so transaction logging is never disrupted.
    """
    if not bot or not getattr(user, "partner_id", None) or tx.tx_type != "expense":
        return

    try:
        partner = await get_user_by_id(session, user.partner_id)
        if not partner or not partner.is_registered:
            return

        p_lang = partner.language
        user_stats = await get_user_statistics(session, user)
        local_dt = to_local_datetime(tx.created_at, partner.timezone)
        cat_label = get_category_label(
            getattr(tx, "category", "other"), lang=p_lang, tx_type="expense"
        )
        desc = f"{tx.description} ({cat_label})" if tx.description else cat_label
        pay_label = payment_method_label(
            getattr(tx, "payment_method", "card"), p_lang
        )

        alert_text = t(
            "partner_expense_alert",
            p_lang,
            partner_name=user.name,
            formatted_amount=format_money(tx.amount, tx.currency, tx_type="expense"),
            description=desc,
            payment_method=pay_label,
            date=local_dt.strftime("%d.%m.%Y"),
            time=local_dt.strftime("%H:%M"),
            month_expense=format_money(
                user_stats.month_expense, user.currency, tx_type="expense"
            ),
            month_income=format_money(
                user_stats.month_income, user.currency, tx_type="income"
            ),
        )
        if hasattr(bot, "send_message"):
            await bot.send_message(
                partner.telegram_id,
                alert_text,
                reply_markup=partner_dashboard_kb(p_lang),
                parse_mode="HTML",
            )
    except Exception as exc:
        logger.warning(
            "Could not send partner expense notification for user=%s: %s",
            user.telegram_id,
            type(exc).__name__,
        )


async def _render_partner_view(
    session, user: User
) -> Tuple[str, InlineKeyboardMarkup]:
    lang = user.language
    partner_code = await ensure_user_partner_code(session, user)

    partner: Optional[User] = None
    if getattr(user, "partner_id", None):
        partner = await get_user_by_id(session, user.partner_id)

    if partner is None:
        text = t("partner_unlinked_card", lang, partner_code=partner_code)
        return text, partner_unlinked_kb(lang)

    await process_due_recurring_for_user(session, user)
    await process_due_recurring_for_user(session, partner)
    partner_stats = await get_user_statistics(session, partner)
    my_stats = await get_user_statistics(session, user)

    p_cur = partner.currency
    my_cur = user.currency
    text = t(
        "partner_dashboard_card",
        lang,
        partner_name=partner.name,
        partner_code=partner_code,
        partner_balance=format_money(partner_stats.balance, p_cur),
        partner_month_income=format_money(
            partner_stats.month_income, p_cur, tx_type="income"
        ),
        partner_month_expense=format_money(
            partner_stats.month_expense, p_cur, tx_type="expense"
        ),
        partner_month_card=format_money(
            partner_stats.month_card_expense, p_cur, tx_type="expense"
        ),
        partner_month_cash=format_money(
            partner_stats.month_cash_expense, p_cur, tx_type="expense"
        ),
        my_month_income=format_money(my_stats.month_income, my_cur, tx_type="income"),
        my_month_expense=format_money(
            my_stats.month_expense, my_cur, tx_type="expense"
        ),
    )
    return text, partner_dashboard_kb(lang)


@router.message(Command("partner"))
async def cmd_partner(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_registered:
            from bot.handlers.start import start_registration_flow

            await start_registration_flow(message, state)
            return
        text, kb = await _render_partner_view(session, user)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "menu:partner")
async def cb_menu_partner(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return
        text, kb = await _render_partner_view(session, user)
        await safe_edit_text(callback.message, text, reply_markup=kb)
        await callback.answer()


@router.callback_query(F.data == "partner:link_start")
async def cb_partner_link_start(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return

        if getattr(user, "partner_id", None):
            partner = await get_user_by_id(session, user.partner_id)
            if partner is not None:
                await state.clear()
                text, kb = await _render_partner_view(session, user)
                await safe_edit_text(callback.message, text, reply_markup=kb)
                await callback.answer(
                    t("partner_error_already_linked", user.language), show_alert=True
                )
                return

        partner_code = await ensure_user_partner_code(session, user)
        await state.set_state(PartnerStates.waiting_code)
        await safe_edit_text(
            callback.message,
            t("prompt_enter_partner_code", user.language, partner_code=partner_code),
            reply_markup=partner_link_cancel_kb(user.language),
        )
        await callback.answer()


@router.message(
    PartnerStates.waiting_code,
    F.text,
    ~F.text.in_(ALL_NAV_TEXTS),
    ~F.text.startswith("/"),
)
async def msg_partner_code_entered(message: Message, state: FSMContext) -> None:
    raw_code = message.text.strip()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_registered:
            return
        lang = user.language
        status, partner_user = await link_partners_permanently(
            session, message.from_user.id, raw_code
        )

        if status == "invalid_code":
            await message.answer(
                t("partner_error_invalid_code", lang),
                reply_markup=partner_link_cancel_kb(lang),
                parse_mode="HTML",
            )
            return

        if status == "self_code":
            await message.answer(
                t("partner_error_self_code", lang),
                reply_markup=partner_link_cancel_kb(lang),
                parse_mode="HTML",
            )
            return

        if status == "target_linked":
            await message.answer(
                t("partner_error_target_linked", lang),
                reply_markup=partner_link_cancel_kb(lang),
                parse_mode="HTML",
            )
            return

        await state.clear()
        user = await get_user_by_telegram_id(session, message.from_user.id)
        dash_text, dash_kb = await _render_partner_view(session, user)

        if status == "already_linked":
            await message.answer(
                f"{t('partner_error_already_linked', lang)}\n\n{dash_text}",
                reply_markup=dash_kb,
                parse_mode="HTML",
            )
            return

        # status == "ok": notify the linked partner in real time
        if partner_user is not None:
            bot_instance = getattr(message, "bot", None)
            if bot_instance and hasattr(bot_instance, "send_message"):
                try:
                    await bot_instance.send_message(
                        partner_user.telegram_id,
                        t(
                            "partner_linked_notification",
                            partner_user.language,
                            user_name=user.name,
                        ),
                        reply_markup=partner_dashboard_kb(partner_user.language),
                        parse_mode="HTML",
                    )
                except Exception as exc:
                    logger.warning(
                        "Could not notify partner %s on link: %s",
                        partner_user.telegram_id,
                        type(exc).__name__,
                    )

        success_banner = t(
            "partner_link_success",
            lang,
            partner_name=partner_user.name if partner_user else "Partner",
        )
        await message.answer(
            f"{success_banner}\n\n{dash_text}",
            reply_markup=dash_kb,
            parse_mode="HTML",
        )


@router.callback_query(F.data == "partner:stats")
async def cb_partner_stats(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return
        if not getattr(user, "partner_id", None):
            text, kb = await _render_partner_view(session, user)
            await safe_edit_text(callback.message, text, reply_markup=kb)
            await callback.answer()
            return

        partner = await get_user_by_id(session, user.partner_id)
        if not partner:
            text, kb = await _render_partner_view(session, user)
            await safe_edit_text(callback.message, text, reply_markup=kb)
            await callback.answer()
            return

        stats_body = await _build_stats_text(
            session, partner, lang_override=user.language
        )
        full_text = t(
            "partner_stats_title",
            user.language,
            partner_name=partner.name,
            stats_body=stats_body,
        )
        await safe_edit_text(
            callback.message,
            full_text,
            reply_markup=partner_back_kb(user.language),
        )
        await callback.answer()


async def _render_partner_history_page(
    session, viewer: User, partner: User, offset: int = 0
) -> Tuple[str, InlineKeyboardMarkup]:
    lang = viewer.language
    txs, total = await get_user_transactions(
        session, partner.id, limit=PARTNER_HISTORY_PAGE_SIZE, offset=offset
    )
    if total == 0:
        return (
            t("partner_history_empty", lang, partner_name=partner.name),
            partner_back_kb(lang),
        )

    if offset >= total and offset > 0:
        offset = max(
            0, ((total - 1) // PARTNER_HISTORY_PAGE_SIZE) * PARTNER_HISTORY_PAGE_SIZE
        )
        txs, total = await get_user_transactions(
            session, partner.id, limit=PARTNER_HISTORY_PAGE_SIZE, offset=offset
        )

    total_pages = max(1, math.ceil(total / PARTNER_HISTORY_PAGE_SIZE))
    current_page = (offset // PARTNER_HISTORY_PAGE_SIZE) + 1
    lines = [
        t(
            "partner_history_title",
            lang,
            partner_name=partner.name,
            total=total,
            page=current_page,
            total_pages=total_pages,
        ),
        "",
    ]
    for tx in txs:
        local_dt = to_local_datetime(tx.created_at, viewer.timezone)
        amt_str = format_money(tx.amount, tx.currency, tx_type=tx.tx_type)
        cat_label = get_category_label(
            getattr(tx, "category", "other"), lang=lang, tx_type=tx.tx_type
        )
        pay_icon = "💵" if getattr(tx, "payment_method", "card") == "cash" else "💳"
        desc = f"{tx.description} ({cat_label})" if tx.description else cat_label
        lines.append(
            f"• {pay_icon} <b>{amt_str}</b> — {desc} <i>({local_dt.strftime('%d.%m %H:%M')})</i>"
        )

    kb = partner_history_list_kb(
        txs, offset=offset, total=total, limit=PARTNER_HISTORY_PAGE_SIZE, lang=lang
    )
    return "\n".join(lines), kb


@router.callback_query(F.data.startswith("partner:history:"))
async def cb_partner_history(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    offset = int(callback.data.split(":")[-1])
    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            return
        if not getattr(user, "partner_id", None):
            text, kb = await _render_partner_view(session, user)
            await safe_edit_text(callback.message, text, reply_markup=kb)
            await callback.answer()
            return

        partner = await get_user_by_id(session, user.partner_id)
        if not partner:
            text, kb = await _render_partner_view(session, user)
            await safe_edit_text(callback.message, text, reply_markup=kb)
            await callback.answer()
            return

        text, kb = await _render_partner_history_page(
            session, viewer=user, partner=partner, offset=offset
        )
        await safe_edit_text(callback.message, text, reply_markup=kb)
        await callback.answer()


@router.callback_query(F.data.startswith("partner:tx:"))
async def cb_partner_tx_detail(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = callback.data.split(":")
    tx_id = int(parts[2])
    offset = int(parts[3]) if len(parts) > 3 else 0

    async with async_session_factory() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_registered or not getattr(user, "partner_id", None):
            await callback.answer()
            return
        partner = await get_user_by_id(session, user.partner_id)
        if not partner:
            await callback.answer()
            return

        tx = await get_transaction_by_id(session, tx_id, user_id=partner.id)
        if not tx:
            await callback.answer(t("tx_not_found", user.language), show_alert=True)
            return

        lang = user.language
        local_dt = to_local_datetime(tx.created_at, user.timezone)
        cat_label = get_category_label(
            getattr(tx, "category", "other"), lang=lang, tx_type=tx.tx_type
        )
        base_desc = tx.description or cat_label
        pay_label = payment_method_label(getattr(tx, "payment_method", "card"), lang)

        text = t(
            "partner_tx_detail_view",
            lang,
            partner_name=partner.name,
            tx_id=tx.id,
            type_label=f"{t('type_expense' if tx.tx_type == 'expense' else 'type_income', lang)} ({cat_label})",
            formatted_amount=format_money(tx.amount, tx.currency, tx_type=tx.tx_type),
            payment_method=pay_label,
            currency=tx.currency,
            description=base_desc,
            date=local_dt.strftime("%d.%m.%Y"),
            time=local_dt.strftime("%H:%M"),
        )
        await safe_edit_text(
            callback.message,
            text,
            reply_markup=partner_tx_detail_kb(offset=offset, lang=lang),
        )
        await callback.answer()
