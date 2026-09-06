# AI Cohort — Coverage Chatbot (31-Day Build)

A member-facing insurance coverage/claims chatbot, built incrementally over
a 31-day program: starting from a basic RAG chatbot and ending as a
multi-agent, MCP-tooled, containerized, Kubernetes-deployed, observable
production system.

## What this is

Members ask natural-language questions about their health plan coverage
and claim status ("What's my deductible?", "Is physical therapy covered
under my Silver plan?", "What's the status of claim CLM-2024-0892?") and
get grounded answers pulled from structured plan/claim data plus a policy
document vector store, with conversation memory across turns, safety
guardrails, and cost/usage tracking.

## Architecture

```
Streamlit frontend (app.py)
        |
        v
FastAPI backend (coverage-chatbot-api/main.py)
        |
        +-- Router --------------> classifies coverage vs. claims vs. general
        |
        +-- Coverage Specialist --> MCP get_plan_details / check_coverage
        |                           (structured plan row + vector_lookup for
        |                            policy-wording questions)
        |
        +-- Claims Specialist ----> MCP get_claim_status
        |
        +-- Guardrails -----------> input/output checks (PII redaction,
        |                           jailbreak/prompt-injection blocking,
        |                           medical-advice redirect)
        |
        +-- Memory ---------------> SQLite conversation history, recent-turn
        |                           context window, auto-summarization
        |
        +-- Token/Cost governance -> tiktoken counting, per-1K cost estimate,
        |                           per-member rate limiting, exact-match
        |                           caching for general (non-member-specific)
        |                           questions
        |
        +-- Langfuse tracing -----> full input/output/metadata trace per call
```

Deployed via Docker (multi-stage builds, docker-compose) and Kubernetes
(Deployments, Services, Secrets, readiness/liveness probes, rolling
updates).

## Day-by-day build log

| Days | Theme |
|---|---|
| 1-20 | Core chatbot: RAG retrieval, structured data lookups, conversation memory (built prior to this session) |
| 21 | LangChain ReAct agent wrapping the chatbot's tools |
| 22 | Multi-agent routing (Coverage Specialist / Claims Specialist) |
| 23 | MCP server exposing `get_plan_details`, `check_coverage`, `get_claim_status` as tools |
| 24 | Async multi-agent system over MCP with timeout + retry-once resilience, chaos testing |
| 25 | AI governance: PHI/PII redaction, prompt-injection/jailbreak guardrails, medical-advice redirects, adversarial test suite |
| 26 | Token/cost governance: tiktoken-based counting, per-member rate limiting, exact-match caching for general questions |
| 27 | RAGAS evaluation (faithfulness, answer relevancy, context precision/recall) and a real bug fix it surfaced |
| 28 | Dockerization: multi-stage builds, healthcheck, docker-compose |
| 29 | Kubernetes deployment on Minikube: Deployments, Services, Secrets, scaling, rolling updates |
| 30 | Observability: Langfuse tracing, kubectl debugging practice, production alert design |
| 31 | Capstone: end-to-end walkthrough, retrospective, v2 roadmap |

## Key files

- `coverage-chatbot-api/main.py` — FastAPI backend (chat endpoint, memory, rate limiting, caching, token logging, Langfuse tracing, health probe)
- `token_utils.py` — token counting + cost estimation
- `redact_pii.py`, `guardrails_config.py` — safety layer
- `mcp_server.py`, `multi_agent.py` — MCP tools + async multi-agent orchestration
- `ragas_eval_set.jsonl`, `ragas_run.py`, `ragas_scorecard.md` — retrieval quality evaluation
- `Dockerfile`, `Dockerfile.frontend`, `docker-compose.yml` — containerization
- `k8s/` — Kubernetes manifests
- `observability_notes.md` — tracing + alerting design
- `capstone_walkthrough.md` — 5 end-to-end scenario walkthroughs
- `retrospective.md` — what worked, what was hard, what's next
- `v2_roadmap.md` — prioritized v2 feature roadmap

## Demo

Portfolio walkthrough video: link here once recorded (Google Drive /
YouTube unlisted) — a short screen-capture running the 5 scenarios in
`capstone_walkthrough.md` against the Kubernetes-deployed stack with
Langfuse tracing visible.

## Running it locally

```
docker compose up --build
```

Frontend on `:8501`, backend on `:8000` (`/health` for the readiness
probe, `/chat` for the SSE chat endpoint, `/usage/{session_id}` for
token/cost reporting).

## Running it on Kubernetes

See `k8s_notes.md` for the full Minikube walkthrough (secret creation,
apply, scale, rolling update, teardown).
