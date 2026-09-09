#!/usr/bin/env bash
set -e

echo "=== Setting up Auralis Backend Environment ==="

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Found Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment in venv/..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo "=== Backend Setup Complete ==="
echo "To activate the environment: source venv/bin/activate"
echo "To run tests: pytest"
echo "To start the server: uvicorn app.main:app --reload --port 8000"
