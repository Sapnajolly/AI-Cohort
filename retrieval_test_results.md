——————————# Day 10: Retrieval Engine Test Results

**Routing function:** `retrieve`
**Test questions:** 10
**Results log file:** `retrieval_test_results.md`

---

## Q1: "What is my deductible for the Silver plan?"
- Classification: structured | SQL: 3 rows | Vector: 0 | Score: good

## Q2: "Is physical therapy covered under the Silver plan?"
- Classification: unstructured | SQL: 0 | Vector: 5 chunks | Score: good
- Top chunk: "Silver plan covers PT at 80% after deductible, up to 30 visits/year."

## Q3: "What is the status of my recent claim?"
- Classification: structured | SQL: 5 rows | Vector: 0 | Score: good

## Q4: "Does my plan cover mental health treatment?"
- Classification: unstructured | SQL: 0 | Vector: 5 chunks | Score: good
- Top chunk: "Mental health services covered at same cost-sharing as medical benefits."

## Q5: "What is the monthly premium for the Gold plan?"
- Classification: structured | SQL: 3 rows | Vector: 0 | Score: good

## Q6: "Is chiropractic care covered?"
- Classification: unstructured | SQL: 0 | Vector: 5 chunks | Score: good
- Top chunk: "Chiropractic care covered up to 20 visits/year after deductible."

## Q7: "How much is my copay for specialist visits?"
- Classification: structured | SQL: 3 rows | Vector: 0 | Score: good

## Q8: "What does the Silver plan say about prior authorization?"
- Classification: both | SQL: 2 rows | Vector: 5 chunks | Score: good
- Top chunk: "Prior auth required for specialist referrals beyond 6 visits and inpatient stays."

## Q9: "What is my out-of-pocket maximum?"
- Classification: structured | SQL: 3 rows | Vector: 0 | Score: good

## Q10: "Are out-of-network providers covered for emergency care?"
- Classification: both | SQL: 2 rows | Vector: 5 chunks | Score: partial
- Top chunk: "Emergency OON care covered at in-network rates. Balance billing may apply."
- Note: SQL lacked granular OON data - needs enrichment for Day 11

---

## Score Summary

| Q | Classification | Score |
|---|---------------|-------|
| 1 | structured | good |
| 2 | unstructured | good |
| 3 | structured | good |
| 4 | unstructured | good |
| 5 | structured | good |
| 6 | unstructured | good |
| 7 | structured | good |
| 8 | both | good |
| 9 | structured | good |
| 10 | both | partial |

**Result: 9 good / 1 partial / 0 poor**

## Day 11 Baseline Notes
- SQL routing accurate for cost/plan/claim queries
- Vector retrieval precise for Silver-plan policy wording
- Hybrid routing captures richer context for complex queries
- collection.count() = 23 chunks indexed
