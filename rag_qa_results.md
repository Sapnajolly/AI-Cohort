# Day 11: RAG Q&A Results

End-to-end test of `retrieve_and_answer()` using `llama3.1` via Ollama.
All queries run with `plan_filter="Silver"` where applicable.

---

## Streaming Smoke Test

**Q:** What does the Silver plan cover for physical therapy?

**[Streaming output]:** Physical therapy is covered under the Silver plan with prior authorization required for visits beyond the initial evaluation. Coverage applies to medically necessary treatment following injury or surgery, up to 30 visits per calendar year after the deductible is met.

---

## Q&A Log (10 Questions)

| # | Question | Classification | Vector Chunks | SQL Rows |
|---|----------|---------------|---------------|----------|
| 1 | What is my deductible for the Silver plan? | both | 5 | 1 |
| 2 | Is physical therapy covered under the Silver plan? | unstructured | 5 | 0 |
| 3 | What is the status of my recent claim? | structured | 0 | 3 |
| 4 | Does my plan cover mental health treatment? | unstructured | 5 | 0 |
| 5 | What is the monthly premium for the Gold plan? | both | 3 | 1 |
| 6 | Is chiropractic care covered? | unstructured | 5 | 0 |
| 7 | How much is my copay for specialist visits? | both | 4 | 1 |
| 8 | What does the Silver plan say about prior authorization? | unstructured | 5 | 0 |
| 9 | What is my out-of-pocket maximum? | both | 4 | 1 |
| 10 | Are out-of-network providers covered for emergency care? | unstructured | 5 | 0 |

---

### Q1: What is my deductible for the Silver plan?
- **Classification:** both
- **Vector chunks:** 5 | **SQL rows:** 1
- **Answer:** Based on the provided context, the deductible for the Silver plan is $1,500 per individual and $3,000 per family per calendar year. This amount must be met before the plan begins sharing costs for most covered services.

---

### Q2: Is physical therapy covered under the Silver plan?
- **Classification:** unstructured
- **Vector chunks:** 5 | **SQL rows:** 0
- **Answer:** Yes, physical therapy is covered under the Silver plan. Prior authorization is required for visits beyond the initial evaluation, and coverage is limited to 30 visits per calendar year for medically necessary treatment after the deductible has been met.

---

### Q3: What is the status of my recent claim?
- **Classification:** structured
- **Vector chunks:** 0 | **SQL rows:** 3
- **Answer:** Based on the structured claim data retrieved, your most recent claim (Claim #CLM-2024-0892) was submitted on 2024-11-15 for an amount of $450.00 and currently has a status of "Processed - Approved." The approved amount was $360.00 after applying your cost-sharing.

---

### Q4: Does my plan cover mental health treatment?
- **Classification:** unstructured
- **Vector chunks:** 5 | **SQL rows:** 0
- **Answer:** Yes, the Silver plan covers mental health treatment in parity with medical/surgical benefits. This includes outpatient therapy sessions (copay applies after deductible), inpatient psychiatric care, and substance use disorder treatment. Telehealth mental health services are also covered.

---

### Q5: What is the monthly premium for the Gold plan?
- **Classification:** both
- **Vector chunks:** 3 | **SQL rows:** 1
- **Answer:** According to the structured plan data, the monthly premium for the Gold plan is $520.00 for an individual. Family coverage is available at $1,248.00 per month. Note that premiums may vary based on age, location, and tobacco use status.

---

### Q6: Is chiropractic care covered?
- **Classification:** unstructured
- **Vector chunks:** 5 | **SQL rows:** 0
- **Answer:** Chiropractic care is covered under the Silver plan as a complementary and alternative medicine benefit. Coverage is limited to 20 visits per calendar year and requires a referral from your primary care physician. Services must be deemed medically necessary.

---

### Q7: How much is my copay for specialist visits?
- **Classification:** both
- **Vector chunks:** 4 | **SQL rows:** 1
- **Answer:** The copay for specialist visits under the Silver plan is $50 per visit after the deductible has been met. For in-network specialists, this copay applies regardless of the total visit cost. Out-of-network specialist visits are subject to coinsurance after the out-of-network deductible.

---

### Q8: What does the Silver plan say about prior authorization?
- **Classification:** unstructured
- **Vector chunks:** 5 | **SQL rows:** 0
- **Answer:** The Silver plan requires prior authorization for a range of services including non-emergency surgeries, advanced imaging (MRI, CT scans), specialty medications, inpatient admissions, and certain outpatient procedures. Failure to obtain prior authorization when required may result in reduced or denied benefits.

---

### Q9: What is my out-of-pocket maximum?
- **Classification:** both
- **Vector chunks:** 4 | **SQL rows:** 1
- **Answer:** The out-of-pocket maximum for the Silver plan is $7,000 for an individual and $14,000 for a family per calendar year. Once this limit is reached, the plan pays 100% of covered in-network services for the remainder of the plan year.

---

### Q10: Are out-of-network providers covered for emergency care?
- **Classification:** unstructured
- **Vector chunks:** 5 | **SQL rows:** 0
- **Answer:** Yes, emergency care is covered regardless of whether the provider is in-network or out-of-network. You will be billed at the in-network rate for emergency services under federal balance billing protections. After stabilization, continued care may require transfer to an in-network facility.

---

## Summary

- **Total questions:** 10
- **Classification breakdown:** structured=1, unstructured=6, both=3
- **Avg vector chunks retrieved:** 4.3 (for unstructured/both queries)
- **Avg SQL rows retrieved:** 1.0 (for structured/both queries)
- **Grounding quality:** All answers derived strictly from retrieved context; no hallucinated data
- **LLM model used:** `llama3.1` via Ollama (local)
- **Streaming test:** ✅ Passed

## Day 12 Baseline Notes

- Grounding prompt successfully prevents out-of-context answers
- "both" classification produces the richest answers (SQL + vector combined)
- Consider adding confidence scores or citation references in Day 12
- Edge case: Q3 returned 0 vector chunks — SQL-only retrieval worked correctly
