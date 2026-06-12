#!/usr/bin/env bash
# TenderProof — local development launcher.
# Prerequisites: MongoDB + Redis reachable (see backend/.env), Python deps
# installed (pip install -r backend/requirements.txt), client deps installed
# (cd client && npm install), and backend/.env populated from .env.example.
set -euo pipefail

cd "$(dirname "$0")"

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT

echo "[1/3] Starting Celery worker…"
(cd backend && celery -A app.worker worker --loglevel=info) &

echo "[2/3] Starting FastAPI on :8000…"
(cd backend && uvicorn app.main:app --reload --port 8000) &

echo "[3/3] Starting Next.js on :3000…"
(cd client && npm run dev) &

wait
