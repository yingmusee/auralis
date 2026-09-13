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

# ffmpeg is required for formats that libsndfile cannot decode, such as M4A/AAC.
if ! command -v ffmpeg &> /dev/null; then
    echo "Error: ffmpeg is required for M4A/AAC and other container formats."
    echo "Install it with 'brew install ffmpeg' on macOS or your system package manager on Linux."
    exit 1
fi

# Create the virtual environment (in .venv/) and install dependencies from uv.lock
echo "Syncing dependencies from uv.lock..."
uv sync

echo "=== Backend Setup Complete ==="
echo "To run the server:   uv run uvicorn app.main:app --reload --reload-dir app --port 8000"
echo "To run tests:        uv run pytest"
