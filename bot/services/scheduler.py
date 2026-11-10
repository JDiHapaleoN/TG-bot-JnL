"""Background async scheduler for recurring operations and daily reminders."""

import asyncio
import logging
from datetime import date
from typing import Optional

from aiogram import Bot

from bot.database.crud import (
    get_all_registered_users,
    get_user_balance,
    local_now,
    process_due_recurring_for_user,
    update_user_fields,
)
from bot.database.session import async_session_factory
from bot.i18n.translations import t
from bot.services.currencies import format_money

logger = logging.getLogger(__name__)


async def run_scheduler_tick(bot: Optional[Bot] = None) -> None:
    """Single tick checking due recurring operations and daily reminders for all users."""
    async with async_session_factory() as session:
        users = await get_all_registered_users(session)
        for user in users:
            try:
                executed = await process_due_recurring_for_user(session, user)
                if executed and bot and user.notify_recurring:
                    new_balance = await get_user_balance(session, user.id)
                    for rec, tx in executed:
                        try:
                            next_fmt = date.fromisoformat(rec.next_run_date).strftime("%d.%m.%Y")
                        except Exception:
                            next_fmt = rec.next_run_date
                        msg = t(
                            "rec_auto_notification",
                            user.language,
                            formatted_amount=format_money(tx.amount, tx.currency, tx_type=tx.tx_type),
                            title=rec.title,
                            next_date=next_fmt,
                            balance=format_money(new_balance, user.currency),
                        )
                        await bot.send_message(user.telegram_id, msg, parse_mode="HTML")

                # Check daily expense reminder in user's local timezone
                if user.daily_reminder and bot:
                    user_now = local_now(user.timezone)
                    today_iso = user_now.date().isoformat()
                    if (
                        user_now.hour == user.reminder_hour
                        and user.last_reminder_date != today_iso
                    ):
                        await update_user_fields(
                            session, user.telegram_id, last_reminder_date=today_iso
                        )
                        await bot.send_message(
                            user.telegram_id,
                            t("daily_reminder_msg", user.language),
                            parse_mode="HTML",
                        )
            except Exception as exc:
                logger.warning("Scheduler error for user %s: %s", user.telegram_id, exc)


async def scheduler_loop(bot: Optional[Bot] = None, interval_seconds: int = 60) -> None:
    """Continuous background loop for executing scheduled tasks."""
    logger.info("Background scheduler started (interval=%ss).", interval_seconds)
    while True:
        try:
            await run_scheduler_tick(bot=bot)
        except asyncio.CancelledError:
            logger.info("Background scheduler stopped.")
            break
        except Exception as exc:
            logger.error("Unexpected scheduler loop error: %s", exc)
        await asyncio.sleep(interval_seconds)

