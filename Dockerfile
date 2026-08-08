# Toolforge / production image (build from repository root)
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/ /app/
COPY config/ /config/

RUN chmod +x /app/start.sh

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV CONFIG_DIR=/config
ENV WEB_CONCURRENCY=1
# Toolforge injects PORT at runtime
ENV PORT=8000

EXPOSE 8000

# Use shell script so $PORT is always honored by the webservice mesh
CMD ["/app/start.sh"]
