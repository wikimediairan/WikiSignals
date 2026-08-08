#!/bin/sh
# Toolforge / container entrypoint — always bind to $PORT
set -eu

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-1}"

echo "WikiSignals starting on 0.0.0.0:${PORT} (workers=${WORKERS})"
echo "CONFIG_DIR=${CONFIG_DIR:-unset} ENVIRONMENT=${ENVIRONMENT:-unset}"

# Fail fast with a clear message if DB URL looks like the local default on "production"
if [ "${ENVIRONMENT:-}" = "production" ] && echo "${DATABASE_URL:-}" | grep -q '127.0.0.1\|localhost'; then
  echo "ERROR: DATABASE_URL points at localhost in production. Set ToolsDB URL via toolforge envvars." >&2
  exit 1
fi

exec gunicorn \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WORKERS}" \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --capture-output \
  app.main:app
