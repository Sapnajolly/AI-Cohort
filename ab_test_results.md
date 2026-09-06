# Day 26 — A/B Test Results: Variant A (structured-only) vs. Variant B (+ vector policy context)

Scored per `experiment_design.md`'s rubric (1-5 groundedness). Token
counts are prompt+completion tokens per answer, via
`token_utils.count_tokens`.

| # | Question | A score | A tokens | B score | B tokens | Notes |
|---|---|---|---|---|---|---|
| 1 | Is physical therapy covered under silver_001? | 5 | 42 | 5 | 71 | Structured `notes` field already states the 30-visit limit; vector context adds nothing new here. |
| 2 | Status of claim CLM-2024-0892? | 5 | 38 | 5 | 65 | Claims question — vector policy context is irrelevant to claim status either way. |
| 3 | Full plan details for silver_001? | 5 | 40 | 5 | 68 | Plan-detail fields are fully structured; no policy text needed. |
| 4 | Is mental health covered under silver_001? | 5 | 41 | 5 | 70 | `notes: "Parity with medical"` already grounds the answer. |
| 5 | Gold_001 — PT covered? Prior auth? | 5 | 43 | 5 | 72 | `requires_prior_auth` flag + notes cover it fully. |
| 6 | Status of claim CLM-2024-1001? | 5 | 39 | 5 | 66 | Claims-only; no coverage/policy angle. |
| 7 | Is chiropractic care covered under silver_001? | 5 | 40 | 5 | 69 | 20-visit limit already in structured `notes`. |
| 8 | Deductible for gold_001? | 5 | 37 | 5 | 64 | Plan-detail field, structured. |
| 9 | Do I need a referral for PT under silver_001? | 2 | 35 | 5 | 88 | **No referral field in the structured schema at all** — Variant A can only guess or say "not sure"; Variant B's policy text actually answers it. |
| 10 | What counts as "in-network" for silver_001? | 2 | 33 | 4 | 92 | Definitional question the structured schema was never designed to answer; vector context helps but the chunk wasn't a perfect match. |
| 11 | What happens if I exceed my 30-visit PT limit? | 3 | 44 | 5 | 95 | A has the number (30) but not the consequence; B's policy chunk explains what happens after the limit. |
| 12 | Is claim CLM-2024-0892 fully or partially paid? | 5 | 40 | 5 | 67 | Structured `amount_billed`/`amount_approved` answer this directly. |
| 13 | Premium difference: silver_001 vs gold_001? | 5 | 46 | 5 | 74 | Two structured plan-detail lookups, no policy text needed. |
| 14 | Does silver_001 cover out-of-network mental health? | 2 | 36 | 4 | 90 | No in/out-of-network field in the structured schema; vector context partially covers it. |
| 15 | What's the appeals process for a denied claim? | 1 | 34 | 4 | 93 | Zero structured data on appeals — Variant A cannot answer this at all; Variant B's policy text at least partially can. |

## Aggregate

- **Mean groundedness — Variant A: 4.0** (60 / 15)
- **Mean groundedness — Variant B: 4.8** (72 / 15)
- **Gap: 0.8** — below the decision rule's 1.0-point threshold.
- **Mean tokens/answer — Variant A: 39.5** vs. **Variant B: 76.9** (~95% more tokens per answer for Variant B, from including retrieved policy chunks).

## Conclusion

**Per the pre-registered decision rule (gap < 1.0), Variant A stays the
default** for `check_coverage`. The two variants tie on every question
the structured schema was actually designed to answer (copay, prior-auth
flag, visit limits, claim amounts, plan financials) — 10 of 15 questions
scored 5/5 on both variants, and the vector-lookup context added ~95%
more tokens per answer for no quality gain there.

The gap is entirely concentrated in 5 questions (#9-11, #14-15) that ask
about things the structured mock schema simply doesn't model: referral
requirements, in/out-of-network rules, exceeding a visit limit, and
appeals. On those specific question types, Variant B is clearly better
(mean 4.4 vs. 2.4) — a real finding, just not one that clears the bar to
flip the *default* path for every question given the added cost.

**Recommendation:** keep Variant A (structured-only) as the default
`check_coverage` path, and consider a smarter router that calls Variant
B's vector-augmented path only when the question matches referral/
network/appeals-style keywords, rather than paying the token cost on
every call. That's a natural Day 27 evaluation-framework follow-up
rather than a blanket default switch today.
