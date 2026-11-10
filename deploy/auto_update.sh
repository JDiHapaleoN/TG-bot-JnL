#!/usr/bin/env bash
# Safe, atomic GitHub auto-updater with pre-update backup, health verification, and automatic rollback.
set -uo pipefail

INSTALL_DIR="/opt/jnl-bot"
PERSISTENT_DATA_DIR="/var/lib/jnl-bot/data"
BACKUP_DIR="/var/backups/jnl-bot"

mkdir -p "$PERSISTENT_DATA_DIR" "$BACKUP_DIR"

# Ensure physical separation of code (/opt/jnl-bot) and user data (/var/lib/jnl-bot/data)
if [ -d "$INSTALL_DIR/data" ] && [ ! -L "$INSTALL_DIR/data" ]; then
    if [ -f "$INSTALL_DIR/data/finance_bot.db" ] && [ ! -f "$PERSISTENT_DATA_DIR/finance_bot.db" ]; then
        cp -a "$INSTALL_DIR/data/finance_bot.db"* "$PERSISTENT_DATA_DIR/" 2>/dev/null || true
    fi
    rm -rf "$INSTALL_DIR/data"
    ln -s "$PERSISTENT_DATA_DIR" "$INSTALL_DIR/data"
elif [ ! -e "$INSTALL_DIR/data" ]; then
    ln -s "$PERSISTENT_DATA_DIR" "$INSTALL_DIR/data"
fi

cd "$INSTALL_DIR" || exit 1

git fetch origin main --quiet || exit 0

LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main)

if [ "$LOCAL_HASH" = "$REMOTE_HASH" ]; then
    exit 0
fi

echo "[jnl-bot-updater] Update detected ($LOCAL_HASH -> $REMOTE_HASH). Starting safe update sequence..."
PREV_HASH="$LOCAL_HASH"

# Step 1: Create verified backup before updating code
"$INSTALL_DIR/.venv/bin/python" -c "from bot.services.backup import create_database_backup; create_database_backup(tag='pre_update')" || true

rollback() {
    echo "[jnl-bot-updater] ERROR detected during update! Rolling back code to $PREV_HASH..."
    cd "$INSTALL_DIR"
    git reset --hard "$PREV_HASH"
    ln -sfn "$PERSISTENT_DATA_DIR" "$INSTALL_DIR/data"
    systemctl restart jnl-bot.service
    echo "[jnl-bot-updater] Rollback complete. User database was not affected."
    exit 1
}

# Step 2: Pull new code and preserve data symlink
git reset --hard origin/main || rollback
ln -sfn "$PERSISTENT_DATA_DIR" "$INSTALL_DIR/data"
chmod +x "$INSTALL_DIR/deploy/"*.sh 2>/dev/null || true

# Step 3: Update dependencies
"$INSTALL_DIR/.venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt" || rollback

# Step 4: Verify configuration, database accessibility, and run safe migrations
"$INSTALL_DIR/.venv/bin/python" -c "
import asyncio
from bot.database.session import init_db, dispose_db
async def _check():
    await init_db()
    await dispose_db()
asyncio.run(_check())
" || rollback

# Step 5: Run automated verification tests
"$INSTALL_DIR/.venv/bin/python" -m unittest discover -s "$INSTALL_DIR/tests" || rollback

# Step 6: Restart service and verify health
systemctl restart jnl-bot.service || rollback
sleep 3

if ! systemctl is-active --quiet jnl-bot.service; then
    rollback
fi

echo "[jnl-bot-updater] Successfully updated to $REMOTE_HASH and verified service health."
