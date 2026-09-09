#!/usr/bin/env bash
set -e

# Detect root directory
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Auralis Environment Setup ==="

# 1. Setup Backend Python Virtual Environment
echo "--> Setting up Python backend in backend/..."
cd "$ROOT_DIR/backend"
chmod +x setup.sh
./setup.sh

# 2. Setup Frontend if npm is available
if command -v npm &> /dev/null; then
    echo "--> Installing frontend dependencies in frontend/..."
    cd "$ROOT_DIR/frontend"
    npm install
fi

cd "$ROOT_DIR"
echo ""
echo "=== All Set! ==="
echo "• To activate backend:  cd backend && source venv/bin/activate"
echo "• To run backend tests: cd backend && source venv/bin/activate && pytest -v"
echo "• To run frontend:      cd frontend && npm run dev"
echo "• To start with Docker: docker-compose up --build"
