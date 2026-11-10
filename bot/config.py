"""Configuration settings for the Personal Finance Bot."""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load local .env, then optional persistent external configs
load_dotenv(BASE_DIR / ".env")
load_dotenv(Path("/var/lib/jnl-bot/.env"))
load_dotenv(Path("/etc/jnl-bot/s3_backup.env"))


def _default_backup_dir() -> Path:
    env_backup = os.getenv("BACKUP_DIR", "").strip()
    if env_backup:
        p = Path(env_backup).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    # On Linux servers (like Ubuntu VPS), standard location is /var/backups/jnl-bot
    var_backups = Path("/var/backups")
    standard_dir = var_backups / "jnl-bot"
    if standard_dir.exists() or (var_backups.exists() and os.access(var_backups, os.W_OK)):
        try:
            standard_dir.mkdir(parents=True, exist_ok=True)
            return standard_dir
        except OSError:
            pass

    # Otherwise store in a sibling directory outside the git repository
    sibling_backup = BASE_DIR.parent / "jnl_bot_backups"
    try:
        sibling_backup.mkdir(parents=True, exist_ok=True)
        return sibling_backup
    except OSError:
        fallback = BASE_DIR / "backups"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _default_database_url() -> str:
    env_db = os.getenv("DATABASE_URL", "").strip()
    if env_db:
        if env_db.startswith("sqlite+aiosqlite:///./"):
            rel_part = env_db.replace("sqlite+aiosqlite:///./", "", 1)
            abs_db_path = (BASE_DIR / rel_part).resolve()
            abs_db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite+aiosqlite:///{abs_db_path}"
        return env_db

    # Standard production location on Linux VPS: /var/lib/jnl-bot/data/finance_bot.db
    var_lib = Path("/var/lib")
    standard_prod_dir = Path("/var/lib/jnl-bot/data")
    if standard_prod_dir.exists() or (var_lib.exists() and os.access(var_lib, os.W_OK)):
        try:
            standard_prod_dir.mkdir(parents=True, exist_ok=True)
            return f"sqlite+aiosqlite:///{standard_prod_dir / 'finance_bot.db'}"
        except OSError:
            pass

    # Fallback for local development
    local_data_dir = BASE_DIR / "data"
    local_data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{local_data_dir / 'finance_bot.db'}"


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str
    backup_dir: Path
    webapp_host: str
    webapp_port: int
    webapp_url: str
    allow_dev_webapp_auth: bool
    s3_backup_enabled: bool
    s3_endpoint_url: str
    s3_access_key_id: str
    s3_secret_access_key: str
    s3_bucket_name: str
    s3_region_name: str
    s3_encryption_key: str
    s3_retention_days: int


def get_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        database_url=_default_database_url(),
        backup_dir=_default_backup_dir(),
        webapp_host=os.getenv("WEBAPP_HOST", "127.0.0.1").strip(),
        webapp_port=int(os.getenv("WEBAPP_PORT", "8095")),
        webapp_url=os.getenv("WEBAPP_URL", "").strip(),
        allow_dev_webapp_auth=os.getenv("ALLOW_DEV_WEBAPP_AUTH", "false").strip().lower() in ("1", "true", "yes"),
        s3_backup_enabled=os.getenv("S3_BACKUP_ENABLED", "false").strip().lower() in ("1", "true", "yes"),
        s3_endpoint_url=os.getenv("S3_ENDPOINT_URL", "").strip(),
        s3_access_key_id=os.getenv("S3_ACCESS_KEY_ID", "").strip(),
        s3_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY", "").strip(),
        s3_bucket_name=os.getenv("S3_BUCKET_NAME", "").strip(),
        s3_region_name=os.getenv("S3_REGION_NAME", "us-east-1").strip(),
        s3_encryption_key=os.getenv("S3_ENCRYPTION_KEY", "").strip(),
        s3_retention_days=int(os.getenv("S3_RETENTION_DAYS", "30")),
    )


settings = get_settings()
