#!/usr/bin/env bash
# Least-Privilege Updater for JnL-Bot
# Operates strictly within /opt/jnl-bot and /var/lib/jnl-bot.
# Uses mandatory pre-update backup, isolated-copy migration pre-flight, and automated rollback.
set -euo pipefail

INSTALL_DIR="/opt/jnl-bot"
PERSISTENT_DATA_DIR="/var/lib/jnl-bot/data"
BACKUP_DIR="/var/lib/jnl-bot/backups"

mkdir -p "$PERSISTENT_DATA_DIR" "$BACKUP_DIR"
chmod 700 "$PERSISTENT_DATA_DIR" "$BACKUP_DIR"

cd "$INSTALL_DIR" || exit 1

# Define scoped service management command (supports unprivileged jnl-bot user via scoped sudoers)
if [ "$(id -u)" -eq 0 ]; then
    SYSTEMCTL_RESTART="systemctl restart jnl-bot.service"
    SYSTEMCTL_IS_ACTIVE="systemctl is-active --quiet jnl-bot.service"
else
    SYSTEMCTL_RESTART="sudo /bin/systemctl restart jnl-bot.service"
    SYSTEMCTL_IS_ACTIVE="sudo /bin/systemctl is-active --quiet jnl-bot.service"
fi

# Step 0: Ensure safe storage separation without risking unmigrated data
if [ -d "$INSTALL_DIR/data" ] && [ ! -L "$INSTALL_DIR/data" ]; then
    if [ -f "$INSTALL_DIR/data/finance_bot.db" ]; then
        echo "[jnl-bot-updater] Found legacy in-repo database. Running verified storage migration..."
        "$INSTALL_DIR/.venv/bin/python" -m bot.services.storage_migration \
            --source "$INSTALL_DIR/data/finance_bot.db" \
            --target "$PERSISTENT_DATA_DIR/finance_bot.db" \
            --backup-dir "$BACKUP_DIR"
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        mv "$INSTALL_DIR/data" "$INSTALL_DIR/data_legacy_archived_${TIMESTAMP}"
    fi
    ln -sfn "$PERSISTENT_DATA_DIR" "$INSTALL_DIR/data"
elif [ ! -e "$INSTALL_DIR/data" ]; then
    ln -sfn "$PERSISTENT_DATA_DIR" "$INSTALL_DIR/data"
fi

git fetch origin main --quiet || exit 0

LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main)

if [ "$LOCAL_HASH" = "$REMOTE_HASH" ]; then
    exit 0
fi

echo "[jnl-bot-updater] New version detected ($LOCAL_HASH -> $REMOTE_HASH). Initiating safe update sequence..."
PREV_HASH="$LOCAL_HASH"

# Step 1: Mandatory verified pre-update backup.
echo "[jnl-bot-updater] Step 1/8: Running mandatory pre-update backup..."
if ! "$INSTALL_DIR/.venv/bin/python" -m bot.services.backup --pre-update; then
    echo "[jnl-bot-updater] FATAL: Pre-update backup failed or could not be verified! Update aborted to protect database."
    exit 1
fi

rollback() {
    echo "[jnl-bot-updater] ⚠️ ERROR occurred during update! Rolling back code to $PREV_HASH..."
    echo "Update from $PREV_HASH to $REMOTE_HASH failed at $(date -u)" > "$PERSISTENT_DATA_DIR/update_failed.flag" 2>/dev/null || true
    cd "$INSTALL_DIR"
    git reset --hard "$PREV_HASH"
    ln -sfn "$PERSISTENT_DATA_DIR" "$INSTALL_DIR/data"
    "$INSTALL_DIR/.venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt" || true
    $SYSTEMCTL_RESTART || true
    echo "[jnl-bot-updater] Rollback complete. Live user database preserved without data loss."
    exit 1
}

# Step 2: Pre-flight migration test on an ISOLATED COPY before touching live code or database
echo "[jnl-bot-updater] Step 2/8: Pre-flight migration validation on isolated database copy..."
"$INSTALL_DIR/.venv/bin/python" -m bot.database.migrations --test-isolated || {
    echo "[jnl-bot-updater] Pre-flight migration test failed on isolated copy. Aborting update."
    exit 1
}

# Step 3: Pull updated application code
echo "[jnl-bot-updater] Step 3/8: Pulling code commit $REMOTE_HASH..."
git reset --hard origin/main || rollback
ln -sfn "$PERSISTENT_DATA_DIR" "$INSTALL_DIR/data"
chmod +x "$INSTALL_DIR/deploy/"*.sh 2>/dev/null || true

# Step 4: Update Python virtual environment dependencies
echo "[jnl-bot-updater] Step 4/8: Updating dependencies in isolated .venv..."
"$INSTALL_DIR/.venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt" || rollback

# Step 5: Verify WAL-safe SQLite runtime
echo "[jnl-bot-updater] Step 5/8: Verifying WAL-safe SQLite runtime..."
"$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/deploy/install_sqlite_amalgamation.py" || rollback
"$INSTALL_DIR/.venv/bin/python" -m bot.database.check_sqlite || rollback

# Step 6: Test new migrations on isolated copy using newly installed code
echo "[jnl-bot-updater] Step 6/8: Testing new migrations on isolated copy..."
"$INSTALL_DIR/.venv/bin/python" -m bot.database.migrations --test-isolated || rollback

# Step 7: Apply backward-compatible migrations to live database
echo "[jnl-bot-updater] Step 7/8: Applying migrations to live database..."
"$INSTALL_DIR/.venv/bin/python" -m bot.database.migrations --apply || rollback

# Step 8: Run automated test suite
echo "[jnl-bot-updater] Step 8/8: Executing test suite..."
"$INSTALL_DIR/.venv/bin/python" -m unittest discover -s "$INSTALL_DIR/tests" || rollback

# Restart service and verify health
echo "[jnl-bot-updater] Restarting jnl-bot.service..."
$SYSTEMCTL_RESTART || rollback
sleep 3

if ! $SYSTEMCTL_IS_ACTIVE; then
    echo "[jnl-bot-updater] Service failed to activate after update. Triggering rollback..."
    rollback
fi

rm -f "$PERSISTENT_DATA_DIR/update_failed.flag" 2>/dev/null || true
echo "[jnl-bot-updater] ✅ Update successful! JnL-Bot updated to $REMOTE_HASH and running normally."
