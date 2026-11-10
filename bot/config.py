"""Configuration settings for the Personal Finance Bot."""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str
    webapp_host: str
    webapp_port: int
    webapp_url: str


def get_settings() -> Settings:
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    default_db = f"sqlite+aiosqlite:///{data_dir / 'finance_bot.db'}"

    return Settings(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        database_url=os.getenv("DATABASE_URL", default_db).strip(),
        webapp_host=os.getenv("WEBAPP_HOST", "127.0.0.1").strip(),
        webapp_port=int(os.getenv("WEBAPP_PORT", "8095")),
        webapp_url=os.getenv("WEBAPP_URL", "").strip(),
    )


settings = get_settings()
