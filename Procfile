# Toolforge Buildpack Procfile
# https://wikitech.wikimedia.org/wiki/Help:Toolforge/Building_container_images/My_first_Buildpack_Python_tool
#
# - FastAPI needs uvicorn worker class
# - HOME=/tmp with --mount=none
# - Unset CONFIG_DIR: old Docker docs set /config which does not exist on buildpack

web: bash -c "export HOME=/tmp TMPDIR=/tmp XDG_CACHE_HOME=/tmp/.cache; unset CONFIG_DIR; cd backend && exec gunicorn --workers=1 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:${PORT:-8000} --forwarded-allow-ips='*' --access-logfile - --error-logfile - --capture-output app.main:app"

migrate: bash -c "export HOME=/tmp TMPDIR=/tmp; unset CONFIG_DIR; cd backend && exec alembic upgrade head"
seed: bash -c "export HOME=/tmp TMPDIR=/tmp; unset CONFIG_DIR; cd backend && exec python -m app.jobs.cli seed-registry"
diagnose: bash -c "export HOME=/tmp TMPDIR=/tmp; unset CONFIG_DIR; cd backend && exec python -m app.jobs.cli diagnose"
bootstrap: bash -c "export HOME=/tmp TMPDIR=/tmp; unset CONFIG_DIR; cd backend && exec python -m app.jobs.cli bootstrap --project fa.wikipedia --months 24"
bootstrap-5y: bash -c "export HOME=/tmp TMPDIR=/tmp; unset CONFIG_DIR; cd backend && exec python -m app.jobs.cli bootstrap --project fa.wikipedia --months 60"
ingest-5y: bash -c "export HOME=/tmp TMPDIR=/tmp; unset CONFIG_DIR; cd backend && exec python -m app.jobs.cli ingest --project fa.wikipedia --since 2021-01-01"
collect-health: bash -c "export HOME=/tmp TMPDIR=/tmp; unset CONFIG_DIR; cd backend && exec python -m app.jobs.cli collect-health --project fa.wikipedia --months 2"
daily: bash -c "export HOME=/tmp TMPDIR=/tmp; unset CONFIG_DIR; cd backend && exec python -m app.jobs.cli daily --project fa.wikipedia"
check: bash -c "export HOME=/tmp TMPDIR=/tmp; unset CONFIG_DIR; cd backend && exec python -m app.jobs.cli check-connectivity"
