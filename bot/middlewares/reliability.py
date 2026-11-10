"""Reliability middleware: Update deduplication, per-user lock, secret redaction, and error boundary."""

import asyncio
import logging
import re
from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from bot.config import settings
from bot.database.crud import is_update_processed, mark_update_processed
from bot.database.session import async_session_factory
from bot.i18n.translations import t

logger = logging.getLogger(__name__)

_TOKEN_PATTERN = re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,50}\b")


class SecretRedactingFilter(logging.Filter):
    """Ensure bot tokens and sensitive credentials are never written to logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact_text(record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    _redact_text(a) if isinstance(a, str) else a for a in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: (_redact_text(v) if isinstance(v, str) else v)
                    for k, v in record.args.items()
                }
        return True


def _redact_text(text: str) -> str:
    if settings.bot_token and settings.bot_token in text:
        text = text.replace(settings.bot_token, "***REDACTED_TOKEN***")
    return _TOKEN_PATTERN.sub("***REDACTED_TOKEN***", text)


class ReliabilityMiddleware(BaseMiddleware):
    """
    Outer middleware attached to Dispatcher.update:
    1. Serializes concurrent updates per telegram_id using an asyncio.Lock.
    2. Prevents duplicate processing of the same Telegram Update.update_id.
    3. Catches all unhandled exceptions, logs structured diagnostics, and sends a
       clean user-friendly message without ever exposing tracebacks or SQL details.
    """

    def __init__(self, session_factory=None) -> None:
        super().__init__()
        self._session_factory = session_factory or async_session_factory
        self._user_locks: Dict[int, asyncio.Lock] = {}

    def _get_lock(self, telegram_id: Optional[int]) -> asyncio.Lock:
        key = telegram_id or 0
        lock = self._user_locks.get(key)
        if lock is None:
            # Cap lock dictionary size to avoid unbounded memory growth
            if len(self._user_locks) > 5000:
                unlocked = [k for k, v in self._user_locks.items() if not v.locked()]
                for k in unlocked[:2500]:
                    self._user_locks.pop(k, None)
            lock = asyncio.Lock()
            self._user_locks[key] = lock
        return lock

    @staticmethod
    def _extract_user_and_message(
        event: TelegramObject,
    ) -> tuple[Optional[int], Optional[Message], Optional[CallbackQuery], str]:
        if isinstance(event, Update):
            if event.message and event.message.from_user:
                lang = event.message.from_user.language_code or "ru"
                return event.message.from_user.id, event.message, None, lang
            if event.callback_query and event.callback_query.from_user:
                lang = event.callback_query.from_user.language_code or "ru"
                return (
                    event.callback_query.from_user.id,
                    event.callback_query.message,
                    event.callback_query,
                    lang,
                )
        elif isinstance(event, Message) and event.from_user:
            return event.from_user.id, event, None, event.from_user.language_code or "ru"
        elif isinstance(event, CallbackQuery) and event.from_user:
            return (
                event.from_user.id,
                event.message,
                event,
                event.from_user.language_code or "ru",
            )
        return None, None, None, "ru"

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        update_id: Optional[int] = getattr(event, "update_id", None)
        tg_id, msg, cb, lang = self._extract_user_and_message(event)
        lock = self._get_lock(tg_id)

        async with lock:
            # 1. Check if this Telegram update_id was already processed
            if update_id is not None:
                try:
                    async with self._session_factory() as session:
                        if await is_update_processed(session, update_id):
                            logger.info(
                                "Skipping already processed update_id=%s (user=%s)",
                                update_id,
                                tg_id,
                            )
                            return None
                except Exception as db_err:
                    logger.error(
                        "Database error checking update_id=%s: %s",
                        update_id,
                        type(db_err).__name__,
                    )

            # 2. Execute handler inside safety boundary
            try:
                result = await handler(event, data)
            except Exception as exc:
                logger.error(
                    "Unhandled error processing update_id=%s user=%s error=%s: %s",
                    update_id,
                    tg_id,
                    type(exc).__name__,
                    _redact_text(str(exc)),
                )
                await self._notify_user_error(msg, cb, lang)
                return None

            # 3. Record update_id as processed once handler succeeded
            if update_id is not None:
                try:
                    async with self._session_factory() as session:
                        await mark_update_processed(session, update_id, telegram_id=tg_id)
                except Exception as exc:
                    logger.warning(
                        "Could not mark update_id=%s as processed: %s",
                        update_id,
                        type(exc).__name__,
                    )

            return result

    @staticmethod
    async def _notify_user_error(
        msg: Optional[Message], cb: Optional[CallbackQuery], lang: str
    ) -> None:
        err_text = t("system_error_safe", lang)
        try:
            if cb is not None:
                await cb.answer(err_text, show_alert=True)
            elif msg is not None:
                await msg.answer(err_text, parse_mode="HTML")
        except Exception:
            pass

