#!/usr/bin/env bash
# Farq Sound — bring up the full local stack in one shot.
#
# Starts Redis, FastAPI, Celery worker, and Next.js. Stops them cleanly
# on Ctrl+C. Uses mock providers when ELEVENLABS_API_KEY / MOYASAR_API_KEY
# are empty, so it runs end-to-end with zero external credentials.
#
# Prerequisites (one-time):
#   sudo apt install ffmpeg rubberband-cli libsndfile1 redis-server
#   pnpm install
#   python -m venv apps/api/.venv && apps/api/.venv/bin/pip install -r apps/api/requirements.txt
#   python apps/api/assets/make_demo_audio.py
#
# Then:
#   ./infra/local-up.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p .runtime/logs
PIDS_FILE=".runtime/pids"
: >"$PIDS_FILE"

cleanup() {
  echo
  echo "→ stopping services..."
  while read -r pid; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  done <"$PIDS_FILE"
  redis-cli -p 6379 shutdown 2>/dev/null || true
  wait 2>/dev/null || true
  echo "→ done."
}
trap cleanup EXIT INT TERM

# ----- env -----
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "→ wrote .env from .env.example — fill in keys if you want live providers"
fi
set -a; source .env; set +a

# ----- Redis -----
if ! redis-cli ping &>/dev/null; then
  echo "→ starting Redis on :6379"
  redis-server --daemonize yes --port 6379 --save "" --appendonly no \
    --logfile "$ROOT/.runtime/logs/redis.log"
  sleep 0.5
fi

# ----- FastAPI -----
echo "→ starting FastAPI on :8000"
(
  cd apps/api && source .venv/bin/activate
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) &>".runtime/logs/api.log" &
echo $! >>"$PIDS_FILE"

# ----- Celery worker -----
echo "→ starting Celery worker"
(
  cd apps/api && source .venv/bin/activate
  exec celery -A app.workers.celery_app worker -l info --concurrency=2
) &>".runtime/logs/worker.log" &
echo $! >>"$PIDS_FILE"

# ----- Next.js -----
echo "→ starting Next.js on :3000"
(
  cd apps/web && exec pnpm dev
) &>".runtime/logs/web.log" &
echo $! >>"$PIDS_FILE"

sleep 2
echo
echo "  web → http://localhost:3000"
echo "  api → http://localhost:8000/health"
echo "  logs: tail -f .runtime/logs/{api,worker,web}.log"
echo
echo "  Press Ctrl+C to stop everything."
wait
