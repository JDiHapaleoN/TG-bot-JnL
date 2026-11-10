"""System monitoring, disk space inspection, SQLite health probes, and Telegram admin alerts.

Tracks:
1. Timestamp and status of the latest successful local backup.
2. Timestamp and status of the latest successful cloud S3 backup.
3. Backup failure events.
4. Free disk space on the database / backup partitions.
5. SQLite availability, latency, and PRAGMA integrity_check.
6. Auto-updater failures.
7. Recurring operation failures.
Sends rate-limited critical alerts directly to ADMIN_TELEGRAM_ID via the Telegram Bot.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from bot.config import settings

logger = logging.getLogger("monitoring")


@dataclass
class MonitoringState:
    last_local_backup_time: Optional[str] = None
    last_local_backup_file: Optional[str] = None
    last_cloud_backup_time: Optional[str] = None
    last_cloud_backup_key: Optional[str] = None
    last_backup_error: Optional[str] = None
    last_update_status: Optional[str] = None
    last_update_error: Optional[str] = None
    last_recurring_error: Optional[str] = None
    consecutive_backup_failures: int = 0
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_STATE_FILE = Path("/var/lib/jnl-bot/data/monitoring_state.json")
_LAST_ALERT_TIMES: Dict[str, float] = {}
ALERT_COOLDOWN_SECONDS = 1800  # 30 minutes cooldown between duplicate alerts


def _get_state_file_path() -> Path:
    if _STATE_FILE.parent.exists():
        return _STATE_FILE
    return settings.backup_dir / "monitoring_state.json"


def load_monitoring_state() -> MonitoringState:
    p = _get_state_file_path()
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return MonitoringState(**data)
        except Exception as exc:
            logger.warning("Could not load monitoring state: %s", exc)
    return MonitoringState()


def save_monitoring_state(state: MonitoringState) -> None:
    p = _get_state_file_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        state.updated_at = datetime.now(timezone.utc).isoformat()
        p.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not save monitoring state: %s", exc)


def record_local_backup_success(backup_name: str) -> None:
    state = load_monitoring_state()
    state.last_local_backup_time = datetime.now(timezone.utc).isoformat()
    state.last_local_backup_file = backup_name
    state.consecutive_backup_failures = 0
    state.last_backup_error = None
    save_monitoring_state(state)


def record_cloud_backup_success(s3_key: str) -> None:
    state = load_monitoring_state()
    state.last_cloud_backup_time = datetime.now(timezone.utc).isoformat()
    state.last_cloud_backup_key = s3_key
    save_monitoring_state(state)


def record_backup_failure(error_msg: str, bot=None) -> None:
    state = load_monitoring_state()
    state.last_backup_error = error_msg
    state.consecutive_backup_failures += 1
    save_monitoring_state(state)

    if bot and settings.admin_telegram_id:
        import asyncio
        asyncio.create_task(
            send_admin_alert(
                bot,
                alert_key="backup_failure",
                title="⚠️ Сбой резервного копирования",
                details=f"Ошибка: {error_msg}\nПодряд сбоев: {state.consecutive_backup_failures}",
            )
        )


def check_disk_space(target_path: Optional[Path] = None) -> dict:
    """Check total, used, free disk space in bytes and percentage."""
    path_to_check = target_path or settings.backup_dir
    try:
        usage = shutil.disk_usage(str(path_to_check))
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        free_pct = (usage.free / usage.total) * 100 if usage.total > 0 else 0.0
        return {
            "total_bytes": usage.total,
            "free_bytes": usage.free,
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "free_pct": round(free_pct, 1),
            "is_critical": free_gb < 1.0 or free_pct < 8.0,
            "is_warning": free_gb < 2.5 or free_pct < 15.0,
        }
    except Exception as exc:
        logger.warning("Disk usage check failed for %s: %s", path_to_check, exc)
        return {"error": str(exc), "is_critical": False, "is_warning": False}


def check_sqlite_health(db_path: Optional[Path] = None) -> dict:
    """Probe SQLite responsiveness and integrity."""
    from bot.services.backup import resolve_sqlite_db_path
    path = db_path or resolve_sqlite_db_path()
    if not path or not path.exists():
        return {"accessible": False, "error": "Database file missing"}

    t0 = time.perf_counter()
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check")
        row = cur.fetchone()
        latency_ms = (time.perf_counter() - t0) * 1000
        cur.execute("SELECT COUNT(*) FROM users")
        users_cnt = cur.fetchone()[0]
        conn.close()
        return {
            "accessible": True,
            "integrity": row[0] if row else "unknown",
            "latency_ms": round(latency_ms, 2),
            "users_count": users_cnt,
            "is_healthy": (row and row[0] == "ok"),
        }
    except Exception as exc:
        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "accessible": False,
            "error": str(exc),
            "latency_ms": round(latency_ms, 2),
            "is_healthy": False,
        }


async def send_admin_alert(
    bot,
    alert_key: str,
    title: str,
    details: str,
    force: bool = False,
) -> bool:
    """Send a rate-limited alert message to settings.admin_telegram_id."""
    admin_id = settings.admin_telegram_id
    if not admin_id or not bot:
        return False

    now = time.time()
    last_sent = _LAST_ALERT_TIMES.get(alert_key, 0.0)
    if not force and (now - last_sent < ALERT_COOLDOWN_SECONDS):
        logger.debug("Suppressing duplicate alert '%s' (cooldown active)", alert_key)
        return False

    msg = (
        f"🚨 <b>JnL-Bot Alert: {title}</b>\n\n"
        f"<b>Время (UTC):</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"<b>Сервер:</b> {os.uname().nodename}\n\n"
        f"{details}"
    )

    try:
        await bot.send_message(chat_id=admin_id, text=msg, parse_mode="HTML")
        _LAST_ALERT_TIMES[alert_key] = now
        logger.info("Admin alert sent to %s for '%s'", admin_id, alert_key)
        return True
    except Exception as exc:
        logger.warning("Could not send admin alert to %s: %s", admin_id, exc)
        return False


async def run_system_health_check(bot=None) -> dict:
    """Execute full health diagnostic and dispatch alerts if critical issues found."""
    disk = check_disk_space()
    sql = check_sqlite_health()
    state = load_monitoring_state()

    alerts_triggered: List[str] = []

    # 1. Disk space alert
    if disk.get("is_critical"):
        alerts_triggered.append("disk_space_critical")
        if bot:
            await send_admin_alert(
                bot,
                alert_key="disk_space_critical",
                title="Критически мало места на диске!",
                details=f"Свободно: {disk.get('free_gb')} GB ({disk.get('free_pct')}%).\nТребуется срочная очистка диска VPS.",
            )

    # 2. SQLite integrity alert
    if not sql.get("is_healthy"):
        alerts_triggered.append("sqlite_unhealthy")
        if bot:
            await send_admin_alert(
                bot,
                alert_key="sqlite_unhealthy",
                title="Ошибка целостности базы данных!",
                details=f"Ошибка: {sql.get('error') or sql.get('integrity')}\nБаза недоступна или повреждена.",
            )

    # 3. Check for failed update flag
    update_fail_flag = Path("/var/lib/jnl-bot/data/update_failed.flag")
    if update_fail_flag.exists():
        alerts_triggered.append("update_failed")
        if bot:
            fail_reason = update_fail_flag.read_text(encoding="utf-8")
            await send_admin_alert(
                bot,
                alert_key="update_failed",
                title="Ошибка автоматического обновления!",
                details=f"Обновление из GitHub было отклонено.\nДетали:\n{fail_reason[:300]}",
            )

    return {
        "status": "healthy" if not alerts_triggered else "degraded",
        "disk": disk,
        "sqlite": sql,
        "monitoring_state": asdict(state),
        "alerts_triggered": alerts_triggered,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

