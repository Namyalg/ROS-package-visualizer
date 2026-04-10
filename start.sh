#!/bin/bash

# Package.XML Visualizer - One-Command Start Script

cd "$(dirname "$0")"

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv and start app
source venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null

echo ""
echo "================================"
echo "Starting Package.XML Visualizer"
echo "================================"
echo ""
echo "Opening http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python3 app.py
