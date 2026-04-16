#!/usr/bin/env bash
set -euo pipefail

trap 'kill 0' EXIT

echo "启动后端 (FastAPI :8000)..."
uv run uvicorn asset_hub.api.app:app --reload --port 8000 &

echo "启动前端 (Vite :5173)..."
pnpm --dir frontend dev &

wait
