# Day 31 — Retrospective

## What worked

- **Building tools before wiring agents around them (Day 23 before Day
  24)** paid off — once `get_plan_details` / `check_coverage` /
  `get_claim_status` existed as clean MCP tools with defined
  input/output contracts, the async multi-agent orchestration in Day 24
  was mostly plumbing, not new logic.
- **Running the RAGAS eval (Day 27) against the actual retrieval
  pipeline, not a toy example**, surfaced a real bug — `sql_lookup()`
  was returning rows across all coverage tiers instead of filtering to
  the member's own plan, which was quietly dragging Context Precision
  down to 0.72. Fixing it and re-running the eval (0.72 -> 0.91) is the
  single most concrete "the process caught something real" moment in
  the whole program.
- **Actually executing the guardrail and PII-redaction regexes against
  realistic adversarial inputs (Day 25)** instead of eyeballing the
  patterns — two guardrail regexes and one phone-number regex were
  quietly broken (too narrow / wrong anchoring) and would have shipped
  broken if I'd trusted them on inspection alone.
- **Keeping the token/cost governance (Day 26) and rate limiting in the
  same layer** made the later Docker/K8s/observability days simpler —
  by Day 30, "trace every `/chat` call" just meant hanging one more
  function off the same request path that was already logging tokens.
- **Writing the Docker and Kubernetes notes as "expected behavior"
  documentation with the actual reasoning behind each design decision**
  (why `coverage.db` isn't copied into the image, why the compose
  volume can't shadow `/app`, why `PYTHONPATH=/app` is needed) instead
  of just pasting commands — this is what makes those days reviewable
  by someone else later, not just a log of things typed into a
  terminal.

## What was hard

- **Sandbox environment gaps.** No running Docker daemon and no network
  path to tiktoken's vocabulary CDN meant Days 26, 28, and 29 had to be
  built and reasoned through carefully rather than verified by actually
  running `docker compose up` or `kubectl apply`. The mitigation was
  writing precise "Expected:" output based on how each tool actually
  behaves, and being explicit about the limitation rather than
  fabricating fake successful command output.
- **Getting the RAGAS eval script to actually match the real
  `rag_chatbot.retrieve_and_answer` function signature** required going
  back to Day 11's actual code instead of guessing a plausible-looking
  interface — a reminder that evaluation code is only as good as its
  fidelity to what it's actually testing.
- **The exact-match quiz verification on abtalks.in** was less forgiving
  than expected in a few spots — some checklist items wanted the literal
  parameter name (`readinessProbe`/`livenessProbe`) rather than a
  paraphrase ("readiness and liveness"), which meant a few submit ->
  inspect-verification -> correct -> resubmit cycles per day rather than
  one-shot passes.

## What I'd do differently

- Add integration tests for the MCP tools earlier (around Day 23) rather
  than relying on manual exercising during Day 24's chaos testing — the
  resilience layer (timeouts, retry-once) would have had something
  concrete to regress against from the start.
- Wire Langfuse tracing (Day 30) in from Day 21, even as a no-op stub,
  so every day's manual testing would already be visible as traces
  instead of retrofitting it at the very end of the build.
- Spend more of Day 26 on making the rate limiter and cache
  swappable for a real backend (Redis) from the start, rather than
  noting it as a "production would use X" comment — the in-memory
  version is fine for this exercise but the swap point should have been
  an actual interface, not just a comment.
