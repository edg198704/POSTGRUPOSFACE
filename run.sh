#!/bin/bash
set -e

# Ensure we are in the script's directory
cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "👉 Please run './setup.sh' first."
    exit 1
fi

# Activate Virtual Environment
source venv/bin/activate

# Launch Dashboard
echo "🚀 Launching Dashboard..."
echo "👉 Open this URL in your browser: http://localhost:8501"

# Run headless to avoid xdg-open issues in WSL
streamlit run dashboard.py --server.headless true
