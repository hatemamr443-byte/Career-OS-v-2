# ─────────────────────────────────────────────────────────────────
# Career OS — Backend Dockerfile
# Multi-stage: build dependencies → slim runtime image
# ─────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Dependency stage ─────────────────────────────────────────────
FROM base AS deps

COPY backend/requirements.txt .
RUN pip install --no-cache-dir \
    --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ \
    -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────
FROM base AS runtime

# Create non-root user for security
RUN groupadd -r career && useradd -r -g career career

WORKDIR /app/backend

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy backend source
COPY backend/ .

# Non-root runtime
USER career

EXPOSE 8001

# Health check — liveness probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
