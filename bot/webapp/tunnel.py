"""Managed Cloudflare Quick Tunnel (trycloudflare.com) for zero-config HTTPS Telegram Mini App."""

import asyncio
import logging
import platform
import re
import shutil
import stat
import urllib.request
from pathlib import Path
from typing import Optional

from aiogram import Bot
from aiogram.types import MenuButtonWebApp, WebAppInfo

from bot.config import BASE_DIR, settings
from bot.services.backup import resolve_sqlite_db_path

logger = logging.getLogger(__name__)

_TRYCLOUDFLARE_RE = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
_active_tunnel_url: Optional[str] = None

CLOUDFLARED_BIN_PATH = BASE_DIR / "bin" / "cloudflared"
CLOUDFLARED_LINUX_AMD64_URL = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
)


def _url_state_file() -> Path:
    db_path = resolve_sqlite_db_path()
    data_dir = db_path.parent if db_path else (BASE_DIR / "data")
    return data_dir / "webapp_url.txt"


def get_active_webapp_url() -> str:
    """Return the active HTTPS URL for the Telegram Mini App (static config or dynamic tunnel)."""
    if settings.webapp_url and settings.webapp_url.startswith("https://"):
        return settings.webapp_url.rstrip("/")
    if _active_tunnel_url and _active_tunnel_url.startswith("https://"):
        return _active_tunnel_url.rstrip("/")
    try:
        state_file = _url_state_file()
        if state_file.exists():
            url = state_file.read_text(encoding="utf-8").strip()
            if url.startswith("https://"):
                return url.rstrip("/")
    except Exception:
        pass
    return ""


def ensure_cloudflared_binary() -> Optional[Path]:
    """
    Locate or download the standalone cloudflared binary on Linux x86_64 inside /opt/jnl-bot/bin/cloudflared.
    Never modifies system packages or outside directories.
    """
    if CLOUDFLARED_BIN_PATH.exists() and CLOUDFLARED_BIN_PATH.stat().st_size > 1_000_000:
        return CLOUDFLARED_BIN_PATH

    sys_bin = shutil.which("cloudflared")
    if sys_bin:
        return Path(sys_bin)

    if platform.system().lower() != "linux" or platform.machine().lower() not in (
        "x86_64",
        "amd64",
    ):
        return None

    try:
        CLOUDFLARED_BIN_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = CLOUDFLARED_BIN_PATH.with_suffix(".tmp")
        logger.info("Downloading standalone cloudflared binary to %s...", CLOUDFLARED_BIN_PATH)
        urllib.request.urlretrieve(CLOUDFLARED_LINUX_AMD64_URL, str(tmp_path))
        tmp_path.chmod(
            stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        tmp_path.replace(CLOUDFLARED_BIN_PATH)
        logger.info("cloudflared binary installed at %s", CLOUDFLARED_BIN_PATH)
        return CLOUDFLARED_BIN_PATH
    except Exception as exc:
        logger.warning("Could not download cloudflared binary: %s", exc)
        return None


async def _update_telegram_menu_button(bot: Optional[Bot], url: str) -> None:
    if not bot or not url.startswith("https://"):
        return
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="📱 Dashboard",
                web_app=WebAppInfo(url=url),
            )
        )
        logger.info("Updated Telegram chat menu button with WebApp URL: %s", url)
    except Exception as exc:
        logger.warning("Could not set Telegram chat menu button: %s", type(exc).__name__)


async def run_cloudflared_tunnel_loop(
    local_port: int, bot: Optional[Bot] = None
) -> None:
    """
    Maintain a background cloudflared quick tunnel pointing to http://127.0.0.1:{local_port}.
    Automatically captures the generated https://*.trycloudflare.com URL and updates the bot.
    """
    global _active_tunnel_url

    if settings.webapp_url and settings.webapp_url.startswith("https://"):
        await _update_telegram_menu_button(bot, settings.webapp_url.rstrip("/"))
        return

    bin_path = ensure_cloudflared_binary()
    if not bin_path:
        logger.info("cloudflared binary not present; skipping automatic HTTPS tunnel.")
        return

    while True:
        proc: Optional[asyncio.subprocess.Process] = None
        try:
            proc = await asyncio.create_subprocess_exec(
                str(bin_path),
                "tunnel",
                "--no-autoupdate",
                "--url",
                f"http://127.0.0.1:{local_port}",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            assert proc.stderr is not None
            while True:
                line_bytes = await proc.stderr.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="ignore")
                match = _TRYCLOUDFLARE_RE.search(line)
                if match:
                    new_url = match.group(0).rstrip("/")
                    if new_url != _active_tunnel_url:
                        _active_tunnel_url = new_url
                        try:
                            state_file = _url_state_file()
                            state_file.parent.mkdir(parents=True, exist_ok=True)
                            state_file.write_text(new_url + "\n", encoding="utf-8")
                        except Exception:
                            pass
                        logger.info("Telegram Mini App HTTPS Tunnel ready: %s", new_url)
                        await _update_telegram_menu_button(bot, new_url)
            await proc.wait()
        except asyncio.CancelledError:
            if proc and proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except Exception:
                    proc.kill()
            break
        except Exception as exc:
            logger.warning("cloudflared tunnel error: %s", type(exc).__name__)
        await asyncio.sleep(10)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    ensure_cloudflared_binary()
