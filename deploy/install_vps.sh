#!/usr/bin/env bash
# Least-Privilege Hardened Installer for JnL-Bot on Ubuntu VPS (HestiaCP / Client Website Safe)
# Strictly isolates JnL-Bot under dedicated unprivileged system user 'jnl-bot'.
# Never modifies OS packages, never touches website files, never runs services as root.
set -euo pipefail

# Security check: Reject passing BOT_TOKEN or secrets as command-line arguments (exposes token in ps aux)
if [ "$#" -gt 0 ]; then
    echo "❌ FATAL SECURITY ERROR: Do not pass BOT_TOKEN or arguments on the command line." >&2
    echo "   Command-line arguments are visible to all processes via 'ps aux' and '/proc'." >&2
    echo "   Run this script without arguments; it will preserve /var/lib/jnl-bot/.env" >&2
    echo "   or prompt you securely with hidden input." >&2
    exit 1
fi

INSTALL_DIR="/opt/jnl-bot"
PERSISTENT_ROOT="/var/lib/jnl-bot"
PERSISTENT_DATA_DIR="/var/lib/jnl-bot/data"
BACKUP_DIR="/var/lib/jnl-bot/backups"
PROD_ENV_FILE="/var/lib/jnl-bot/.env"
REPO_URL="https://github.com/JDiHapaleoN/TG-bot-JnL.git"

BOT_USER="jnl-bot"
BOT_GROUP="jnl-bot"

echo "====================================================================="
echo "JnL-Bot Least-Privilege Hardened Production Installer"
echo "====================================================================="

