"""Configuration settings for the Personal Finance Bot."""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _default_backup_dir() -> Path:
    env_backup = os.getenv("BACKUP_DIR", "").strip()
    if env_backup:
        p = Path(env_backup).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    # On Linux servers (like Ubuntu VPS), prefer /var/backups/jnl-bot if writable
    var_backups = Path("/var/backups")
    if var_backups.exists() and os.access(var_backups, os.W_OK):
        p = var_backups / "jnl-bot"
        p.mkdir(parents=True, exist_ok=True)
        return p

    # Otherwise store in a sibling directory outside the git repository
    sibling_backup = BASE_DIR.parent / "jnl_bot_backups"
    try:
        sibling_backup.mkdir(parents=True, exist_ok=True)
        return sibling_backup
    except OSError:
        fallback = BASE_DIR / "backups"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str
    backup_dir: Path
    webapp_host: str
    webapp_port: int
    webapp_url: str
    allow_dev_webapp_auth: bool


def get_settings() -> Settings:
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    default_db = f"sqlite+aiosqlite:///{data_dir / 'finance_bot.db'}"

    raw_db_url = os.getenv("DATABASE_URL", default_db).strip()
    # Normalize relative sqlite path to absolute path anchored at BASE_DIR
    if raw_db_url.startswith("sqlite+aiosqlite:///./"):
        rel_part = raw_db_url.replace("sqlite+aiosqlite:///./", "", 1)
        abs_db_path = (BASE_DIR / rel_part).resolve()
        abs_db_path.parent.mkdir(parents=True, exist_ok=True)
        raw_db_url = f"sqlite+aiosqlite:///{abs_db_path}"

    return Settings(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        database_url=raw_db_url,
        backup_dir=_default_backup_dir(),
        webapp_host=os.getenv("WEBAPP_HOST", "127.0.0.1").strip(),
        webapp_port=int(os.getenv("WEBAPP_PORT", "8095")),
        webapp_url=os.getenv("WEBAPP_URL", "").strip(),
        allow_dev_webapp_auth=os.getenv("ALLOW_DEV_WEBAPP_AUTH", "false").strip().lower() in ("1", "true", "yes"),
    )


settings = get_settings()
