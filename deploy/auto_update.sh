#!/usr/bin/env bash
# Least-Privilege Controlled Updater for JnL-Bot
# Runs as unprivileged user 'jnl-bot' WITHOUT root or sudo.
# Requires administrator to stop jnl-bot.service before execution and start it after verification.
set -euo pipefail

INSTALL_DIR="${JNL_INSTALL_DIR:-/opt/jnl-bot}"
PERSISTENT_ROOT="${JNL_PERSISTENT_ROOT:-/var/lib/jnl-bot}"
PERSISTENT_DATA_DIR="${JNL_DATA_DIR:-$PERSISTENT_ROOT/data}"
BACKUP_DIR="${JNL_BACKUP_DIR:-$PERSISTENT_ROOT/backups}"
DB_FILE="$PERSISTENT_DATA_DIR/finance_bot.db"
VENV_PYTHON="${JNL_VENV_PYTHON:-$INSTALL_DIR/.venv/bin/python}"
VENV_PIP="${JNL_VENV_PIP:-$INSTALL_DIR/.venv/bin/pip}"

verify_canonical_dir() {
    local dir_path="$1"
    if [ -L "$dir_path" ]; then
        echo "[jnl-bot-updater] FATAL: Refusing to operate on symbolic link directory: $dir_path" >&2
        exit 1
    fi
    if command -v mountpoint >/dev/null 2>&1; then
        if mountpoint -q "$dir_path" 2>/dev/null; then
            echo "[jnl-bot-updater] FATAL: Unexpected mountpoint at $dir_path" >&2
            exit 1
        fi
    fi
    if [ ! -d "$dir_path" ]; then
        echo "[jnl-bot-updater] FATAL: Required directory does not exist: $dir_path" >&2
        exit 1
    fi
    local resolved
    resolved=$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$dir_path")
    case "$resolved" in
        /home/*|/var/www/*|/root/*|/usr/local/hestia/*|/etc/*)
            echo "[jnl-bot-updater] FATAL: Directory resolves to prohibited path: $resolved" >&2
            exit 1
            ;;
    esac
}

verify_canonical_dir "$INSTALL_DIR"
verify_canonical_dir "$PERSISTENT_DATA_DIR"
verify_canonical_dir "$BACKUP_DIR"

cd "$INSTALL_DIR" || exit 1

# Step 0: Detect active bot service/process and refuse to run while bot is active
echo "[jnl-bot-updater] Step 0/8: Verifying that JnL-Bot is stopped before update..."
if ! "$VENV_PYTHON" -m bot.database.migrations --check-stopped --db-path "$DB_FILE"; then
    echo "[jnl-bot-updater] ❌ REFUSED: JnL-Bot is currently running (jnl-bot.service or bot.lock is active)." >&2
    echo "[jnl-bot-updater] Please stop jnl-bot.service first (sudo systemctl stop jnl-bot.service) before updating." >&2
    exit 1
fi

git fetch origin main --quiet || {
    echo "[jnl-bot-updater] ERROR: Failed to fetch from origin/main." >&2
    exit 1
}

LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main)

if [ "$LOCAL_HASH" = "$REMOTE_HASH" ]; then
    echo "[jnl-bot-updater] Already up to date at commit $LOCAL_HASH."
    exit 0
fi

echo "[jnl-bot-updater] New version detected ($LOCAL_HASH -> $REMOTE_HASH). Initiating controlled update..."
PREV_HASH="$LOCAL_HASH"
PRE_UPDATE_MANIFEST="$PERSISTENT_DATA_DIR/.pre_update_backup_path"
rm -f "$PRE_UPDATE_MANIFEST"

# Step 1: Mandatory verified pre-update backup
echo "[jnl-bot-updater] Step 1/8: Creating and verifying mandatory pre-update backup..."
if ! "$VENV_PYTHON" -m bot.services.backup \
    --pre-update \
    --source "$DB_FILE" \
    --backup-dir "$BACKUP_DIR" \
    --manifest-out "$PRE_UPDATE_MANIFEST"; then
    echo "[jnl-bot-updater] FATAL: Pre-update backup failed or could not be verified! Update aborted." >&2
    exit 1
fi

PRE_UPDATE_BACKUP_PATH="NONE"
if [ -f "$PRE_UPDATE_MANIFEST" ]; then
    PRE_UPDATE_BACKUP_PATH=$(cat "$PRE_UPDATE_MANIFEST")
fi

DB_MIGRATION_STARTED=0

rollback() {
    local fail_stage="${1:-unknown}"
    echo "[jnl-bot-updater] ⚠️ ERROR at stage '$fail_stage'! Initiating rollback to $PREV_HASH..." >&2
    echo "Update from $PREV_HASH to $REMOTE_HASH failed at stage '$fail_stage' on $(date -u)" > "$PERSISTENT_DATA_DIR/update_failed.flag" 2>/dev/null || true

    cd "$INSTALL_DIR"
    git reset --hard "$PREV_HASH"
    if [ "${JNL_SKIP_PIP_INSTALL:-0}" != "1" ]; then
        "$VENV_PIP" install --quiet -r "$INSTALL_DIR/requirements.txt" || true
    fi

    if [ "$DB_MIGRATION_STARTED" -eq 1 ]; then
        echo "[jnl-bot-updater] Live database migration had started; performing mandatory DATABASE ROLLBACK from $PRE_UPDATE_BACKUP_PATH..." >&2
        if [ "$PRE_UPDATE_BACKUP_PATH" != "NONE" ] && [ -f "$PRE_UPDATE_BACKUP_PATH" ]; then
            if "$VENV_PYTHON" -m bot.services.backup \
                --restore "$PRE_UPDATE_BACKUP_PATH" \
                --target "$DB_FILE" \
                --backup-dir "$BACKUP_DIR" && \
               "$VENV_PYTHON" -m bot.services.backup \
                --verify "$DB_FILE" \
                --compare-backup "$PRE_UPDATE_BACKUP_PATH"; then
                rm -f "$PERSISTENT_DATA_DIR/db_rollback_failed.flag" 2>/dev/null || true
                echo "[jnl-bot-updater] Full rollback complete: Git code reverted to $PREV_HASH AND database restored and verified from pre-update backup." >&2
                exit 1
            else
                echo "Database rollback from $PRE_UPDATE_BACKUP_PATH failed at $(date -u)" > "$PERSISTENT_DATA_DIR/db_rollback_failed.flag"
                echo "[jnl-bot-updater] ❌ CRITICAL: Git code was reverted to $PREV_HASH, but DATABASE ROLLBACK FAILED! Startup is blocked by db_rollback_failed.flag until manual verification." >&2
                exit 2
            fi
        else
            echo "Database rollback failed: missing pre-update backup ($PRE_UPDATE_BACKUP_PATH) at $(date -u)" > "$PERSISTENT_DATA_DIR/db_rollback_failed.flag"
            echo "[jnl-bot-updater] ❌ CRITICAL: Cannot roll back database because pre-update backup path is unavailable!" >&2
            exit 2
        fi
    else
        # Verify untouched database is still intact
        if "$VENV_PYTHON" -m bot.services.backup \
            --verify "$DB_FILE" \
            --compare-backup "$PRE_UPDATE_BACKUP_PATH"; then
            echo "[jnl-bot-updater] Code-only rollback to $PREV_HASH complete (live database was not touched and is verified intact)." >&2
            exit 1
        else
            echo "Database verification failed after code rollback at $(date -u)" > "$PERSISTENT_DATA_DIR/db_rollback_failed.flag"
            echo "[jnl-bot-updater] ❌ CRITICAL: Database verification failed after code rollback!" >&2
            exit 2
        fi
    fi
}

# Step 2: Pre-flight migration test on an ISOLATED COPY before touching code or database
echo "[jnl-bot-updater] Step 2/8: Pre-flight migration validation on isolated database copy..."
"$VENV_PYTHON" -m bot.database.migrations --test-isolated --db-path "$DB_FILE" || {
    echo "[jnl-bot-updater] Pre-flight migration test failed on isolated copy. Aborting update before any changes." >&2
    exit 1
}

# Step 3: Pull updated application code
echo "[jnl-bot-updater] Step 3/8: Pulling code commit $REMOTE_HASH..."
git reset --hard origin/main || rollback "git_reset"
chmod +x "$INSTALL_DIR/deploy/"*.sh 2>/dev/null || true

# Step 4: Update Python virtual environment dependencies
echo "[jnl-bot-updater] Step 4/8: Updating dependencies in isolated .venv..."
if [ "${JNL_SKIP_PIP_INSTALL:-0}" != "1" ]; then
    "$VENV_PIP" install --quiet -r "$INSTALL_DIR/requirements.txt" || rollback "pip_install"
fi

# Step 5: Verify WAL-safe SQLite runtime
echo "[jnl-bot-updater] Step 5/8: Verifying WAL-safe SQLite runtime..."
if [ "${JNL_SKIP_SQLITE_BUILD:-0}" != "1" ]; then
    "$VENV_PYTHON" "$INSTALL_DIR/deploy/install_sqlite_amalgamation.py" || rollback "sqlite_amalgamation"
    "$VENV_PYTHON" -m bot.database.check_sqlite || rollback "check_sqlite"
fi

# Step 6: Test new migrations on isolated copy using newly installed code
echo "[jnl-bot-updater] Step 6/8: Testing new migrations on isolated copy..."
"$VENV_PYTHON" -m bot.database.migrations --test-isolated --db-path "$DB_FILE" || rollback "isolated_migration_v2"

# Step 7: Apply backward-compatible migrations to stopped database
echo "[jnl-bot-updater] Step 7/8: Applying migrations to stopped database..."
DB_MIGRATION_STARTED=1
"$VENV_PYTHON" -m bot.database.migrations --apply --db-path "$DB_FILE" || rollback "live_migration"

# Step 8: Verify final state of the database and run automated test suite
echo "[jnl-bot-updater] Step 8/8: Verifying final database state and executing test suite..."
"$VENV_PYTHON" -m bot.services.backup \
    --verify "$DB_FILE" \
    --compare-backup "$PRE_UPDATE_BACKUP_PATH" || rollback "post_migration_db_verify"

if [ "${JNL_SKIP_UNITTESTS:-0}" != "1" ]; then
    "$VENV_PYTHON" -m unittest discover -s "$INSTALL_DIR/tests" || rollback "unit_tests"
fi

rm -f "$PERSISTENT_DATA_DIR/update_failed.flag" "$PERSISTENT_DATA_DIR/db_rollback_failed.flag" "$PRE_UPDATE_MANIFEST" 2>/dev/null || true
echo "[jnl-bot-updater] ✅ Update to $REMOTE_HASH and final database verification succeeded."
echo "[jnl-bot-updater] Next step: Administrator should now start and verify the service:"
echo "    sudo systemctl start jnl-bot.service && sudo systemctl status jnl-bot.service --no-pager"
