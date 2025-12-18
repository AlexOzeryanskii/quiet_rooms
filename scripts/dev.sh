#!/usr/bin/env bash
set -euo pipefail

# Универсальный дев-стартер для control-plane, node_service и фронта.
# Запуск из корня проекта:
#   bash scripts/dev.sh

ROOT_DIR=$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if [ -f "$ROOT_DIR/.env" ]; then
  # Простой способ подхватить переменные окружения для backend
  set -a
  # shellcheck source=/dev/null
  source "$ROOT_DIR/.env"
  set +a
fi

if [ -f "$ROOT_DIR/node_service/.env.node" ]; then
  # Переменные ноды
  set -a
  # shellcheck source=/dev/null
  source "$ROOT_DIR/node_service/.env.node"
  set +a
fi

cd "$ROOT_DIR"

echo "[dev] Стартуем control-plane (port 8000)..."
uvicorn app.main:app --reload --port 8000 &
CP_PID=$!

echo "[dev] Стартуем node_service (port 9000)..."
uvicorn node_service.app.main:app --reload --host 0.0.0.0 --port 9000 &
NODE_PID=$!

echo "[dev] Стартуем frontend (port 5173)..."
(cd frontend && npm run dev -- --host --port 5173) &
FE_PID=$!

cleanup() {
  echo "\n[dev] Завершаем процессы..."
  kill $CP_PID $NODE_PID $FE_PID 2>/dev/null || true
  wait $CP_PID $NODE_PID $FE_PID 2>/dev/null || true
}

trap cleanup INT TERM

wait