# Helper: Verify canonical path, reject symlinks, reject unexpected mountpoints, and forbid website paths
verify_canonical_dir() {
    local target_dir="$1"
    local expected_realpath="$2"

    if [ -L "$target_dir" ]; then
        echo "❌ FATAL: Target directory '$target_dir' is a symbolic link! Aborting." >&2
        exit 1
    fi

    if command -v mountpoint >/dev/null 2>&1; then
        if mountpoint -q "$target_dir" 2>/dev/null; then
            echo "❌ FATAL: Target directory '$target_dir' is an unexpected mountpoint! Aborting." >&2
            exit 1
        fi
    fi

    local resolved
    resolved=$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$target_dir")
    if [ "$resolved" != "$expected_realpath" ]; then
        echo "❌ FATAL: Canonical path mismatch for '$target_dir': resolved to '$resolved', expected '$expected_realpath'." >&2
        exit 1
    fi

    case "$resolved" in
        /home/*|/var/www/*|/root/*|/usr/local/hestia/*|/etc/*)
            echo "❌ FATAL: Path '$resolved' points into a prohibited directory! Aborting." >&2
            exit 1
            ;;
    esac
}

verify_no_external_symlinks() {
    local scan_dir="$1"
    local allow_venv_python="$2"

    while IFS= read -r -d '' link_path; do
        local target_real
        target_real=$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$link_path")
        if [ "$allow_venv_python" = "true" ]; then
            case "$target_real" in
                /opt/jnl-bot/*|/usr/bin/python*|/usr/lib/*|/lib/*)
                    continue
                    ;;
            esac
        fi
        echo "❌ FATAL: Unexpected symbolic link detected inside '$scan_dir': '$link_path' -> '$target_real'" >&2
        exit 1
    done < <(find -P "$scan_dir" -xdev -type l -print0)
}

# Step 1: Pre-flight check for system prerequisites (NO AUTOMATIC APT-GET)
echo "==> [1/7] Checking system prerequisites..."
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
    echo "❌ FATAL: Missing required system dependencies: ${MISSING_DEPS[*]}" >&2
    echo "CRITICAL INFRASTRUCTURE SAFETY RULE:" >&2
    echo "To guarantee that the client's production website is never disrupted," >&2
    echo "this installer will NEVER run 'apt-get' or alter system-wide packages." >&2
    echo "Please ask the server administrator to manually install the missing packages:" >&2
    echo "    sudo apt-get update && sudo apt-get install -y ${MISSING_DEPS[*]}" >&2
    exit 1
fi
echo "    Prerequisites verified (python3, venv, git)."

# Verify parent OS directories are not symlinks
for parent_dir in /opt /var /var/lib; do
    if [ -L "$parent_dir" ]; then
        echo "❌ FATAL: System parent directory '$parent_dir' is a symbolic link! Aborting." >&2
        exit 1
    fi
done

# Step 2: Ensure dedicated unprivileged system user and group exist
echo "==> [2/7] Verifying dedicated unprivileged system user '$BOT_USER'..."
if ! getent group "$BOT_GROUP" >/dev/null 2>&1; then
    echo "    Creating system group '$BOT_GROUP'..."
    groupadd --system "$BOT_GROUP"
fi

if ! id -u "$BOT_USER" >/dev/null 2>&1; then
    echo "    Creating system user '$BOT_USER' (no interactive login, restricted home)..."
    useradd --system \
        --gid "$BOT_GROUP" \
        --no-create-home \
        --home-dir "$PERSISTENT_ROOT" \
        --shell /usr/sbin/nologin \
        "$BOT_USER"
fi

# Step 3: Create and verify isolated persistent storage directories
echo "==> [3/7] Verifying isolated persistent storage in $PERSISTENT_ROOT..."
mkdir -p "$PERSISTENT_ROOT" "$PERSISTENT_DATA_DIR" "$BACKUP_DIR"
verify_canonical_dir "$PERSISTENT_ROOT" "/var/lib/jnl-bot"
verify_canonical_dir "$PERSISTENT_DATA_DIR" "/var/lib/jnl-bot/data"
verify_canonical_dir "$BACKUP_DIR" "/var/lib/jnl-bot/backups"
chmod 750 "$PERSISTENT_ROOT"
chmod 700 "$PERSISTENT_DATA_DIR" "$BACKUP_DIR"

# Stop jnl-bot.service before any backup, migration, or code update
if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet jnl-bot.service 2>/dev/null; then
    echo "    Stopping active jnl-bot.service before backup and update..."
    systemctl stop jnl-bot.service
fi

# Step 4: Backup existing data BEFORE any git reset, migration, or directory modification
echo "==> [4/7] Backing up existing database state before touching repository..."
verify_and_backup_sqlite() {
    local src_db="$1"
    local label="$2"
    local ts
    ts=$(date -u +%Y%m%d_%H%M%S)
    local bkp_file="$BACKUP_DIR/finance_bot_${label}_${ts}.db"

    python3 - "$src_db" "$bkp_file" <<'PYEOF'
import hashlib, sqlite3, sys
src_path, bkp_path = sys.argv[1], sys.argv[2]
src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True, timeout=15)
dst = sqlite3.connect(bkp_path, timeout=15)
try:
    with dst:
        src.backup(dst)
finally:
    dst.close()
    src.close()

chk = sqlite3.connect(f"file:{bkp_path}?mode=ro", uri=True, timeout=15)
try:
    row = chk.execute("PRAGMA integrity_check").fetchone()
    if not row or row[0] != "ok":
        raise RuntimeError(f"Integrity check failed on backup {bkp_path}: {row}")
finally:
    chk.close()

h = hashlib.sha256()
with open(bkp_path, "rb") as f:
    for chunk in iter(lambda: f.read(65536), b""):
        h.update(chunk)
with open(bkp_path + ".sha256", "w", encoding="utf-8") as sf:
    sf.write(f"{h.hexdigest()}  {bkp_path}\n")
print(f"    Verified backup created: {bkp_path}")
PYEOF
}

if [ -f "$PERSISTENT_DATA_DIR/finance_bot.db" ] && [ -s "$PERSISTENT_DATA_DIR/finance_bot.db" ]; then
    echo "    Creating verified backup of existing production database..."
    verify_and_backup_sqlite "$PERSISTENT_DATA_DIR/finance_bot.db" "pre_install"
fi

# Safely migrate legacy in-repo database if present BEFORE git reset --hard
if [ -L "$INSTALL_DIR/data" ]; then
    rm -f "$INSTALL_DIR/data"
elif [ -d "$INSTALL_DIR/data" ]; then
    if [ -f "$INSTALL_DIR/data/finance_bot.db" ] && [ -s "$INSTALL_DIR/data/finance_bot.db" ]; then
        echo "    Detected legacy in-repo database. Backing up before migration..."
        verify_and_backup_sqlite "$INSTALL_DIR/data/finance_bot.db" "legacy_inrepo"
        if [ ! -f "$PERSISTENT_DATA_DIR/finance_bot.db" ] || [ ! -s "$PERSISTENT_DATA_DIR/finance_bot.db" ]; then
            echo "    Migrating legacy database to $PERSISTENT_DATA_DIR/finance_bot.db..."
            python3 - "$INSTALL_DIR/data/finance_bot.db" "$PERSISTENT_DATA_DIR/finance_bot.db" <<'PYEOF'
import sqlite3, sys
src_path, tgt_path = sys.argv[1], sys.argv[2]
src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True, timeout=15)
dst = sqlite3.connect(tgt_path, timeout=15)
try:
    with dst:
        src.backup(dst)
finally:
    dst.close()
    src.close()
chk = sqlite3.connect(f"file:{tgt_path}?mode=ro", uri=True, timeout=15)
try:
    res = chk.execute("PRAGMA integrity_check").fetchone()
    if not res or res[0] != "ok":
        raise RuntimeError(f"Migrated DB failed integrity_check: {res}")
finally:
    chk.close()
PYEOF
        fi
    fi
    TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
    mv "$INSTALL_DIR/data" "$PERSISTENT_ROOT/data_legacy_archived_${TIMESTAMP}"
fi

# Migrate legacy in-repo .env if /var/lib/jnl-bot/.env does not exist yet, and remove any in-repo .env symlink
if [ -L "$INSTALL_DIR/.env" ]; then
    rm -f "$INSTALL_DIR/.env"
elif [ -f "$INSTALL_DIR/.env" ]; then
    if [ ! -f "$PROD_ENV_FILE" ]; then
        cp -a "$INSTALL_DIR/.env" "$PROD_ENV_FILE"
    fi
    rm -f "$INSTALL_DIR/.env"
fi

# Step 5: Clone or update repository in /opt/jnl-bot
echo "==> [5/7] Setting up application repository in $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
verify_canonical_dir "$INSTALL_DIR" "/opt/jnl-bot"

if [ ! -d "$INSTALL_DIR/.git" ]; then
    git clone "$REPO_URL" "$INSTALL_DIR"
else
    cd "$INSTALL_DIR"
    git fetch origin main
    git reset --hard origin/main
fi

# Ensure canonical production configuration at /var/lib/jnl-bot/.env (never overwrite existing)
if [ ! -f "$PROD_ENV_FILE" ]; then
    INPUT_TOKEN=""
    if [ -t 0 ]; then
        read -r -s -p "    Enter Telegram BOT_TOKEN (input hidden, or press Enter to edit $PROD_ENV_FILE later): " INPUT_TOKEN
        echo ""
    fi
    cat <<EOF > "$PROD_ENV_FILE"
APP_ENV=production
BOT_TOKEN=${INPUT_TOKEN}
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
fi

if [ -L "$PROD_ENV_FILE" ]; then
    echo "❌ FATAL: $PROD_ENV_FILE must be a regular file, not a symlink!" >&2
    exit 1
fi
chmod 600 "$PROD_ENV_FILE"
chown -h "$BOT_USER:$BOT_GROUP" "$PROD_ENV_FILE"

# Step 6: Isolated Python virtual environment (.venv) and fail-closed SQLite verification
echo "==> [6/7] Configuring isolated virtual environment (.venv) and verifying SQLite..."
if [ ! -d "$INSTALL_DIR/.venv" ]; then
    python3 -m venv "$INSTALL_DIR/.venv"
fi
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q

echo "    Verifying WAL-safe SQLite runtime (>= 3.51.3) in virtual environment..."
"$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/deploy/install_sqlite_amalgamation.py"

echo "    Executing mandatory fail-closed SQLite WAL diagnostic verification..."
"$INSTALL_DIR/.venv/bin/python" -m bot.database.check_sqlite

chmod +x "$INSTALL_DIR/deploy/"*.sh

# Verify canonical directories and symlink safety BEFORE recursive ownership changes
verify_canonical_dir "$INSTALL_DIR" "/opt/jnl-bot"
verify_canonical_dir "$PERSISTENT_ROOT" "/var/lib/jnl-bot"
verify_canonical_dir "$PERSISTENT_DATA_DIR" "/var/lib/jnl-bot/data"
verify_canonical_dir "$BACKUP_DIR" "/var/lib/jnl-bot/backups"

verify_no_external_symlinks "$INSTALL_DIR" "true"
verify_no_external_symlinks "$PERSISTENT_ROOT" "false"

# Confined, single-filesystem (-xdev), non-dereferencing (-P / -h) ownership assignment
find -P "$INSTALL_DIR" -xdev -not -type l -exec chown -h "$BOT_USER:$BOT_GROUP" {} +
find -P "$PERSISTENT_ROOT" -xdev -not -type l -exec chown -h "$BOT_USER:$BOT_GROUP" {} +

# Step 7: Install and verify systemd units (no sudoers privileges granted)
echo "==> [7/7] Installing and verifying sandboxed systemd unit files..."
rm -f /etc/sudoers.d/jnl-bot

cp "$INSTALL_DIR/deploy/jnl-bot.service" /etc/systemd/system/jnl-bot.service
cp "$INSTALL_DIR/deploy/jnl-bot-updater.service" /etc/systemd/system/jnl-bot-updater.service
cp "$INSTALL_DIR/deploy/jnl-bot-updater.timer" /etc/systemd/system/jnl-bot-updater.timer

systemctl daemon-reload

# Ensure automatic background updater timer is disabled by default
systemctl disable --now jnl-bot-updater.timer 2>/dev/null || true

if command -v systemd-analyze >/dev/null 2>&1; then
    echo "    Validating systemd unit files with systemd-analyze verify..."
    systemd-analyze verify /etc/systemd/system/jnl-bot.service /etc/systemd/system/jnl-bot-updater.service
fi

systemctl enable jnl-bot.service
systemctl start jnl-bot.service

echo ""
echo "====================================================================="
echo "✅ JnL-Bot installed and running under unprivileged user '$BOT_USER'!"
echo "   Entrypoint: /opt/jnl-bot/main.py"
echo "   Database:   $PERSISTENT_DATA_DIR/finance_bot.db"
echo "   Backups:    $BACKUP_DIR"
echo "   Config:     $PROD_ENV_FILE"
echo "   Auto-timer: DISABLED by default (use controlled update workflow)"
echo "====================================================================="
systemctl --no-pager status jnl-bot.service || true
