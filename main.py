"""Entrypoint for Personal Finance Bot (aiogram 3 + Telegram Mini App + Scheduler)."""

import asyncio
import logging
import sys
from typing import Optional

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.config import settings
from bot.database.session import init_db
from bot.handlers import menu, profile, recurring, start, stats, transactions
from bot.services.scheduler import scheduler_loop
from bot.webapp.server import create_webapp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("finance_bot")


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(stats.router)
    dp.include_router(recurring.router)
    dp.include_router(profile.router)
    # transactions router is registered last so its quick-entry text handler catches plain amounts
    dp.include_router(transactions.router)
    return dp


async def setup_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Запуск / Главное меню"),
        BotCommand(command="menu", description="Главное меню и баланс"),
        BotCommand(command="stats", description="Статистика за день/неделю/месяц"),
        BotCommand(command="history", description="История операций"),
        BotCommand(command="recurring", description="Регулярные доходы и расходы"),
        BotCommand(command="profile", description="Мой профиль и настройки"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as exc:
        logger.warning("Could not set bot commands: %s", exc)


async def main() -> None:
    await init_db()
    logger.info("SQLite database initialized.")

    # Start embedded Telegram Mini App (WebApp) HTTP server safely (non-fatal if port is busy)
    runner: Optional[web.AppRunner] = None
    if settings.webapp_port > 0:
        try:
            webapp = create_webapp()
            runner = web.AppRunner(webapp)
            await runner.setup()
            site = web.TCPSite(runner, host=settings.webapp_host, port=settings.webapp_port)
            await site.start()
            logger.info(
                "Telegram Mini App (WebApp) server running at http://%s:%s",
                settings.webapp_host,
                settings.webapp_port,
            )
        except OSError as exc:
            logger.warning(
                "Could not bind WebApp port %s (%s). Continuing with Telegram Bot polling only.",
                settings.webapp_port,
                exc,
            )
            runner = None

    bot: Optional[Bot] = None
    token_valid = bool(
        settings.bot_token
        and settings.bot_token != "your_telegram_bot_token_here"
        and ":" in settings.bot_token
    )

    if token_valid:
        bot = Bot(token=settings.bot_token)
        dp = build_dispatcher()
        await setup_bot_commands(bot)
        scheduler_task = asyncio.create_task(scheduler_loop(bot=bot, interval_seconds=60))
        logger.info("Starting Telegram Bot polling...")
        try:
            await dp.start_polling(bot)
        finally:
            scheduler_task.cancel()
            await bot.session.close()
            if runner:
                await runner.cleanup()
    else:
        logger.warning(
            "BOT_TOKEN is not set in .env. Running in WebApp Preview + Scheduler mode only. "
            "Set BOT_TOKEN in .env to enable Telegram Bot polling."
        )
        scheduler_task = asyncio.create_task(scheduler_loop(bot=None, interval_seconds=60))
        try:
            await asyncio.Event().wait()
        finally:
            scheduler_task.cancel()
            if runner:
                await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down Personal Finance Bot.")
