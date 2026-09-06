# Day 28 — Docker Notes

## Files

- `Dockerfile` — multi-stage build for the FastAPI backend
  (`coverage-chatbot-api/main.py`). Builder stage installs deps into a
  venv; final stage is `python:3.11-slim` + `curl` (for the healthcheck)
  only, no build toolchain.
- `Dockerfile.frontend` — multi-stage build for the Streamlit frontend
  (`app.py`).
- `docker-compose.yml` — wires `backend` (port 8000) and `frontend` (port
  8501), both loading secrets from `.env` via `env_file`, with a
  `chroma_data` named volume mounted into the backend so the vector store
  survives container recreation, and `frontend` depending on `backend`
  being `service_healthy` before it starts.
- `.env.example` — placeholder keys only; copy to `.env` before running
  (`.env` is not committed).
- `.dockerignore` — keeps `.git`, `.env`, caches, and large training
  artifacts (embeddings, fine-tune JSONL) out of the build context.

## Running it locally

```
cp .env.example .env          # fill in real values if/when needed
docker compose up --build
```

## Health check

`GET /health` on the backend returns `{"status": "ok"}` — added to
`coverage-chatbot-api/main.py` specifically as the container health probe
target. The Dockerfile's `HEALTHCHECK` and `docker-compose.yml`'s
`healthcheck:` block both curl it every 30s.

Expected `docker ps` output after `docker compose up -d` and the 10s
start period elapses:

```
CONTAINER ID   IMAGE                    STATUS
<id>           ai-cohort-backend        Up 45 seconds (healthy)
<id>           ai-cohort-frontend       Up 40 seconds (healthy)
```

Manual confirmation:

```
$ curl http://localhost:8000/health
{"status":"ok"}
```

## Notes / gotchas

- The backend's build `context:` is the **repo root**, not
  `coverage-chatbot-api/`, because `main.py` does
  `from token_utils import count_tokens, estimate_cost` and
  `token_utils.py` lives at the repo root — the Dockerfile copies it in
  separately (`COPY token_utils.py ./token_utils.py`) alongside the
  `coverage-chatbot-api/` directory, and sets `PYTHONPATH=/app` so the
  import resolves regardless of the working directory the app runs from.
- `coverage.db` is intentionally **not** copied into the image —
  `main.py`'s `sqlite3.connect()` creates it on first run if missing.
  Only the Chroma vector store is volume-mounted per the mission spec;
  the SQLite file lives in the container's writable layer for this
  exercise (a production setup would volume-mount that too).
- The frontend's `API_URL` is overridden by compose to
  `http://backend:8000` (the compose service name), not
  `http://127.0.0.1:8000` — containers on the same compose network reach
  each other by service name, not localhost. `app.py` reads it from the
  `API_URL` env var with a localhost fallback for running it outside
  Docker.
- No API keys are hardcoded anywhere in `Dockerfile`, `Dockerfile.frontend`,
  or `docker-compose.yml` — both services load `.env` via `env_file:` only.
