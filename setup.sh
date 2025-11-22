#!/bin/bash
set -e

echo "=================================="
echo "   FB Auto Poster - One-Click Setup"
echo "=================================="

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Installing..."
    sudo apt update && sudo apt install python3 -y
fi

# 2. Check Pip
if ! command -v pip3 &> /dev/null; then
    echo "📦 Installing pip..."
    sudo apt install python3-pip -y
fi

# 3. Check Node.js (Optional but requested check)
if ! command -v node &> /dev/null; then
    echo "⚠️  Node.js not found. (Optional for Python Dashboard)"
else
    echo "✅ Node.js found."
fi

# 4. Check for venv module
if ! python3 -c "import venv" &> /dev/null; then
    echo "❌ Python venv module not found."
    echo "📦 Installing python3-venv..."
    sudo apt install python3-venv -y
fi

# 5. Create Virtual Environment
if [ ! -d "venv" ]; then
    echo "📦 Creating Virtual Environment (venv)..."
    python3 -m venv venv
else
    echo "✅ Venv already exists."
fi

# 6. Install Dependencies
echo "⬇️  Installing/Updating Dependencies..."
source venv/bin/activate
pip install --upgrade pip > /dev/null
pip install -r requirements.txt

# 7. Generate .env if missing
if [ ! -f ".env" ]; then
    echo "cF Creating .env file..."
    echo "FACEBOOK_ACCESS_TOKEN=REPLACE_ME" > .env
    echo "✅ .env created."
else
    echo "✅ .env found."
fi

echo ""
echo -e "\033[0;32mSetup Complete! Now run 'nano .env' to add your keys.\033[0m"
