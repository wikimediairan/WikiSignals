#!/bin/sh
# Toolforge / container entrypoint — always bind to $PORT
set -eu

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-1}"

# Prefer absolute path — Toolforge webservice may use a stripped PATH
if [ -x /usr/local/bin/python ]; then
  PYTHON=/usr/local/bin/python
elif [ -x /usr/local/bin/python3 ]; then
  PYTHON=/usr/local/bin/python3
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=$(command -v python3)
elif command -v python >/dev/null 2>&1; then
  PYTHON=$(command -v python)
else
  echo "ERROR: no Python interpreter found" >&2
  ls -la /usr/local/bin/ 2>/dev/null || true
  exit 1
fi

echo "WikiSignals starting on 0.0.0.0:${PORT} (workers=${WORKERS}) python=${PYTHON}"
echo "CONFIG_DIR=${CONFIG_DIR:-unset} ENVIRONMENT=${ENVIRONMENT:-unset}"

if [ "${ENVIRONMENT:-}" = "production" ] && echo "${DATABASE_URL:-}" | grep -q '127.0.0.1\|localhost'; then
  echo "ERROR: DATABASE_URL points at localhost in production. Set ToolsDB URL via toolforge envvars." >&2
  exit 1
fi

exec "${PYTHON}" -m gunicorn \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WORKERS}" \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --capture-output \
  app.main:app
