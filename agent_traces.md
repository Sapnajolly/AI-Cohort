# Day 21 — ReAct Agent Traces

`langchain_agent.py` run with `verbose=True` against the local Ollama
`llama3.1` model. Tools available to the agent: `check_coverage`,
`get_claim_status`, `get_plan_details` (wrapped from Day 13's
`tool_calling_chatbot.py`).

---

## Q1 — "Is physical therapy covered under my Silver plan (silver_001)? What would my copay be?"

```
Thought: The member is asking whether a specific procedure is covered under a
specific plan and what the copay is. That's exactly what check_coverage is for.
Action: check_coverage
Action Input: silver_001, physical therapy
Observation: {'plan_id': 'silver_001', 'procedure': 'physical therapy', 'covered': True,
'requires_prior_auth': True, 'copay': 40.0, 'notes': '30 visits/year limit'}
Thought: I now know the final answer
Final Answer: Yes, physical therapy is covered under your Silver plan (silver_001).
Your copay is $40 per visit, up to 30 visits per year. Note that prior
authorization is required before starting treatment.
```

**Tool selection review:** Correct — a human coverage rep would pull up the
same coverage lookup rather than guessing. Single tool call, no wasted steps.

---

## Q2 — "What is the status of claim CLM-2024-0892, and how much was approved?"

```
Thought: This is a claim-status question, not a coverage or plan question, so
get_claim_status is the right tool.
Action: get_claim_status
Action Input: CLM-2024-0892
Observation: {'claim_id': 'CLM-2024-0892', 'status': 'Approved', 'amount_billed': 450.0,
'amount_approved': 360.0, 'notes': 'Processed 2024-11-20'}
Thought: I now know the final answer
Final Answer: Claim CLM-2024-0892 was Approved. Of the $450.00 billed, $360.00 was
approved. It was processed on 2024-11-20.
```

**Tool selection review:** Correct — matches what a rep would do first when
given a claim number: look up its status before explaining anything else.

---

## Q3 — "Can you give me the full details of the silver_001 plan, including the deductible?"

```
Thought: The member wants overall plan details (deductible, premium, etc.),
not a specific procedure's coverage, so get_plan_details is the right call.
Action: get_plan_details
Action Input: silver_001
Observation: {'plan_id': 'silver_001', 'plan_name': 'Silver Select', 'plan_type': 'Silver',
'deductible': 1500.0, 'out_of_pocket_max': 7000.0, 'monthly_premium': 320.0}
Thought: I now know the final answer
Final Answer: Your silver_001 plan is "Silver Select" (Silver tier). Your annual
deductible is $1,500, your out-of-pocket max is $7,000, and your monthly
premium is $320.
```

**Tool selection review:** Correct — a rep would open the plan summary, not
a coverage rule, since the question is about the plan itself.

---

## Q4 — "Is mental health treatment covered under my silver_001 plan?"

```
Thought: Coverage question for a specific procedure/service under a specific
plan -> check_coverage.
Action: check_coverage
Action Input: silver_001, mental health
Observation: {'plan_id': 'silver_001', 'procedure': 'mental health', 'covered': True,
'requires_prior_auth': False, 'copay': 50.0, 'notes': 'Parity with medical'}
Thought: I now know the final answer
Final Answer: Yes, mental health treatment is covered under your silver_001
plan, with a $50 copay and no prior authorization needed. Coverage is at
parity with your medical benefits.
```

**Tool selection review:** Correct, and a good example of tool-selection
quality — the agent didn't ask a clarifying question or hallucinate parity
rules, it pulled the real coverage record.

---

## Q5 — "I'm on the gold_001 plan — is physical therapy covered, and do I need prior authorization?"

```
Thought: This is a coverage + prior-auth question for a named plan and
procedure -> check_coverage.
Action: check_coverage
Action Input: gold_001, physical therapy
Observation: {'plan_id': 'gold_001', 'procedure': 'physical therapy', 'covered': True,
'requires_prior_auth': False, 'copay': 20.0, 'notes': 'Unlimited visits'}
Thought: I now know the final answer
Final Answer: Yes, physical therapy is covered under your gold_001 plan, with
a $20 copay and unlimited visits. No prior authorization is needed.
```

**Tool selection review:** Correct. Also a useful contrast case: same
procedure as Q1 but a different plan (Gold vs. Silver) returns a different
prior-auth requirement and copay — the agent picked the tool correctly
rather than reusing the Q1 answer from context.

---

## Overall tool-selection review

Across all 5 questions the agent picked the single correct tool on the first
try — no retries, no wrong-tool detours, no unnecessary multi-tool chains.
That matches how a human coverage-support rep would triage these requests:
coverage/copay questions go to the coverage lookup, claim questions go to
claims status, and plan-level questions go to the plan summary. The
tool `description` strings (not just the `name`) were what made this
reliable — vague descriptions in an earlier draft caused the agent to
occasionally call `get_plan_details` for a coverage question, which is why
each description above spells out both *what* the tool returns and *when*
to use it.
