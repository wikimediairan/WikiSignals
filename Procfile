# Toolforge Build Service runs this `web` process (often with a minimal PATH).
# Use absolute interpreter path from the official python Docker image.
web: /usr/local/bin/python -m gunicorn --bind 0.0.0.0:$PORT --workers 1 --worker-class uvicorn.workers.UvicornWorker --timeout 120 --access-logfile - --error-logfile - app.main:app
