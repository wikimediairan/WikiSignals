#!/usr/bin/env bash
# Toolforge daily entrypoint — keep this script short and env-driven.
set -euo pipefail

cd "$(dirname "$0")/../backend" 2>/dev/null || cd backend || true
export PYTHONPATH="${PYTHONPATH:-.}"

python -m app.jobs.cli daily "$@"
