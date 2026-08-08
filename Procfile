# Toolforge Buildpack Procfile
# https://wikitech.wikimedia.org/wiki/Help:Toolforge/Building_container_images/My_first_Buildpack_Python_tool
#
# IMPORTANT:
# - FastAPI is ASGI → must use uvicorn worker class (not gunicorn default "sync")
# - With --mount=none, $HOME may point at unwritable /data paths → force HOME/TMPDIR=/tmp

web: bash -c "export HOME=/tmp TMPDIR=/tmp XDG_CACHE_HOME=/tmp/.cache && cd backend && exec gunicorn --workers=1 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:${PORT:-8000} --forwarded-allow-ips='*' --access-logfile - --error-logfile - --capture-output app.main:app"

migrate: bash -c "export HOME=/tmp TMPDIR=/tmp && cd backend && exec alembic upgrade head"
seed: bash -c "export HOME=/tmp TMPDIR=/tmp && cd backend && exec python -m app.jobs.cli seed-registry"
bootstrap: bash -c "export HOME=/tmp TMPDIR=/tmp && cd backend && exec python -m app.jobs.cli bootstrap --project fa.wikipedia --months 24"
collect-health: bash -c "export HOME=/tmp TMPDIR=/tmp && cd backend && exec python -m app.jobs.cli collect-health --project fa.wikipedia --months 2"
daily: bash -c "export HOME=/tmp TMPDIR=/tmp && cd backend && exec python -m app.jobs.cli daily --project fa.wikipedia"
check: bash -c "export HOME=/tmp TMPDIR=/tmp && cd backend && exec python -m app.jobs.cli check-connectivity"
