#!/bin/bash
set -e

echo "=================================="
echo "   FB Auto Poster - WSL Setup"
echo "=================================="

# 1. Update and Install System Dependencies
echo "[1/5] Checking System Dependencies..."
sudo apt-get update
# Ensure Python and venv are installed. Node is optional but checked as requested.
sudo apt-get install -y python3 python3-pip python3-venv

if ! command -v node &> /dev/null; then
    echo "⚠️  Node.js not found (Optional, skipping)."
else
    echo "✅ Node.js detected."
fi

# 2. Create Virtual Environment
echo "[2/5] Setting up Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 'venv' created."
else
    echo "✅ 'venv' already exists."
fi

# 3. Install Python Libraries
echo "[3/5] Installing Python Dependencies..."
source venv/bin/activate
pip install --upgrade pip > /dev/null
pip install -r requirements.txt

# 4. Configure Environment Variables
echo "[4/5] Checking Configuration..."
if [ ! -f ".env" ]; then
    echo "FACEBOOK_ACCESS_TOKEN=REPLACE_ME" > .env
    echo "⚠️  Created .env file. Please edit it with your Access Token."
else
    echo "✅ .env file found."
fi

# 5. Permissions
echo "[5/5] Finalizing..."
chmod +x run.sh

echo ""
echo "🎉 Setup Complete!"
echo "👉 Next Step: Run 'nano .env' to paste your Facebook Token."
