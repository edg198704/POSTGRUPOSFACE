#!/bin/bash
set -e

# Ensure venv exists
if [ ! -d "venv" ]; then
    echo "❌ Venv not found. Please run 'bash setup.sh' first."
    exit 1
fi

source venv/bin/activate

echo "🚀 Starting Dashboard..."
echo "👉 Open the URL below in your Windows Browser (usually http://localhost:8501)"
echo ""
streamlit run dashboard.py
