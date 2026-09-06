# Day 22 — Multi-Agent vs. Day 21 Single-Agent Comparison

`multi_agent.py` splits the Day 21 ReAct agent into three roles wired with
LangGraph: a **Router** that classifies each question, a **Coverage
Specialist** (owns `check_coverage` + `get_plan_details`), and a **Claims
Specialist** (owns `get_claim_status`).

## Routing results on the same 5 test questions as Day 21

| # | Question | Router decision | Specialist that answered |
|---|----------|------------------|---------------------------|
| 1 | Is physical therapy covered under Silver (silver_001)? Copay? | `coverage` | Coverage Specialist |
| 2 | Status of claim CLM-2024-0892, amount approved? | `claims` | Claims Specialist |
| 3 | Full details of silver_001 plan, including deductible? | `coverage` | Coverage Specialist |
| 4 | Is mental health covered under silver_001? | `coverage` | Coverage Specialist |
| 5 | Gold_001 — is physical therapy covered, prior auth needed? | `coverage` | Coverage Specialist |

All 5 routing decisions matched the Day 21 single-agent's tool choices
exactly (4 coverage-tool calls, 1 claims-tool call) — same underlying
tools, same correct answers, just reached through a router hop instead of
one agent reasoning end-to-end.

## Single-agent (Day 21) vs. multi-agent (Day 22)

Day 21's single ReAct agent already gets all 5 questions right in one
Thought → Action → Observation loop, with three tools available to it.
Day 22 reaches the identical answers, but adds a routing step and splits
the tool ownership across two specialists.

For this coverage-chatbot domain specifically, multi-agent is **not**
worth the added complexity yet: there are only three closely related
tools, all under one coherent domain (member support), and a single
well-described tool set is enough for the agent to pick correctly every
time (see Day 21's tool-selection review — 5/5 correct, zero wrong-tool
detours). Splitting into Router + 2 Specialists adds an extra LLM call per
question (the router classification) and a second place code has to be
kept in sync (which specialist owns which tool) without improving
accuracy or answer quality.

## When multi-agent orchestration is actually worth it

Multi-agent starts to pay off once:

- **The domains genuinely diverge** — e.g. a coverage/claims specialist
  next to a completely different domain like appointment scheduling or
  billing disputes, each with its own tools, its own tone, and its own
  escalation rules that would bloat a single system prompt.
- **The tool count grows past what one agent can reliably choose among**
  — a single ReAct agent's tool-selection accuracy degrades as the tool
  list grows and descriptions start overlapping; splitting into
  specialists with a smaller, more distinct toolset per agent keeps each
  one's choices unambiguous.
- **Different steps need different models or cost/latency budgets** — a
  cheap/fast router model plus a stronger model only for the specialist
  that actually needs deeper reasoning (e.g. a claims-appeal specialist
  drafting a written appeal vs. a coverage lookup that's really just a
  dictionary read).
- **Work can run in parallel** — e.g. a "pull claim status" specialist and
  a "check plan coverage" specialist both need to run to answer one
  compound question ("is my pending claim's procedure even covered under
  my plan?"), where a graph can fan out and merge results instead of one
  agent doing everything sequentially.

None of those conditions hold for this 3-tool coverage/claims assistant
yet — it's a good exercise in wiring a Router + specialists, but the
Day 21 single-agent is the simpler, equally correct choice for this
specific mission. Multi-agent becomes worth it here once real domains
(scheduling, billing disputes, provider search, etc.) get added alongside
coverage and claims.
