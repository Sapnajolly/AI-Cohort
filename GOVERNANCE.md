# GOVERNANCE.md — Coverage Chatbot

## Data sources used and their sensitivity

| Source | Contents | Sensitivity |
|---|---|---|
| `data/plans.csv` / `coverage.db` plans table | Plan name, tier, deductible, premium | Low — no direct member identifiers, but tied to a member's plan choice |
| `coverage.db` claims table / `MOCK_CLAIMS` | Claim ID, billed/approved amounts, status | **High (PHI-adjacent)** — claim IDs and amounts can identify a specific member's medical activity in combination with other fields |
| Knowledge base / vector store (`knowledge_base.jsonl`, Chroma) | Policy wording, enrollment/benefits text | Low — general policy text, not member-specific |
| Conversation memory (Day 20) | Chat history including plan_id, claim_id, procedures mentioned | **High** — this is where real PHI/PII would land if a member typed it in |
| Fine-tuning datasets (`fine_tune_*.jsonl`) | Synthetic Q&A pairs | Low — synthetic only, per program instructions; never real member data |

All data used throughout this program is synthetic/mock (`MOCK_COVERAGE`,
`MOCK_CLAIMS`, `MOCK_PLANS`). **No real member data has been used or
should ever be used in this repo.**

## PHI/PII fields present in this system

- `member_id` / `plan_id` (e.g. `silver_001`) — identifies a member's plan
- `claim_id` (e.g. `CLM-2024-0892`) — identifies a specific claim
- Billed/approved dollar amounts tied to a claim
- Procedure names (e.g. "physical therapy", "mental health") — combined
  with a member/plan ID, this is PHI (it reveals a member is seeking a
  specific kind of care)
- Free-text conversation turns, which could contain anything a member
  types: name, DOB, SSN, phone, email, symptoms

`redact_pii.py` targets exactly these fields (SSN, claim ID, member/plan
ID, email, phone, DOB) before any request/response is written to
application logs. It is wired into `coverage-chatbot-api/main.py`'s
`/chat` logging path so raw PHI never persists in logs, even though the
in-memory conversation (used for context) still has it during the live
request.

## Bias risks

- **Plan-tier assumptions**: the agent could implicitly treat Gold-tier
  members as "more important" or give more thorough answers than
  Silver-tier members, since Gold's mock data has fewer restrictions
  (no prior auth, lower copay). Mitigation: the system prompt and
  specialist prompts (Day 21/22) instruct the agent to answer based only
  on that member's actual plan data, never to editorialize about tiers.
- **Procedure-name bias**: if the knowledge base or fine-tuning set has
  uneven coverage of procedures (e.g. more mental-health examples than
  physical-therapy examples), the agent could answer some procedure types
  more confidently/accurately than others. Mitigation: `fine_tune_dataset.jsonl`
  and the knowledge base should be periodically audited for balance
  across procedure categories as new procedures are added.
- **Tool-selection bias from Day 21's tool descriptions**: vague or
  narrow tool descriptions can cause the agent to systematically prefer
  one tool over another for ambiguous questions. Day 21's tool-selection
  review process (comparing agent choices to a human rep) is the ongoing
  check against this.

## Accountability — who reviews chatbot outputs

- **Engineering owner (this repo's maintainer)**: responsible for the
  guardrail code (`guardrails_config.py`), redaction code
  (`redact_pii.py`), and keeping the adversarial test suite
  (`adversarial_tests.md`) current as new attack patterns are found.
- **Compliance/clinical reviewer (formal, production-only)**: any
  response that touches coverage determinations or claim outcomes with
  real financial/medical consequence needs sign-off from a compliance or
  clinical reviewer before this moves beyond a training/demo project —
  **this has not happened and this repo is not production-ready.** The
  guardrails here (regex-based prompt-injection/leakage/medical-advice
  checks) are a first pass for a learning exercise, not a substitute for
  a real PHI compliance review, a signed BAA, or a Presidio/Guardrails-AI
  grade redaction pipeline.
- **On-call/escalation**: the canned fallback message (Day 24) is the
  explicit hand-off point to a human — any tool failure routes there
  rather than guessing, and a real deployment would route that fallback
  to a live support queue.

## Production compliance note

This project uses **synthetic data only** and lightweight, regex-based
guardrails suitable for a learning exercise. Before any version of this
system could touch real member data, it would need: a formal HIPAA/PHI
compliance review, a proper PII-detection library (Presidio) instead of
hand-written regexes, encryption-at-rest for conversation memory, an
access-control/audit-log layer, and sign-off from a compliance officer —
none of which is in place here.
