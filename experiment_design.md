# Day 26 — A/B Experiment Design (one page)

## Question

Does adding the policy-wording context from `vector_lookup` (Variant B)
produce noticeably better coverage answers than the plain structured
lookup alone (Variant A) — enough to justify the extra tokens/cost of the
vector call on every coverage question?

## Variants

- **Variant A (control)** — Day 21's ReAct agent: `check_coverage` /
  `get_claim_status` / `get_plan_details` only, no vector context.
- **Variant B (treatment)** — Day 23's MCP `check_coverage`, which adds
  `retrieval_engine.vector_lookup` policy-wording chunks alongside the
  structured result.

## Hypothesis

H1: Variant B's answers score higher on **groundedness/completeness**
(does the answer cite the relevant policy condition, e.g. visit limits or
prior-auth wording, not just the copay number) than Variant A, because it
has the underlying policy text available, not just the structured fields.

Null hypothesis (H0): there is no meaningful difference in answer quality
between A and B for this tool set — the structured fields alone are
already sufficient for members' actual questions.

## Metric

- **Primary metric:** groundedness score, 1-5, scored by a human rubric:
  1 = wrong/contradicts data, 3 = correct but missing relevant policy
  detail (e.g. omits the visit limit), 5 = correct and cites the specific
  policy condition that matters for the member's question.
- **Secondary metric:** prompt+completion token count per answer (from
  `token_utils.count_tokens`), to weigh quality gain against the added
  cost of the vector-lookup context.

## Sample size

**15 questions**, drawn from the same coverage/claims mix used in Day 21
and Day 22 (a mix of "is X covered", "claim status", "plan details", so
both structured-only and policy-wording-relevant questions are
represented). 15 is small for statistical significance but is the
program's target sample size for a fast, directional read — the decision
rule below is set to require a clear, not marginal, gap given that size.

## Decision rule

- If Variant B's mean groundedness score is **≥ 1.0 point higher** than
  Variant A's mean (on the 1-5 scale) across the 15 questions, adopt
  Variant B as the default `check_coverage` path.
- If the gap is **less than 1.0 point**, keep Variant A (the cheaper,
  lower-token path) as the default, since the added vector-lookup cost
  isn't justified by a marginal quality gain.
- Token/cost delta is reported alongside the decision either way, so a
  future re-run with more questions can revisit the threshold.

## Bias controls

- Same 15 questions run through both variants, same order, same session
  reset between variants (no shared conversation memory contaminating
  scores).
- Groundedness scored against the same MOCK_COVERAGE/MOCK_CLAIMS/policy
  data both variants read from, so no variant has access to information
  the other lacks except the vector-lookup context itself.
