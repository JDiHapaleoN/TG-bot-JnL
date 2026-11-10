#!/usr/bin/env bash
# Safe, atomic GitHub auto-updater with mandatory pre-update backup,
# isolated-copy migration pre-flight, and backward-compatible rollback.
set -euo pipefail

INSTALL_DIR="/opt/jnl-bot"
PERSISTENT_DATA_DIR="/var/lib/jnl-bot/data"
BACKUP_DIR="/var/lib/jnl-bot/backups"

mkdir -p "$PERSISTENT_DATA_DIR" "$BACKUP_DIR"
chmod 700 "$PERSISTENT_DATA_DIR" "$BACKUP_DIR"

cd "$INSTALL_DIR" || exit 1

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
# If backup fails or verification fails, the update MUST be completely aborted.
echo "[jnl-bot-updater] Step 1/7: Running mandatory pre-update backup..."
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
    systemctl restart jnl-bot.service || true
    echo "[jnl-bot-updater] Rollback complete. Live user database preserved without data loss."
    exit 1
}

# Step 2: Pre-flight migration test on an ISOLATED COPY before touching live code or database
echo "[jnl-bot-updater] Step 2/7: Pre-flight migration validation on isolated database copy..."
"$INSTALL_DIR/.venv/bin/python" -m bot.database.migrations --test-isolated || {
    echo "[jnl-bot-updater] Pre-flight migration test failed on isolated copy. Aborting update."
    exit 1
}

# Step 3: Pull updated application code
echo "[jnl-bot-updater] Step 3/7: Pulling code commit $REMOTE_HASH..."
git reset --hard origin/main || rollback
ln -sfn "$PERSISTENT_DATA_DIR" "$INSTALL_DIR/data"
chmod +x "$INSTALL_DIR/deploy/"*.sh 2>/dev/null || true

# Step 4: Update Python virtual environment dependencies
echo "[jnl-bot-updater] Step 4/7: Updating dependencies..."
"$INSTALL_DIR/.venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt" || rollback

# Step 5: Test new migrations on isolated copy using newly installed code
echo "[jnl-bot-updater] Step 5/7: Testing new migrations on isolated copy..."
"$INSTALL_DIR/.venv/bin/python" -m bot.database.migrations --test-isolated || rollback

# Step 6: Apply backward-compatible migrations to live database
echo "[jnl-bot-updater] Step 6/7: Applying migrations to live database..."
"$INSTALL_DIR/.venv/bin/python" -m bot.database.migrations --apply || rollback

# Step 7: Run automated test suite
echo "[jnl-bot-updater] Step 7/7: Executing test suite..."
"$INSTALL_DIR/.venv/bin/python" -m unittest discover -s "$INSTALL_DIR/tests" || rollback

# Step 8: Restart service and verify health
systemctl restart jnl-bot.service || rollback
sleep 3

if ! systemctl is-active --quiet jnl-bot.service; then
    echo "[jnl-bot-updater] Service failed to activate after update. Triggering rollback..."
    rollback
fi

rm -f "$PERSISTENT_DATA_DIR/update_failed.flag" 2>/dev/null || true
echo "[jnl-bot-updater] ✅ Update successful! JnL-Bot updated to $REMOTE_HASH and running normally."
