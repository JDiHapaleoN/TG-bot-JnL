"""Diagnostic utility for verifying SQLite runtime version, WAL mode, synchronous=FULL, and concurrency."""

from __future__ import annotations

import asyncio
import os
import platform
import sqlite3
import sys
import tempfile
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.database.session import configure_sqlite_engine, is_sqlite_wal_safe, parse_sqlite_version


def get_sqlite_runtime_info() -> dict:
    return {
        "sqlite_version": sqlite3.sqlite_version,
        "sqlite_version_info": sqlite3.sqlite_version_info,
        "python_sqlite_module_version": getattr(sqlite3, "version", "builtin"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
    }


def analyze_sqlite_version(sqlite_ver_info: tuple[int, ...]) -> dict:
    """
    Evaluate SQLite runtime version against the WAL-reset bug advisory.
    The WAL-reset bug affects all versions prior to 3.51.3 except verified backports (3.50.7, 3.44.6).
    """
    version_str = ".".join(str(x) for x in sqlite_ver_info[:3])
    recommendations = []
    is_safe = is_sqlite_wal_safe(sqlite_ver_info)

    if not is_safe:
        recommendations.append(
            f"VULNERABLE RUNTIME: SQLite {version_str} does not include the official WAL-reset fix. "
            "SQLite >= 3.51.3 or backports (3.50.7 / 3.44.6) are required. "
            "Run 'deploy/install_sqlite_amalgamation.py' to compile a safe runtime in .venv."
        )
    else:
        recommendations.append(f"VERIFIED SAFE: SQLite {version_str} includes the official WAL-reset fix.")

    return {
        "version": version_str,
        "wal_reset_safe": is_safe,
        "recommendations": recommendations,
    }


async def verify_runtime_pragmas(db_path: Path) -> dict:
    """Verify that SQLAlchemy engine applies PRAGMA journal_mode=WAL, synchronous=FULL, busy_timeout=15000."""
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(url, connect_args={"timeout": 15.0})
    configure_sqlite_engine(engine)

    results = {}
    async with engine.connect() as conn:
        journal_mode = (await conn.execute(text("PRAGMA journal_mode"))).scalar()
        synchronous = (await conn.execute(text("PRAGMA synchronous"))).scalar()
        busy_timeout = (await conn.execute(text("PRAGMA busy_timeout"))).scalar()
        foreign_keys = (await conn.execute(text("PRAGMA foreign_keys"))).scalar()

        # Also query the actual SQL engine version directly from the connection
        sql_ver = (await conn.execute(text("SELECT sqlite_version()"))).scalar()

        results["journal_mode"] = str(journal_mode).lower()
        results["synchronous"] = int(synchronous) if synchronous is not None else -1
        results["busy_timeout"] = int(busy_timeout) if busy_timeout is not None else -1
        results["foreign_keys"] = int(foreign_keys) if foreign_keys is not None else -1
        results["sqlite_version"] = str(sql_ver)

    await engine.dispose()
    return results


async def run_concurrency_stress_test(db_path: Path, writers_count: int = 15, reads_count: int = 30) -> bool:
    """Stress test WAL mode with concurrent async readers and writers."""
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(url, connect_args={"timeout": 15.0})
    configure_sqlite_engine(engine)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS stress_test ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "worker_id INTEGER NOT NULL, "
                "payload TEXT NOT NULL"
                ")"
            )
        )

    errors = []

    async def _writer(w_id: int):
        try:
            async with session_factory() as session:
                for i in range(5):
                    await session.execute(
                        text("INSERT INTO stress_test (worker_id, payload) VALUES (:w, :p)"),
                        {"w": w_id, "p": f"write_{i}"},
                    )
                    await session.commit()
                    await asyncio.sleep(0.01)
        except Exception as exc:
            errors.append(f"Writer {w_id} error: {exc}")

    async def _reader(r_id: int):
        try:
            async with session_factory() as session:
                for _ in range(5):
                    res = await session.execute(text("SELECT COUNT(*) FROM stress_test"))
                    _ = res.scalar()
                    await asyncio.sleep(0.01)
        except Exception as exc:
            errors.append(f"Reader {r_id} error: {exc}")

    tasks = [_writer(i) for i in range(writers_count)] + [_reader(j) for j in range(reads_count)]
    await asyncio.gather(*tasks)
    await engine.dispose()

    if errors:
        raise RuntimeError(f"Concurrency stress test failed with {len(errors)} errors: {errors[:3]}")
    return True


async def main_async() -> int:
    info = get_sqlite_runtime_info()
    print("=" * 60)
    print("JnL-Bot SQLite & WAL Diagnostic Utility")
    print("=" * 60)
    print(f"Runtime SQLite Version : {info['sqlite_version']}")
    print(f"Python sqlite3 Wrapper : {info['python_sqlite_module_version']}")
    print(f"Python Runtime Version : {info['python_version']}")
    print(f"Operating System       : {info['system']} {info['machine']} ({info['platform']})")
    print("-" * 60)

    analysis = analyze_sqlite_version(info["sqlite_version_info"])
    print("WAL Durability Assessment:")
    for rec in analysis["recommendations"]:
        print(f"  • {rec}")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "diag_test.db"
        pragmas = await verify_runtime_pragmas(test_db)
        print("Configured SQLite PRAGMAs:")
        print(f"  • journal_mode : {pragmas['journal_mode']} (Expected: wal)")
        print(f"  • synchronous  : {pragmas['synchronous']} (Expected: 2 / FULL)")
        print(f"  • busy_timeout : {pragmas['busy_timeout']} ms (Expected: 15000)")
        print(f"  • foreign_keys : {pragmas['foreign_keys']} (Expected: 1 / ON)")
        print(f"  • connection ver: {pragmas['sqlite_version']}")
        print("-" * 60)

        conn_tuple = parse_sqlite_version(pragmas["sqlite_version"])
        conn_safe = is_sqlite_wal_safe(conn_tuple)

        assert pragmas["journal_mode"] == "wal", f"journal_mode is {pragmas['journal_mode']}, expected wal"
        assert pragmas["synchronous"] in (2, 3), f"synchronous is {pragmas['synchronous']}, expected 2"

        print("Executing WAL Concurrency Stress Test (15 writers, 30 readers)...")
        await run_concurrency_stress_test(test_db, writers_count=15, reads_count=30)
        print("✅ Concurrency Stress Test PASSED: 0 locks, 0 errors.")

    if not conn_safe:
        print("❌ CRITICAL: The connection SQLite runtime fails WAL safety check.")
        print(f"   Detected version: {pragmas['sqlite_version']}. Required: >= 3.51.3 or backport (3.50.7 / 3.44.6).")
        return 1

    print("=" * 60)
    print("✅ All SQLite diagnostics and WAL checks completed successfully.")
    print("=" * 60)
    return 0


def main() -> None:
    code = asyncio.run(main_async())
    sys.exit(code)


if __name__ == "__main__":
    main()
