#!/bin/bash
set -e

echo "=================================="
jh="   FB Auto Poster - WSL Setup"
echo "=================================="

# 1. Check and Install System Dependencies (WSL/Ubuntu)
echo "🔍 Checking system requirements..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Installing..."
    sudo apt-get update && sudo apt-get install -y python3
fi

if ! command -v pip3 &> /dev/null; then
    echo "📦 Installing pip..."
    sudo apt-get install -y python3-pip
fi

# Check for venv module specifically (often missing in minimal Ubuntu)
if ! dpkg -s python3-venv &> /dev/null; then
    echo "📦 Installing python3-venv..."
    sudo apt-get install -y python3-venv
fi

# Check Node.js (Optional check as requested)
if ! command -v node &> /dev/null; then
    echo "⚠️  Node.js not found (Optional, skipping as we use Python Dashboard)."
else
    echo "✅ Node.js detected."
fi

# 2. Create Virtual Environment
if [ ! -d "venv" ]; then
    echo "🔨 Creating Virtual Environment (venv)..."
    python3 -m venv venv
else
    echo "✅ Venv already exists."
fi

# 3. Install Python Dependencies
echo "⬇️  Installing Python dependencies inside venv..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Generate .env Configuration
if [ ! -f ".env" ]; then
    echo "cF Creating .env file..."
    # Create file with placeholder
    cat <<EOF > .env
FACEBOOK_ACCESS_TOKEN=REPLACE_ME
EOF
    echo "✅ .env created."
else
    echo "✅ .env found."
fi

echo ""
echo "=================================="
echo "✅ SETUP COMPLETE"
echo "=================================="
echo "👉 NEXT STEP: Run 'nano .env' and paste your Facebook Access Token."
echo "👉 THEN: Run './run.sh' to start the bot."
