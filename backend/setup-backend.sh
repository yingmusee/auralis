#!/usr/bin/env bash
set -euo pipefail

echo "=== Setting up Auralis Backend Environment ==="

# Ensure uv is available
if ! command -v uv &> /dev/null; then
    echo "uv not found — installing via the official installer..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for the rest of this script
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi

# Create the virtual environment (in .venv/) and install dependencies from uv.lock
echo "Syncing dependencies from uv.lock..."
uv sync

echo "=== Backend Setup Complete ==="
echo "To run the server:   uv run uvicorn app.main:app --reload --port 8000"
echo "To run tests:        uv run pytest"
