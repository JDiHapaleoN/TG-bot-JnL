#!/usr/bin/env bash
# Safe, isolated installer for JnL-Bot on Ubuntu VPS (HestiaCP / Nginx safe)
# Physically separates code (/opt/jnl-bot), database (/var/lib/jnl-bot/data), and backups (/var/backups/jnl-bot).
set -euo pipefail

INSTALL_DIR="/opt/jnl-bot"
PERSISTENT_DATA_DIR="/var/lib/jnl-bot/data"
BACKUP_DIR="/var/backups/jnl-bot"
REPO_URL="https://github.com/JDiHapaleoN/TG-bot-JnL.git"
TOKEN_ARG="${1:-}"

mkdir -p "$PERSISTENT_DATA_DIR" "$BACKUP_DIR"
chmod 700 "$PERSISTENT_DATA_DIR" "$BACKUP_DIR"

echo "==> [1/5] Checking python3-venv (ensurepip) and git..."
if ! python3 -c "import ensurepip" >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y python3-venv python3-pip git
fi

# Step 1.1: If an unmigrated database exists in /opt/jnl-bot/data, safely migrate it using SQLite online backup
if [ -d "$INSTALL_DIR/data" ] && [ ! -L "$INSTALL_DIR/data" ]; then
    if [ -f "$INSTALL_DIR/data/finance_bot.db" ]; then
        echo "==> Detected legacy in-repo database. Running verified storage migration..."
        if [ -x "$INSTALL_DIR/.venv/bin/python" ]; then
            "$INSTALL_DIR/.venv/bin/python" -m bot.services.storage_migration \
                --source "$INSTALL_DIR/data/finance_bot.db" \
                --target "$PERSISTENT_DATA_DIR/finance_bot.db" \
                --backup-dir "$BACKUP_DIR"
        else
            python3 -c "
import sqlite3, shutil, os
src = '$INSTALL_DIR/data/finance_bot.db'
tgt = '$PERSISTENT_DATA_DIR/finance_bot.db'
if not os.path.exists(tgt) or os.path.getsize(tgt) == 0:
    s = sqlite3.connect(f'file:{src}?mode=ro', uri=True)
    d = sqlite3.connect(tgt)
    with d: s.backup(d)
    d.close(); s.close()
"
        fi
        # Archive old directory, never delete it
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        mv "$INSTALL_DIR/data" "$INSTALL_DIR/data_legacy_archived_${TIMESTAMP}"
    fi
fi

# Preserve existing .env if present
TMP_ENV=""
if [ -f "$INSTALL_DIR/.env" ]; then
    TMP_ENV=$(mktemp)
    cp -a "$INSTALL_DIR/.env" "$TMP_ENV"
fi

echo "==> [2/5] Cloning / updating repository in $INSTALL_DIR..."
if [ ! -d "$INSTALL_DIR/.git" ]; then
    mkdir -p "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
else
    cd "$INSTALL_DIR"
    git fetch origin main
    git reset --hard origin/main
fi

if [ -n "$TMP_ENV" ] && [ -f "$TMP_ENV" ]; then
    cp -a "$TMP_ENV" "$INSTALL_DIR/.env"
    rm -f "$TMP_ENV"
fi

# Link /opt/jnl-bot/data -> /var/lib/jnl-bot/data so data is permanently external to git
ln -sfn "$PERSISTENT_DATA_DIR" "$INSTALL_DIR/data"

cd "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/deploy/"*.sh

echo "==> [3/5] Creating isolated virtual environment (.venv) and installing packages..."
if [ ! -d "$INSTALL_DIR/.venv" ]; then
    python3 -m venv "$INSTALL_DIR/.venv"
fi
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q

echo "==> [4/5] Configuring .env..."
if [ -n "$TOKEN_ARG" ]; then
    cat <<EOF > "$INSTALL_DIR/.env"
BOT_TOKEN=$TOKEN_ARG
DATABASE_URL=sqlite+aiosqlite:///$PERSISTENT_DATA_DIR/finance_bot.db
BACKUP_DIR=$BACKUP_DIR
WEBAPP_HOST=127.0.0.1
WEBAPP_PORT=0
WEBAPP_URL=
S3_BACKUP_ENABLED=false
S3_ENDPOINT_URL=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_BUCKET_NAME=
S3_REGION_NAME=us-east-1
S3_ENCRYPTION_KEY=
S3_RETENTION_DAYS=30
EOF
    chmod 600 "$INSTALL_DIR/.env"
    echo "    .env configured with provided BOT_TOKEN and persistent storage paths."
elif [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"
    echo "    Created template $INSTALL_DIR/.env (remember to set BOT_TOKEN)."
fi

# Run pre-flight SQLite diagnostic check
echo "==> Checking SQLite runtime version and WAL mode..."
"$INSTALL_DIR/.venv/bin/python" -m bot.database.check_sqlite || true

echo "==> [5/5] Enabling 24/7 systemd service + GitHub auto-updater timer..."
cp "$INSTALL_DIR/deploy/jnl-bot.service" /etc/systemd/system/jnl-bot.service
cp "$INSTALL_DIR/deploy/jnl-bot-updater.service" /etc/systemd/system/jnl-bot-updater.service
cp "$INSTALL_DIR/deploy/jnl-bot-updater.timer" /etc/systemd/system/jnl-bot-updater.timer

systemctl daemon-reload
systemctl enable --now jnl-bot.service
systemctl restart jnl-bot.service
systemctl enable --now jnl-bot-updater.timer

echo ""
echo "✅ JnL-Bot is installed, running 24/7, and linked to GitHub for automatic updates!"
systemctl --no-pager status jnl-bot.service || true
