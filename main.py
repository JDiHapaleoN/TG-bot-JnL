"""Entrypoint for Personal Finance Bot (aiogram 3 + Telegram Mini App + Scheduler + Backup & Lock)."""

import asyncio
import fcntl
import logging
import sys
from pathlib import Path
from typing import Optional

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.config import BASE_DIR, settings
from bot.database.session import dispose_db, init_db
from bot.handlers import menu, profile, recurring, start, stats, transactions
from bot.middlewares.reliability import ReliabilityMiddleware, SecretRedactingFilter
from bot.services.backup import create_database_backup, resolve_sqlite_db_path
from bot.services.scheduler import scheduler_loop
from bot.webapp.server import create_webapp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
for _handler in logging.root.handlers:
    _handler.addFilter(SecretRedactingFilter())

logger = logging.getLogger("finance_bot")


def build_dispatcher(session_factory=None) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(ReliabilityMiddleware(session_factory=session_factory))
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
        logger.warning("Could not set bot commands: %s", type(exc).__name__)


def _acquire_single_instance_lock() -> Optional[object]:
    """Prevent multiple conflicting bot instances from running simultaneously."""
    db_path = resolve_sqlite_db_path()
    lock_dir = db_path.parent if db_path else (BASE_DIR / "data")
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "bot.lock"
    lock_file = open(lock_path, "w", encoding="utf-8")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_file
    except OSError:
        lock_file.close()
        return None


async def main() -> None:
    db_path = resolve_sqlite_db_path()
    logger.info("Starting JnL-Bot...")
    logger.info("Active database: %s", db_path or settings.database_url)
    logger.info("Backup directory: %s", settings.backup_dir)
    if settings.s3_backup_enabled:
        logger.info(
            "Cloud S3 backup: ENABLED (bucket: %s, retention: %d days)",
            settings.s3_bucket_name,
            settings.s3_retention_days,
        )
    else:
        logger.info("Cloud S3 backup: DISABLED")

    if Path("/var/lib/jnl-bot/data").exists() and db_path:
        expected_db = Path("/var/lib/jnl-bot/data/finance_bot.db").resolve()
        if db_path.resolve() != expected_db:
            logger.warning(
                "DATABASE_URL points to %s, but standard persistent path is %s.",
                db_path,
                expected_db,
            )

    lock_handle = _acquire_single_instance_lock()
    if lock_handle is None:
        logger.error("Another instance of JnL-Bot is already running (bot.lock is held). Exiting.")
        sys.exit(1)

    try:
        # 1. Pre-migration backup if database already exists
        try:
            create_database_backup(tag="pre_init")
        except Exception as exc:
            logger.warning("Pre-init backup skipped: %s", exc)

        # 2. Initialize schema and run safe non-destructive migrations
        await init_db()
        logger.info("SQLite database initialized and verified (WAL mode enabled).")

        # 3. Create verified startup backup
        try:
            create_database_backup(tag="startup")
        except Exception as exc:
            logger.warning("Startup backup warning: %s", exc)

        # 4. Start embedded Telegram Mini App (WebApp) HTTP server safely (if enabled)
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
                try:
                    await scheduler_task
                except asyncio.CancelledError:
                    pass
                await bot.session.close()
                if runner:
                    await runner.cleanup()
                await dispose_db()
        else:
            logger.warning(
                "BOT_TOKEN is not set in .env. Running in WebApp + Scheduler mode only."
            )
            scheduler_task = asyncio.create_task(scheduler_loop(bot=None, interval_seconds=60))
            try:
                await asyncio.Event().wait()
            finally:
                scheduler_task.cancel()
                try:
                    await scheduler_task
                except asyncio.CancelledError:
                    pass
                if runner:
                    await runner.cleanup()
                await dispose_db()
    finally:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            lock_handle.close()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down Personal Finance Bot gracefully.")
