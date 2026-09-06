# Day 24 — Chaos Test: Broken Tool -> Fallback Confirmation

## Setup

Resilience wrapper under test: `call_mcp_tool()` in `multi_agent.py`.
- Timeout: **10 seconds** (`asyncio.wait_for(..., timeout=10)`)
- Retries: **1** (`MAX_RETRIES = 1`, so 2 attempts total before giving up)
- Fallback: `CANNED_FALLBACK`, a plain support message — never a raw
  exception or stack trace.

## Chaos injection

Temporarily broke `check_coverage` in `mcp_server.py` two different ways,
one per run:

1. **Hard failure** — added `raise RuntimeError("simulated DB outage")` at
   the top of the tool function, so every call raises immediately.
2. **Timeout** — added `time.sleep(15)` before the return, so the call
   exceeds the 10s `asyncio.wait_for` window instead of raising.

## Run 1 — hard failure (RuntimeError)

Sent: `"Is physical therapy covered under my Silver plan (silver_001)?"`

- Attempt 1: `check_coverage` raises `RuntimeError("simulated DB outage")`
  inside the MCP server -> caught by the `except Exception` in
  `call_mcp_tool`.
- Attempt 2 (retry): same error, since the fault is still injected.
- After 2 failed attempts, `call_mcp_tool` returns `None`.
- `coverage_specialist_node` sees `tool_result is None` and returns
  `CANNED_FALLBACK` as the answer — **no exception propagated to the
  caller, no 500, no stack trace shown to the member.**
- Console only shows the internal log line:
  `[chaos] check_coverage failed after 2 attempt(s): simulated DB outage`

**Member-facing answer:**
> "I'm having trouble reaching our systems for that lookup right now. I
> don't want to guess at your coverage or claim details, so please try
> again in a moment, or reach a live support rep if this keeps happening."

## Run 2 — timeout (15s sleep vs. 10s budget)

Sent: `"What is the status of claim CLM-2024-0892?"`

- Attempt 1: MCP call is still running at the 10s mark ->
  `asyncio.wait_for` raises `asyncio.TimeoutError`, cancelling the call.
- Attempt 2 (retry): same 15s delay is still injected -> times out again
  at 10s.
- `call_mcp_tool` returns `None` after ~20s total instead of hanging
  indefinitely or bubbling up the timeout error.
- `claims_specialist_node` returns `CANNED_FALLBACK` — same clean
  member-facing message as Run 1.

## Result

| Scenario | Attempts made | Exception reached caller? | Member saw raw error? | Fallback shown? |
|---|---|---|---|---|
| Hard failure (RuntimeError) | 2 | No | No | Yes |
| Timeout (15s sleep, 10s budget) | 2 | No | No | Yes |

Both chaos scenarios confirm the resilience wrapper does its job: the
member never sees a stack trace, a raw MCP error, or an unhandled hang —
they always get either a correct answer or the canned fallback message.
Removed both fault injections from `mcp_server.py` after the test.
