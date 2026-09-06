# v2 Roadmap

Prioritized next steps for this chatbot beyond the 31-day build, ordered
by what should happen before anything else (compliance) down to
longer-horizon feature work.

## 0. Compliance / legal review — before any real member data (blocking)

This is called out explicitly because it blocks everything else below
touching real PHI/PII: per `GOVERNANCE.md`'s Production Compliance Note,
this system has not gone through a legal/compliance review and must not
be pointed at real member data until it has. Specifically, before any
production rollout with real members:

- HIPAA/PHI handling review of the redaction layer (`redact_pii.py`) —
  today it's a regex-based best-effort filter validated against a fixed
  test suite, not a certified PHI de-identification pipeline.
- Data retention policy for the `conversations` and `token_usage` SQLite
  tables (how long chat history and usage logs are kept, and member
  right-to-deletion handling).
- Review of what gets sent to Langfuse (a third-party service) — full
  prompts/responses are traced today; a compliance pass needs to decide
  what, if anything, must be redacted before it leaves the environment.
- BAA (Business Associate Agreement) coverage for every third-party
  service in the path (LLM provider, Langfuse) before real PHI touches
  them.

## 1. High priority (next few sprints)

- **Swap in-memory rate limiting and caching for Redis** — the current
  per-process `dict`/`deque` implementation (Day 26) doesn't survive a
  restart and isn't shared across replicas, which matters as soon as
  `kubectl scale` runs more than one backend pod in front of real
  traffic.
- **Real LLM integration** — `generate_llm_tokens()` is currently a
  placeholder echo function; swapping in an actual model call is the
  highest-value change, and should happen alongside the guardrails and
  token-governance layers already built around it.
- **Redis- or DB-backed session store** for conversation history instead
  of local SQLite, so the backend can run multiple replicas without a
  shared-file-access problem.
- **Automated regression suite for the guardrails and PII redaction**
  (turn the Day 25 adversarial test log into actual `pytest` assertions
  that run in CI) so a future prompt or regex change can't silently
  reopen a jailbreak path.

## 2. Medium priority

- **Expand the vector-augmented path beyond referral/network/appeals
  questions** — Day 26's A/B test found the vector-augmented variant
  only clearly wins on that question category; broadening it further
  needs its own eval, not just enabling it everywhere.
- **CI/CD pipeline** — build/push images on merge, run the RAGAS eval
  and guardrail regression suite as gates, then `kubectl set image` +
  `rollout status` automatically instead of the manual Day 29 process.
- **Structured alerting from the Day 30 alert sketch** — wire the error
  rate / p95 latency / daily cost ceiling thresholds into an actual
  alerting tool (e.g. Langfuse alerts or a Prometheus/Grafana stack)
  instead of leaving them as a documented design.
- **Multi-language support** for member questions, given a health plan
  membership base is rarely English-only.

## 3. Longer-term / exploratory

- **Proactive notifications** — e.g. "your claim CLM-... was just
  approved" pushed to the member instead of only answering when asked.
- **Voice/IVR front-end** on top of the same backend, reusing the
  Coverage/Claims specialist routing.
- **Personalized plan recommendations** during open enrollment, built
  on top of the existing structured plan data — this would need its own
  compliance review (it edges into advice-giving) before scoping further.
