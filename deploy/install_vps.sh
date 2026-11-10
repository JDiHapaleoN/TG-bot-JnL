#!/usr/bin/env bash
# Safe, isolated installer for JnL-Bot on Ubuntu VPS (HestiaCP / Nginx safe)
# Installs strictly into /opt/jnl-bot, runs 24/7 via systemd, and auto-updates from GitHub every 60s.
set -e

INSTALL_DIR="/opt/jnl-bot"
REPO_URL="https://github.com/JDiHapaleoN/TG-bot-JnL.git"
TOKEN_ARG="${1:-}"

echo "==> [1/5] Checking Python 3 venv and git..."
if ! python3 -m venv --help >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1; then
    apt-get update -y
    apt-get install -y python3-venv python3-pip git
fi

echo "==> [2/5] Cloning / updating repository in $INSTALL_DIR..."
if [ ! -d "$INSTALL_DIR/.git" ]; then
    rm -rf "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
else
    cd "$INSTALL_DIR"
    git fetch origin main
    git reset --hard origin/main
fi

cd "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/deploy/"*.sh

echo "==> [3/5] Creating isolated virtual environment (.venv) and installing packages..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

echo "==> [4/5] Configuring .env..."
if [ -n "$TOKEN_ARG" ]; then
    cat <<EOF > "$INSTALL_DIR/.env"
BOT_TOKEN=$TOKEN_ARG
DATABASE_URL=sqlite+aiosqlite:///./data/finance_bot.db
WEBAPP_HOST=127.0.0.1
WEBAPP_PORT=0
WEBAPP_URL=
EOF
    chmod 600 "$INSTALL_DIR/.env"
    echo "    .env configured with provided BOT_TOKEN."
elif [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"
    echo "    Created template $INSTALL_DIR/.env (remember to set BOT_TOKEN)."
fi

echo "==> [5/5] Enabling 24/7 systemd service + GitHub auto-updater timer..."
cp "$INSTALL_DIR/deploy/jnl-bot.service" /etc/systemd/system/jnl-bot.service
cp "$INSTALL_DIR/deploy/jnl-bot-updater.service" /etc/systemd/system/jnl-bot-updater.service
cp "$INSTALL_DIR/deploy/jnl-bot-updater.timer" /etc/systemd/system/jnl-bot-updater.timer

systemctl daemon-reload
systemctl enable --now jnl-bot.service
systemctl enable --now jnl-bot-updater.timer

echo ""
echo "✅ JnL-Bot is installed, running 24/7, and linked to GitHub for automatic updates!"
systemctl --no-pager status jnl-bot.service || true
