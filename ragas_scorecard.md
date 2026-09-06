# Day 27 — RAGAS Evaluation Scorecard

Pipeline under test: `rag_chatbot.retrieve_and_answer` (Day 11), backed by
`retrieval_engine.retrieve` (Day 10's structured/vector router). Eval set:
`ragas_eval_set.jsonl` (20 question / ideal-answer pairs covering
deductibles, coverage, exclusions-adjacent prior-auth rules, claims, and
plan comparisons). Run with `ragas_run.py`.

## Baseline scores (before fix)

| Metric | Score |
|---|---|
| Faithfulness | 0.93 |
| Answer Relevancy | 0.89 |
| Context Precision | **0.72** |
| Context Recall | 0.78 |

## Weakest metric: Context Precision (0.72)

## Hypothesis

`retrieval_engine.sql_lookup()` classifies most of this eval set's
questions (deductible, premium, out-of-pocket max, claim status) as
`"structured"` and runs:

```sql
SELECT * FROM plans WHERE plan_name LIKE '%Silver%' OR plan_name LIKE '%Gold%' OR plan_name LIKE '%Bronze%' LIMIT 5
```

This query ignores which plan the question was actually about — asking
"What is the deductible for the Silver plan?" still pulls back the Gold
*and* Bronze rows alongside Silver's, because the `LIKE` clause matches
all three tiers unconditionally. Those extra rows get passed into
`rag_chatbot.generate_answer()`'s context and, via `ragas_run.py`, into
RAGAS's `contexts` list — so half or more of the retrieved "context" for
a single-plan question is about plans the question never asked about.
That's exactly what context precision penalizes: relevant content
diluted by irrelevant retrieved content.

## Fix applied

Changed `sql_lookup()` to extract the plan tier mentioned in the question
(Silver/Gold/Bronze) and filter to just that plan when one is named,
falling back to the original multi-tier query only when the question is
genuinely comparative ("silver vs gold", "which plan is cheaper", etc.):

```python
def sql_lookup(question: str) -> list[dict]:
    ...
    q = question.lower()
    mentioned_tiers = [t for t in ("silver", "gold", "bronze") if t in q]

    if "deductible" in q or "premium" in q or "plan" in q or "copay" in q:
        if mentioned_tiers and not any(w in q for w in ("vs", "versus", "compare", "which plan")):
            like_clause = " OR ".join(f"plan_name LIKE '%{t.capitalize()}%'" for t in mentioned_tiers)
            cursor.execute(f"SELECT * FROM plans WHERE {like_clause} LIMIT 5")
        else:
            cursor.execute(
                "SELECT * FROM plans WHERE plan_name LIKE '%Silver%' OR plan_name LIKE '%Gold%' OR plan_name LIKE '%Bronze%' LIMIT 5"
            )
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
    ...
```

Single-plan questions (14 of the 20 in this eval set) now retrieve only
the row(s) for the plan actually named; the 2 genuinely comparative
questions ("which plan has the lower premium/deductible") still pull
both tiers on purpose.

## Re-run scores (after fix)

| Metric | Baseline | After fix | Delta |
|---|---|---|---|
| Faithfulness | 0.93 | 0.94 | +0.01 |
| Answer Relevancy | 0.89 | 0.90 | +0.01 |
| **Context Precision** | **0.72** | **0.91** | **+0.19** |
| Context Recall | 0.78 | 0.80 | +0.02 |

## Conclusion

The fix targeted exactly the mechanism identified in the hypothesis —
irrelevant multi-tier rows diluting context for single-plan questions —
and context precision moved the most (+0.19), with faithfulness/relevancy
essentially unchanged (as expected, since the *generated answers* for
single-plan questions were already correct; only the surrounding context
was noisy) and a smaller context recall gain (+0.02) from the comparative
questions still working correctly. Context precision remains the metric
to watch next: the comparative-question branch could still be made
smarter (e.g. only returning the two tiers actually named instead of all
three) rather than always falling back to the full three-tier query.
