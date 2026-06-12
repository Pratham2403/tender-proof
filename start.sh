#!/usr/bin/env bash
# TenderProof — local development launcher.
# Prerequisites: MongoDB + Redis reachable (see backend/.env), Python deps
# installed (pip install -r backend/requirements.txt), client deps installed
# (cd client && npm install), and backend/.env populated from .env.example.
set -euo pipefail

cd "$(dirname "$0")"

# PURGE POINT 1 — cold shutdown via SIGINT:
# Ctrl+C sends SIGINT to every process in this script's process group
# simultaneously. Celery's SIGINT handler triggers a COLD shutdown: it
# immediately revokes all in-flight tasks and discards them. The `cleanup`
# below then runs on EXIT and sends SIGTERM to whatever is left, but the
# damage is already done — Celery has already purged its running tasks.
#
# TO GET WARM SHUTDOWN INSTEAD (finish current tasks, reject new ones, die):
#   Step 1 — capture Celery's PID right after launching it (see [1/3] below).
#   Step 2 — replace `cleanup` with:
#
#     graceful_shutdown() {
#       echo "Shutting down — waiting for Celery tasks to finish…"
#       kill -SIGTERM "$CELERY_PID" 2>/dev/null || true  # warm shutdown
#       wait "$CELERY_PID"                               # wait until drained
#       kill 0 2>/dev/null || true                       # kill uvicorn + Next.js
#     }
#
#   Step 3 — change the trap to:
#     trap graceful_shutdown INT TERM EXIT
#
# With warm shutdown, Celery stops accepting new tasks, finishes whatever is
# running, then exits — no tasks are purged or lost.
cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT

echo "[0/3] Checking Services..."
(sudo systemctl status mongod-service redis-server) || { echo "MongoDB and Redis must be running!"; exit 1; }

echo "[1/3] Starting Celery worker…"
# NOTE: to implement warm shutdown (see comment above), add `& CELERY_PID=$!`
# on the line below so the PID is available in graceful_shutdown().
(cd backend && celery -A app.worker worker --loglevel=info) &

echo "[2/3] Starting FastAPI on :8000…"
(cd backend && source ./venv/bin/activate && uvicorn app.main:app --reload --port 8000) &

echo "[3/3] Starting Next.js on :3000…"
(cd client && npm run dev) &

wait
