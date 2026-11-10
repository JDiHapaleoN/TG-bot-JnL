#!/usr/bin/env bash
# Least-Privilege Installer for JnL-Bot on Ubuntu VPS (HestiaCP / Client Website Safe)
# Strictly isolates JnL-Bot under dedicated unprivileged system user 'jnl-bot'.
# Never modifies OS packages, never touches website files, never runs services as root.
set -euo pipefail

INSTALL_DIR="/opt/jnl-bot"
PERSISTENT_DATA_DIR="/var/lib/jnl-bot/data"
BACKUP_DIR="/var/lib/jnl-bot/backups"
PROD_ENV_FILE="/var/lib/jnl-bot/.env"
REPO_URL="https://github.com/JDiHapaleoN/TG-bot-JnL.git"
TOKEN_ARG="${1:-}"

BOT_USER="jnl-bot"
BOT_GROUP="jnl-bot"

echo "====================================================================="
echo "JnL-Bot Least-Privilege Production Installer"
echo "====================================================================="

# Step 1: Pre-flight check for system prerequisites (NO AUTOMATIC APT-GET)
echo "==> [1/6] Checking system prerequisites..."
MISSING_DEPS=()
if ! command -v python3 >/dev/null 2>&1; then
    MISSING_DEPS+=("python3")
fi
if ! python3 -c "import venv, ensurepip" >/dev/null 2>&1; then
    MISSING_DEPS+=("python3-venv")
fi
if ! command -v git >/dev/null 2>&1; then
    MISSING_DEPS+=("git")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo "❌ FATAL: Missing required system dependencies: ${MISSING_DEPS[*]}"
    echo "CRITICAL INFRASTRUCTURE SAFETY RULE:"
    echo "To guarantee that the client's production website is never disrupted,"
    echo "this installer will NEVER run 'apt-get' or alter system-wide packages."
    echo "Please ask the server administrator to manually install the missing packages:"
    echo "    sudo apt-get update && sudo apt-get install -y ${MISSING_DEPS[*]}"
    exit 1
fi
echo "    Prerequisites verified (python3, venv, git)."

# Step 2: Ensure dedicated unprivileged system user and group exist
echo "==> [2/6] Verifying dedicated unprivileged system user '$BOT_USER'..."
if ! getent group "$BOT_GROUP" >/dev/null 2>&1; then
    echo "    Creating system group '$BOT_GROUP'..."
    groupadd --system "$BOT_GROUP"
fi

if ! id -u "$BOT_USER" >/dev/null 2>&1; then
    echo "    Creating system user '$BOT_USER' (no interactive login, restricted home)..."
    useradd --system \
        --gid "$BOT_GROUP" \
        --no-create-home \
        --home-dir /var/lib/jnl-bot \
        --shell /usr/sbin/nologin \
        "$BOT_USER"
fi

# Step 3: Create isolated persistent storage directories with strict permissions
echo "==> [3/6] Setting up isolated persistent storage in /var/lib/jnl-bot..."
mkdir -p "$PERSISTENT_DATA_DIR" "$BACKUP_DIR"
chmod 700 "$PERSISTENT_DATA_DIR" "$BACKUP_DIR"
chown -h "$BOT_USER:$BOT_GROUP" "$PERSISTENT_DATA_DIR" "$BACKUP_DIR"

# Step 4: Clone or update repository in /opt/jnl-bot
echo "==> [4/6] Setting up application repository in $INSTALL_DIR..."
if [ ! -d "$INSTALL_DIR/.git" ]; then
    mkdir -p "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
else
    cd "$INSTALL_DIR"
    git fetch origin main
    git reset --hard origin/main
fi

# Safe storage migration if legacy in-repo database exists
if [ -d "$INSTALL_DIR/data" ] && [ ! -L "$INSTALL_DIR/data" ]; then
    if [ -f "$INSTALL_DIR/data/finance_bot.db" ]; then
        echo "    Detected legacy in-repo database. Migrating safely via SQLite Online Backup..."
        python3 -c "
