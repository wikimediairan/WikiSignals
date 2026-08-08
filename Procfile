# Toolforge Buildpack Procfile
# https://wikitech.wikimedia.org/wiki/Help:Toolforge/Building_container_images
# First `web` entry is used by: toolforge webservice buildservice start --mount=none
#
# Buildpack installs deps from root requirements.txt and puts gunicorn/python on PATH.
# App code lives under backend/ — use --chdir so "app.main:app" imports correctly.

web: gunicorn --workers=1 --bind=0.0.0.0:$PORT --forwarded-allow-ips=* --chdir=backend app.main:app

# Jobs: toolforge jobs run --image tool-wikisignals/tool-wikisignals:latest --command "migrate" ...
migrate: bash -c "cd backend && alembic upgrade head"
seed: bash -c "cd backend && python -m app.jobs.cli seed-registry"
bootstrap: bash -c "cd backend && python -m app.jobs.cli bootstrap --project fa.wikipedia --months 24"
collect-health: bash -c "cd backend && python -m app.jobs.cli collect-health --project fa.wikipedia --months 2"
daily: bash -c "cd backend && python -m app.jobs.cli daily --project fa.wikipedia"
check: bash -c "cd backend && python -m app.jobs.cli check-connectivity"
