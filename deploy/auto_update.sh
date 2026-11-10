#!/usr/bin/env bash
# Automatically pulls updates from GitHub (origin/main) and restarts jnl-bot if changed.
# Untracked files (.env and data/finance_bot.db) are preserved safely.
set -e

INSTALL_DIR="/opt/jnl-bot"
cd "$INSTALL_DIR"

git fetch origin main --quiet

LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main)

if [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
    echo "[jnl-bot-updater] New update detected ($LOCAL_HASH -> $REMOTE_HASH). Updating..."
    git reset --hard origin/main
    chmod +x "$INSTALL_DIR/deploy/"*.sh
    "$INSTALL_DIR/.venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"
    systemctl restart jnl-bot.service
    echo "[jnl-bot-updater] Update applied and jnl-bot.service restarted successfully."
fi

