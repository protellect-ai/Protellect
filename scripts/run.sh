#!/bin/bash
echo "🔬 Starting Protellect..."
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install from https://python.org"
    exit 1
fi

# Install deps if needed
echo "📦 Checking dependencies..."
pip install -r requirements.txt -q

echo ""
echo "✅ Launching Protellect at http://localhost:8501"
echo "   Press Ctrl+C to stop"
echo ""

streamlit run app.py
