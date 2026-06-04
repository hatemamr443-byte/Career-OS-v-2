FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Dependency stage ─────────────────────────────────────────────
FROM base AS deps

COPY backend/requirements.txt .
RUN pip install --no-cache-dir \
    --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ \
    -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# ── Runtime stage ─────────────────────────────────────────────────
FROM base AS runtime

RUN groupadd -r career && useradd -r -g career career

WORKDIR /app/backend

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY backend/ .

USER career

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Use gunicorn + uvicorn workers for production scalability
# WEB_CONCURRENCY env var overrides worker count (Render sets it automatically)
CMD ["sh", "-c", "gunicorn server:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers ${WEB_CONCURRENCY:-2} \
    --bind 0.0.0.0:8001 \
    --timeout 120 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile -"]