import sqlite3, os
src = '$INSTALL_DIR/data/finance_bot.db'
tgt = '$PERSISTENT_DATA_DIR/finance_bot.db'
if not os.path.exists(tgt) or os.path.getsize(tgt) == 0:
    s = sqlite3.connect(f'file:{src}?mode=ro', uri=True)
    d = sqlite3.connect(tgt)
    with d: s.backup(d)
    d.close(); s.close()
"
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        mv "$INSTALL_DIR/data" "$INSTALL_DIR/data_legacy_archived_${TIMESTAMP}"
    fi
fi

# Link /opt/jnl-bot/data -> /var/lib/jnl-bot/data
ln -sfn "$PERSISTENT_DATA_DIR" "$INSTALL_DIR/data"

# Standardize .env in /var/lib/jnl-bot/.env (single canonical path)
if [ -n "$TOKEN_ARG" ]; then
    cat <<EOF > "$PROD_ENV_FILE"
APP_ENV=production
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
S3_PBKDF2_ITERATIONS=600000
ADMIN_TELEGRAM_ID=
EOF
elif [ ! -f "$PROD_ENV_FILE" ]; then
    cp "$INSTALL_DIR/.env.example" "$PROD_ENV_FILE"
fi

chmod 600 "$PROD_ENV_FILE"
chown -h "$BOT_USER:$BOT_GROUP" "$PROD_ENV_FILE"
ln -sfn "$PROD_ENV_FILE" "$INSTALL_DIR/.env"

# Step 5: Isolated Python virtual environment (.venv)
echo "==> [5/6] Creating isolated virtual environment (.venv) and installing dependencies..."
if [ ! -d "$INSTALL_DIR/.venv" ]; then
    python3 -m venv "$INSTALL_DIR/.venv"
fi
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q

# Compile WAL-safe SQLite runtime (>= 3.51.3) statically inside .venv if needed
echo "    Verifying WAL-safe SQLite runtime in virtual environment..."
"$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/deploy/install_sqlite_amalgamation.py"

# Enforce fail-closed SQLite diagnostics
echo "    Executing mandatory SQLite WAL diagnostic verification..."
"$INSTALL_DIR/.venv/bin/python" -m bot.database.check_sqlite

# Set strict ownership (safe against symlink attacks)
find "$INSTALL_DIR" -not -type l -exec chown "$BOT_USER:$BOT_GROUP" {} +
find "$PERSISTENT_DATA_DIR" -not -type l -exec chown "$BOT_USER:$BOT_GROUP" {} +
find "$BACKUP_DIR" -not -type l -exec chown "$BOT_USER:$BOT_GROUP" {} +
chmod +x "$INSTALL_DIR/deploy/"*.sh

# Step 6: Systemd sandboxed service installation
echo "==> [6/6] Installing sandboxed systemd service and sudoers policy..."
cp "$INSTALL_DIR/deploy/jnl-bot.service" /etc/systemd/system/jnl-bot.service

if [ -f "$INSTALL_DIR/deploy/jnl-bot.sudoers" ]; then
    cp "$INSTALL_DIR/deploy/jnl-bot.sudoers" /etc/sudoers.d/jnl-bot
    chmod 440 /etc/sudoers.d/jnl-bot
fi

systemctl daemon-reload
systemctl enable jnl-bot.service
systemctl restart jnl-bot.service

# Note: Automated background update timer is deliberately DISABLED by default to protect the client's website.
echo ""
echo "====================================================================="
echo "✅ JnL-Bot installed and running under unprivileged user '$BOT_USER'!"
echo "   Database: $PERSISTENT_DATA_DIR/finance_bot.db"
echo "   Backups:  $BACKUP_DIR"
echo "   Config:   $PROD_ENV_FILE"
echo "   Website safety: Port 0 (long polling only), system packages untouched."
echo "====================================================================="
systemctl --no-pager status jnl-bot.service || true
