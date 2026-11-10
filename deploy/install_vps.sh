#!/usr/bin/env bash
# Safe, isolated installer for JnL-Bot on Ubuntu VPS (does NOT touch existing websites/Nginx/DBs)
set -e

INSTALL_DIR="/opt/jnl-bot"
REPO_URL="https://github.com/JDiHapaleoN/TG-bot-JnL.git"

echo "==> Checking Python 3 venv support..."
if ! python3 -m venv --help >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y python3-venv python3-pip git
fi

if [ ! -d "$INSTALL_DIR" ]; then
    echo "==> Cloning repository into $INSTALL_DIR..."
    sudo git clone "$REPO_URL" "$INSTALL_DIR"
    sudo chown -R "$USER:$USER" "$INSTALL_DIR"
else
    echo "==> Updating existing repository in $INSTALL_DIR..."
    cd "$INSTALL_DIR"
    git pull origin main
fi

cd "$INSTALL_DIR"

echo "==> Setting up isolated Python virtual environment (.venv)..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    echo "==> Created $INSTALL_DIR/.env from template."
fi

echo "==> Installing systemd service (jnl-bot.service) for 24/7 operation..."
sudo cp "$INSTALL_DIR/deploy/jnl-bot.service" /etc/systemd/system/jnl-bot.service
sudo systemctl daemon-reload
sudo systemctl enable jnl-bot.service

echo ""
echo "✅ Installation complete!"
echo "1. Put your BOT_TOKEN in: nano /opt/jnl-bot/.env"
echo "2. Start the bot 24/7:    sudo systemctl restart jnl-bot"
echo "3. Check status/logs:     sudo systemctl status jnl-bot"
