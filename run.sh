#!/bin/bash
set -e

# Ensure we are in the script's directory
cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run './setup.sh' first."
    exit 1
fi

echo "🚀 Activating environment..."
source venv/bin/activate

echo "qh Launching Dashboard..."
echo "👉 If the browser does not open, copy the 'Local URL' below into your Windows browser."

streamlit run dashboard.py
