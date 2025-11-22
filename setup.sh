#!/bin/bash
set -e

echo "=================================="
echo "   FB Auto Poster - One-Click Setup"
echo "=================================="

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please run: sudo apt update && sudo apt install python3 python3-venv -y"
    exit 1
fi

# 2. Check Venv Module (Critical for WSL)
if ! python3 -c "import venv" &> /dev/null; then
    echo "❌ Python venv module not found."
    echo "👉 Please run: sudo apt install python3-venv -y"
    exit 1
fi

# 3. Create Virtual Environment
if [ ! -d "venv" ]; then
    echo "📦 Creating Virtual Environment (venv)..."
    python3 -m venv venv
else
    echo "✅ Venv already exists."
fi

# 4. Install Dependencies
echo "⬇️  Installing/Updating Dependencies..."
source venv/bin/activate
pip install --upgrade pip > /dev/null
pip install -r requirements.txt

# 5. Streamlit Config (Suppress Email Prompt)
if [ ! -f ".streamlit/config.toml" ]; then
    echo "⚙️  Configuring Streamlit..."
    mkdir -p .streamlit
    echo "[browser]
gatherUsageStats = false
[server]
headless = true" > .streamlit/config.toml
fi

# 6. Generate .env if missing
if [ ! -f ".env" ]; then
    echo "cF Creating .env file..."
    echo "FACEBOOK_ACCESS_TOKEN=REPLACE_ME" > .env
    echo "✅ .env created."
else
    echo "✅ .env found."
fi

echo ""
echo -e "\033[0;32mSUCCESS! Setup Complete.\033[0m"
echo "👉 Action Required: Run 'nano .env' and paste your Access Token."
echo "👉 Then run: bash run.sh"
