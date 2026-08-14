# Day 14: Fine-Tuning Dataset Preparation Notes

## Dataset Overview

- **Total examples:** 30
- **Train split:** 25 examples (`fine_tune_train.jsonl`)
- **Test split:** 5 examples (`fine_tune_test.jsonl`)
- **Format:** OpenAI messages schema (JSONL)
- **Domain:** Health insurance coverage assistant

## Format Used

Each line in the JSONL files follows the OpenAI messages schema:

```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

The system prompt used across all examples:
> "You are a compassionate, compliant health insurance coverage assistant. Answer using only verified plan information. Always close with: 'Disclaimer: This is general plan information, not medical advice. Consult a licensed provider for medical decisions.'"

## Topics Covered (30 examples)

1. Physical therapy coverage
2. Deductible explanation (Silver plan)
3. Mental health treatment
4. Out-of-pocket maximum
5. Chiropractic care
6. Specialist copays
7. MRI prior authorization
8. Emergency room (out-of-network)
9. Monthly premium (Gold plan)
10. Telehealth coverage
11. Prescription drug coverage
12. Finding in-network providers
13. Dental care coverage
14. Out-of-network specialist costs
15. Maternity care
16. Appeals process
17. Acupuncture coverage
18. Coinsurance explanation
19. Second opinion coverage
20. Vision care
21. Preventive care (no-cost services)
22. Referrals (PPO vs HMO)
23. Copay vs. deductible difference
24. Substance use disorder treatment
25. Ambulance services
26. Adding dependents
27. Home health care
28. Silver vs. Gold plan comparison
29. Inpatient hospital stays
30. Claim submission process

## Fine-Tuning vs. Retrieval-Augmented Generation (RAG)

### When to Use Fine-Tuning

| Criterion | Fine-Tuning |
|-----------|-------------|
| **Style/tone consistency** | ✅ Excellent — model learns exact response format |
| **Compliance language** | ✅ Disclaimer always included after training |
| **Static knowledge** | ✅ Good for stable plan facts that rarely change |
| **Inference speed** | ✅ Faster at runtime (no retrieval step) |
| **Setup cost** | ❌ High — requires curated dataset, GPU hours |
| **Updatability** | ❌ Requires re-training when plan details change |

### When to Use RAG

| Criterion | RAG |
|-----------|-----|
| **Dynamic/updated info** | ✅ Excellent — retrieves latest documents |
| **Coverage breadth** | ✅ Can answer from any document in the corpus |
| **Auditability** | ✅ Source chunks are surfaced with each answer |
| **Setup cost** | ✅ Lower — just index documents |
| **Hallucination risk** | ✅ Lower — answers grounded in retrieved context |
| **Latency** | ❌ Higher — retrieval adds round-trip |
| **Tone consistency** | ❌ Varies unless system prompt is carefully tuned |

### Recommendation for This Use Case

For a **health insurance coverage assistant**, **RAG is preferred** in production because:

1. **Plan details change** — deductibles, copays, and covered services are updated annually. RAG lets you update the document corpus without retraining.
2. **Auditability** — regulators and compliance teams can trace answers back to specific policy documents.
3. **Hallucination risk is critical** — incorrect coverage information can cause patient harm or liability; grounding answers in retrieved text reduces risk.

Fine-tuning is **complementary**, not a replacement:
- Fine-tune on a curated dataset to lock in tone, compliance language (disclaimers), and response format.
- Use RAG for factual content retrieval.
- **Best practice:** RAG + fine-tuned model = consistent style + accurate facts.

## Train/Test Split Rationale

- **80/20 split** (25 train / 5 test) is standard for small datasets.
- Test examples cover: dependents, home health, Silver vs Gold comparison, inpatient stays, claim submission — diverse topics not over-represented in training.
- In production, a 90/10 split or k-fold cross-validation would be used with larger datasets.
