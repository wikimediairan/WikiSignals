# Toolforge / production image (build from repository root)
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# App code + project/metric YAML config
COPY backend/ /app/
COPY config/ /config/

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV CONFIG_DIR=/config

# Toolforge sets PORT; default for local docker
ENV PORT=8000

EXPOSE 8000

# Prefer gunicorn in production; fall back if PORT unset
CMD gunicorn -b 0.0.0.0:${PORT:-8000} -w 2 -k uvicorn.workers.UvicornWorker app.main:app
