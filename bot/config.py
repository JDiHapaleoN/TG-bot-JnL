"""Configuration settings for the Personal Finance Bot."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

PROD_ENV_FILE = Path("/var/lib/jnl-bot/.env")
PROD_DATA_DIR = Path("/var/lib/jnl-bot/data")
PROD_DB_FILE = PROD_DATA_DIR / "finance_bot.db"
PROD_BACKUP_DIR = Path("/var/lib/jnl-bot/backups")


def _detect_app_env() -> str:
    """Determine active environment ('production', 'development', or 'testing') BEFORE loading .env."""
    env_override = os.getenv("APP_ENV", "").strip().lower()
    if env_override:
        return env_override
    if (
        Path("/var/lib/jnl-bot").exists()
        or (sys.platform == "linux" and os.path.exists("/opt/jnl-bot"))
        or str(BASE_DIR).startswith("/opt/jnl-bot")
    ):
        return "production"
    return "development"


def _load_environment_file(
    app_env: str,
    prod_env_file: Optional[Path] = None,
    dev_env_file: Optional[Path] = None,
) -> Path:
    """
    Select and load environment configuration strictly according to environment:
    - Production MUST load only from /var/lib/jnl-bot/.env and abort if missing/unreadable.
    - Development/testing may use repository-local .env.
    """
    target_prod = prod_env_file if prod_env_file is not None else PROD_ENV_FILE
    target_dev = dev_env_file if dev_env_file is not None else (BASE_DIR / ".env")

    if app_env == "production":
        if not target_prod.exists() or not target_prod.is_file():
            raise RuntimeError(
                f"CRITICAL CONFIGURATION ERROR: Canonical production configuration file '{target_prod}' is missing. "
                "Production startup aborted; refusing to fall back to repository .env."
            )
        if not os.access(target_prod, os.R_OK):
            raise RuntimeError(
                f"CRITICAL CONFIGURATION ERROR: Canonical production configuration file '{target_prod}' "
                f"is not readable by current user (UID {os.getuid()}). Startup aborted."
            )
        load_dotenv(target_prod, override=False)
        return target_prod

    # Development or testing mode
    if target_dev.exists() and target_dev.is_file():
        load_dotenv(target_dev, override=False)
        # If local .env declared APP_ENV=production, enforce canonical production config
        if os.getenv("APP_ENV", "").strip().lower() == "production":
            return _load_environment_file("production", prod_env_file=target_prod, dev_env_file=target_dev)
    return target_dev


def _resolve_production_database_url() -> str:
    """Enforce strict production database path. Fail closed with clear error on misconfiguration."""
    env_db = os.getenv("DATABASE_URL", "").strip()
    if env_db:
        # Strictly reject in-repo, relative, or legacy directories in production
        for forbidden in ("/opt/jnl-bot/data", "./data", "/var/backups", "finance_bot.db"):
            if forbidden in env_db and not env_db.startswith(f"sqlite+aiosqlite:///{PROD_DATA_DIR}"):
                raise RuntimeError(
                    f"CRITICAL CONFIGURATION ERROR: Prohibited database path in production: '{env_db}'. "
                    f"Production database must reside strictly at '{PROD_DB_FILE}' to guarantee data preservation."
                )
        return env_db

    if not PROD_DATA_DIR.exists():
        try:
            PROD_DATA_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RuntimeError(
                f"CRITICAL: Production data directory '{PROD_DATA_DIR}' does not exist and cannot be created: {exc}. "
                "Startup aborted to prevent silent fallback or database loss."
            )

    if not os.access(PROD_DATA_DIR, os.W_OK):
        raise RuntimeError(
            f"CRITICAL: Production data directory '{PROD_DATA_DIR}' is not writable by current user (UID {os.getuid()}). "
            "Startup aborted to prevent data loss."
        )

    return f"sqlite+aiosqlite:///{PROD_DB_FILE}"


def _resolve_production_backup_dir() -> Path:
    """Enforce strict production backup path. Fail closed with clear error on misconfiguration."""
    env_backup = os.getenv("BACKUP_DIR", "").strip()
    if env_backup:
        p = Path(env_backup).resolve()
        for forbidden in ("/opt/jnl-bot", "jnl_bot_backups", "/var/backups"):
            if forbidden in str(p) and not str(p).startswith(str(PROD_BACKUP_DIR)):
                raise RuntimeError(
                    f"CRITICAL CONFIGURATION ERROR: Prohibited backup path in production: '{env_backup}'. "
                    f"Production backups must reside strictly under '{PROD_BACKUP_DIR}'."
                )
    else:
        p = PROD_BACKUP_DIR

    if not p.exists():
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RuntimeError(
                f"CRITICAL: Production backup directory '{p}' does not exist and cannot be created: {exc}. "
                "Startup aborted."
            )

    if not os.access(p, os.W_OK):
        raise RuntimeError(
            f"CRITICAL: Production backup directory '{p}' is not writable by current user (UID {os.getuid()}). "
            "Startup aborted."
        )

    return p


def _default_database_url(app_env: Optional[str] = None) -> str:
    active_env = app_env if app_env is not None else _detect_app_env()
    if active_env == "production":
        return _resolve_production_database_url()

    env_db = os.getenv("DATABASE_URL", "").strip()
    if env_db:
        if env_db.startswith("sqlite+aiosqlite:///./"):
            rel_part = env_db.replace("sqlite+aiosqlite:///./", "", 1)
            abs_db_path = (BASE_DIR / rel_part).resolve()
            abs_db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite+aiosqlite:///{abs_db_path}"
        return env_db

    local_data_dir = BASE_DIR / "data"
    local_data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{local_data_dir / 'finance_bot.db'}"


def _default_backup_dir(app_env: Optional[str] = None) -> Path:
    active_env = app_env if app_env is not None else _detect_app_env()
    if active_env == "production":
        return _resolve_production_backup_dir()

    env_backup = os.getenv("BACKUP_DIR", "").strip()
    if env_backup:
        p = Path(env_backup).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    local_backup = BASE_DIR / "backups"
    local_backup.mkdir(parents=True, exist_ok=True)
    return local_backup


@dataclass(frozen=True)
class Settings:
    app_env: str
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
    s3_pbkdf2_iterations: int
    admin_telegram_id: Optional[int]


def get_settings() -> Settings:
    active_env = _detect_app_env()
    _load_environment_file(active_env)
    active_env = _detect_app_env()

    admin_raw = os.getenv("ADMIN_TELEGRAM_ID", "").strip()
    admin_id = int(admin_raw) if admin_raw.isdigit() else None

    return Settings(
        app_env=active_env,
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        database_url=_default_database_url(active_env),
        backup_dir=_default_backup_dir(active_env),
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
        s3_pbkdf2_iterations=int(os.getenv("S3_PBKDF2_ITERATIONS", "600000")),
        admin_telegram_id=admin_id,
    )


APP_ENV = _detect_app_env()
settings = get_settings()
