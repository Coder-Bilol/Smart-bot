#!/bin/bash
set -e

# Configuration
APP_DIR="/home/bilol/smart-bot"
PYTHON_BIN="python3.11" # AlmaLinux 9 usually has 3.9, we might need 3.11. Adjust if needed.

echo ">>> Starting Deployment..."

# 1. Install Dependencies
echo ">>> Installing System Packages..."
# Check if python3.11 is available, if not try to install or fallback
if ! command -v $PYTHON_BIN &> /dev/null; then
    echo "Python 3.11 not found, attempting install..."
    sudo dnf install -y python3.11 python3.11-pip git
fi

# 2. Setup Directory
echo ">>> Setting up directory $APP_DIR..."
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# 3. Setup Virtual Environment
echo ">>> Setting up Virtual Environment..."
if [ ! -d "venv" ]; then
    $PYTHON_BIN -m venv venv
fi
source venv/bin/activate

# 4. Install Python Dependencies
echo ">>> Installing Python Requirements..."
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# 5. Create Systemd Service
echo ">>> Configuring Systemd Service..."
SERVICE_PATH="/etc/systemd/system/smartbot.service"

sudo bash -c "cat > $SERVICE_PATH" <<EOF
[Unit]
Description=Smart Bot Telegram Service
After=network.target

[Service]
User=bilol
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/src/main.py
EnvironmentFile=$APP_DIR/.env
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 6. Start Service
echo ">>> Reloading and Starting Service..."
sudo systemctl daemon-reload
sudo systemctl enable smartbot
sudo systemctl restart smartbot

echo ">>> Deployment Complete!"
sudo systemctl status smartbot --no-pager
