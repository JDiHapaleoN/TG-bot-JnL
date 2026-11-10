"""Async SQLAlchemy engine, WAL durability settings, and safe initialization."""

import logging
import sys
from typing import Optional, Tuple

# Transparently upgrade SQLite C-runtime to modern build if pysqlite3 is available
try:
    import pysqlite3
    sys.modules["sqlite3"] = pysqlite3
except ImportError:
    pass

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.config import settings
from bot.database.migrations import run_safe_migrations
from bot.database.models import Base

logger = logging.getLogger(__name__)


def parse_sqlite_version(ver_str: str) -> Tuple[int, ...]:
    """Parse SQLite version string into integer tuple."""
    parts = []
    for chunk in ver_str.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts)


def is_sqlite_wal_safe(ver_tuple: Tuple[int, ...]) -> bool:
    """
    Check if SQLite version contains the official WAL-reset fix.
    - Mainstream: >= 3.51.3
    - Official Backports: 3.50.7, 3.44.6
    """
    if ver_tuple >= (3, 51, 3):
        return True
    if ver_tuple[:3] in ((3, 50, 7), (3, 44, 6)):
        return True
    return False


def configure_sqlite_engine(target_engine: AsyncEngine) -> None:
    """Attach durability and concurrency PRAGMAs to a SQLite engine."""

    @event.listens_for(target_engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.close()


engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    connect_args={"timeout": 15} if settings.database_url.startswith("sqlite") else {},
)

if settings.database_url.startswith("sqlite"):
    configure_sqlite_engine(engine)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db(target_engine: Optional[AsyncEngine] = None) -> None:
    """
    Safely initialize database schema and run non-destructive migrations.
    Verifies database integrity and SQLite WAL-reset safety.
    """
    eng = target_engine or engine
    async with eng.begin() as conn:
        if str(eng.url).startswith("sqlite"):
            # Verify actual SQLite runtime version via SQL connection
            res_ver = await conn.execute(text("SELECT sqlite_version()"))
            ver_str = str(res_ver.scalar() or "0.0.0")
            ver_tuple = parse_sqlite_version(ver_str)

            if not is_sqlite_wal_safe(ver_tuple):
                msg = (
                    f"Insecure SQLite runtime version {ver_str}. "
                    "SQLite >= 3.51.3 or official backports (3.50.7 / 3.44.6) are required "
                    "to prevent the WAL-reset database corruption bug."
                )
                if settings.app_env == "production":
                    logger.critical("FATAL: %s", msg)
                    raise RuntimeError(f"FATAL: {msg}")
                else:
                    logger.warning("DEVELOPMENT WARNING: %s", msg)

        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(run_safe_migrations)

        if str(eng.url).startswith("sqlite"):
            res = await conn.execute(text("PRAGMA integrity_check"))
            status = res.scalar()
            if status != "ok":
                logger.error("Database integrity check reported: %s", status)
                raise RuntimeError(f"Database integrity check failed: {status}")


async def dispose_db(target_engine: Optional[AsyncEngine] = None) -> None:
    """Gracefully close all database connections."""
    eng = target_engine or engine
    await eng.dispose()
