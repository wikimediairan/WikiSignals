# Toolforge Build Service runs the `web` process for webservice.
# Image WORKDIR is /app (backend code); use python -m so PATH is irrelevant.
web: python -m gunicorn --bind 0.0.0.0:$PORT --workers ${WEB_CONCURRENCY:-1} --worker-class uvicorn.workers.UvicornWorker --timeout 120 --access-logfile - --error-logfile - app.main:app
