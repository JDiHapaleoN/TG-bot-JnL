"""Async SQLAlchemy engine, WAL durability settings, and safe initialization."""

import logging
from typing import Optional

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
    Verifies database integrity without ever dropping or overwriting user tables.
    """
    eng = target_engine or engine
    async with eng.begin() as conn:
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
