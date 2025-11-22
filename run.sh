#!/bin/bash
set -e

# Ensure venv exists
if [ ! -d "venv" ]; then
    echo "❌ Venv not found. Please run 'bash setup.sh' first."
    exit 1
fi

source venv/bin/activate

echo "🚀 Starting Dashboard..."
echo "👉 Opening in your default browser..."

streamlit run dashboard.py
