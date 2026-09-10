#!/usr/bin/env bash
set -euo pipefail

# Detect root directory
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Auralis Environment Setup ==="

# 1. Setup Backend Python Virtual Environment
echo "--> Setting up Python backend in backend/..."
cd "$ROOT_DIR/backend"
chmod +x setup-backend.sh
./setup-backend.sh

# 2. Setup Frontend if pnpm is available
if command -v pnpm &> /dev/null; then
    echo "--> Installing frontend dependencies in frontend/..."
    cd "$ROOT_DIR/frontend"
    pnpm install
fi

cd "$ROOT_DIR"
echo ""
echo "=== All Set! ==="
echo "• To run the backend:   cd backend && uv run uvicorn app.main:app --reload --port 8000"
echo "• To run backend tests: cd backend && uv run pytest -v"
echo "• To run frontend:      cd frontend && pnpm run dev"
echo "• To start with Docker: docker compose up --build"
