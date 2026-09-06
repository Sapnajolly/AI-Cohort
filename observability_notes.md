# Day 30 — Observability Notes

## 1. Langfuse wiring

`coverage-chatbot-api/main.py` initializes a `Langfuse()` client from
`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` env vars
(never hardcoded — passed via `.env`/`env_file` locally and via the k8s
Secret in the cluster, same `coverage-chatbot-secrets` object from Day 29
extended with the Langfuse keys). If the keys aren't set, `_langfuse` is
`None` and `_trace_to_langfuse()` no-ops, so tracing is opt-in and never
crashes the app.

Every `/chat` call logs one trace via `_trace_to_langfuse()`, capturing:
- `input`: the full prompt (user message)
- `output`: the full generated response
- `metadata.prompt_tokens` / `completion_tokens` (from `token_utils.count_tokens`, Day 26)
- `metadata.latency_ms` (wall-clock time from request start to completion)
- `metadata.error` (set when the LLM call raised, output omitted in that case)

```
kubectl create secret generic coverage-chatbot-secrets \
  --from-literal=OPENAI_API_KEY=your-key-here \
  --from-literal=LANGFUSE_PUBLIC_KEY=pk-lf-xxxx \
  --from-literal=LANGFUSE_SECRET_KEY=sk-lf-xxxx \
  --from-literal=LANGFUSE_HOST=https://cloud.langfuse.com
```

## 2. Redeploy + confirm traces

```
docker compose build backend
kubectl set image deployment/coverage-chatbot-backend backend=coverage-chatbot-backend:latest
kubectl rollout status deployment/coverage-chatbot-backend
```

After sending a few `/chat` requests through the frontend, the Langfuse
dashboard's Traces view shows one `coverage-chatbot-chat` trace per call,
each expandable to the full input/output pair plus the
`prompt_tokens` / `completion_tokens` / `latency_ms` metadata — confirming
the tracing wiring reaches the deployed (not just local) backend.

## 3. kubectl debugging practice

Intentionally broke a pod (set the backend's image tag to a nonexistent
one) to practice the debug workflow:

```
$ kubectl get pods
NAME                                       READY   STATUS             RESTARTS
coverage-chatbot-backend-7f9c8d6b5-x2z9p   0/1     ImagePullBackOff   0

$ kubectl describe pod coverage-chatbot-backend-7f9c8d6b5-x2z9p
...
Events:
  Type     Reason     Age   From               Message
  ----     ------     ----  ----               -------
  Normal   Scheduled  30s   default-scheduler  Successfully assigned ...
  Normal   Pulling    28s   kubelet            Pulling image "coverage-chatbot-backend:doesnotexist"
  Warning  Failed     10s   kubelet            Failed to pull image: not found
  Warning  Failed     10s   kubelet            Error: ErrImagePull
```

`describe pod`'s Events section is what pinpointed the cause (bad image
tag) immediately — much faster than guessing from `get pods`'s STATUS
column alone.

After fixing the image tag and reapplying:

```
$ kubectl logs -f coverage-chatbot-backend-<new-pod-id>
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
[TOKENS] session=... member=... prompt=41 completion=68 est_cost=$0.000198
```

`kubectl logs -f` (follow mode) is how the token/cost log lines from Day
26 and the `[LANGFUSE]` failure-fallback print (if tracing ever fails)
get watched live during a debugging session, without re-running the
command for every new line.

## 4. Production alert sketch

| Alert | Metric | Threshold | Why |
|---|---|---|---|
| **Error rate** | % of `/chat` calls returning `error` in the SSE stream (or a non-2xx status) over a 5-minute window | > 5% for 5 min | Anything above a low single-digit error rate means the LLM backend, DB, or a tool call is failing for real users, not just occasional flakiness. |
| **p95 latency** | 95th-percentile `latency_ms` from the Langfuse trace metadata, over a 5-minute window | > 8000 ms | The `/chat` endpoint streams tokens, so total latency matters less than time-to-first-token in a real product, but a p95 this high on total latency signals the LLM call itself (or a hung tool call) is degrading badly for 1 in 20 users. |
| **Daily cost ceiling** | Sum of `est_cost_usd` from the `token_usage` table (Day 26) / Langfuse cost tracking, rolled up daily | > $50/day (placeholder — set to the actual approved budget) | Catches a runaway loop, a caching regression, or unexpectedly high traffic before it becomes a billing surprise; paired with the Day 26 per-member rate limit as the first line of defense. |

Each of these maps directly to data already being collected: error rate
and latency come straight from the Langfuse traces this day wires up,
and the cost ceiling comes from Day 26's `token_usage` logging — this
sketch is deliberately built on top of instrumentation this repo already
has, not hypothetical future work.
