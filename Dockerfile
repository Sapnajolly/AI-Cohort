# Day 28: Multi-stage Dockerfile for the FastAPI backend (coverage-chatbot-api).
# Build context is the REPO ROOT (docker-compose.yml uses `context: .`),
# because main.py imports token_utils.py which lives at the repo root and
# reads coverage.db from one level above coverage-chatbot-api/.

# ---------- Stage 1: builder — installs dependencies into a venv ----------
FROM python:3.11-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY coverage-chatbot-api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir tiktoken

# ---------- Stage 2: final — slim runtime image, no build tools ----------
FROM python:3.11-slim AS final

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Repo-root modules main.py imports (token_utils.py). coverage.db is NOT
# copied in — main.py's sqlite3.connect() creates it on first run if it
# doesn't exist, and docker-compose.yml mounts a volume so it (and the
# Chroma data dir) persist across container restarts instead of living
# only in the image layer.
COPY token_utils.py ./token_utils.py
COPY coverage-chatbot-api/ ./coverage-chatbot-api/

WORKDIR /app/coverage-chatbot-api

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
