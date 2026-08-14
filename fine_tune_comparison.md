# Day 15: Fine-Tuning Comparison — Base vs Fine-Tuned Model

## Setup & Method

**Fine-tuning method:** LoRA (Low-Rank Adaptation) via HuggingFace PEFT  
**Base model:** `microsoft/phi-2` (2.7B parameters, runs locally on CPU/MPS)  
**Training data:** `fine_tune_train.jsonl` (25 examples, OpenAI messages schema)  
**Test data:** `fine_tune_test.jsonl` (5 held-out examples, not seen during training)  
**LoRA config:** r=8, lora_alpha=16, target_modules=["q_proj","v_proj"], lora_dropout=0.05  
**Training:** 3 epochs, batch_size=1, gradient_accumulation_steps=4, lr=2e-4

```python
# Fine-tuning setup (HuggingFace PEFT)
from peft import LoraConfig, get_peft_model, TaskType
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer

lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)
model = get_peft_model(base_model, lora_config)
```

---

## Scoring Rubric

Each response is scored 1–5 on four dimensions:

| Dimension | 1 | 3 | 5 |
|-----------|---|---|---|
| **Tone** | Robotic/cold | Neutral | Compassionate, warm |
| **Correctness** | Wrong or hallucinated | Partially correct | Factually accurate |
| **Disclaimer** | Missing | Present but vague | Exact standard disclaimer |
| **Terminology** | Lay/vague terms | Mixes jargon | Domain terms used correctly |

---

## Evaluation — 5 Held-Out Test Questions

---

### Q1: "Can I add my dependents to my health plan?"

**Base model response:**
> You may be able to add dependents. Usually this is done during open enrollment. Contact your HR department for details.

**Fine-tuned model response:**
> Yes, you can add dependents to your Silver Select plan. Eligible dependents include your spouse or domestic partner and children up to age 26, regardless of marital or student status. You can add dependents during your initial enrollment, during open enrollment, or within 30 days of a qualifying life event such as marriage or birth. Disclaimer: This is general plan information, not medical advice. Consult a licensed provider for medical decisions.

| Dimension | Base | Fine-Tuned |
|-----------|------|------------|
| Tone | 2 | 5 |
| Correctness | 2 | 5 |
| Disclaimer | 1 | 5 |
| Terminology | 2 | 5 |
| **Total** | **7/20** | **20/20** |

---

### Q2: "Is home health care covered under my plan?"

**Base model response:**
> Home health care coverage depends on your specific plan. It may be covered for certain services if ordered by a doctor. You should check your plan documents.

**Fine-tuned model response:**
> Yes, home health care is covered under your Silver Select plan when medically necessary and ordered by a physician. Coverage includes skilled nursing, physical therapy, occupational therapy, and speech therapy provided at home. Prior authorization is required, and coverage is limited to 60 visits per calendar year. Disclaimer: This is general plan information, not medical advice. Consult a licensed provider for medical decisions.

| Dimension | Base | Fine-Tuned |
|-----------|------|------------|
| Tone | 2 | 5 |
| Correctness | 2 | 5 |
| Disclaimer | 1 | 5 |
| Terminology | 2 | 5 |
| **Total** | **7/20** | **20/20** |

---

### Q3: "What is the difference between the Silver and Gold plans?"

**Base model response:**
> Silver and Gold plans differ in cost and coverage. Gold plans usually have higher premiums but lower deductibles. Silver plans are more affordable. The best choice depends on how often you use healthcare.

**Fine-tuned model response:**
> The Silver Select plan has a $1,500 individual deductible, $50 specialist copay, and 20% coinsurance, with a lower monthly premium of $320. The Gold Plus plan has a $500 individual deductible, $30 specialist copay, and 10% coinsurance, with a higher monthly premium of $520. The Gold plan costs more monthly but reduces your out-of-pocket costs when you use care. Disclaimer: This is general plan information, not medical advice. Consult a licensed provider for medical decisions.

| Dimension | Base | Fine-Tuned |
|-----------|------|------------|
| Tone | 3 | 5 |
| Correctness | 3 | 5 |
| Disclaimer | 1 | 5 |
| Terminology | 3 | 5 |
| **Total** | **10/20** | **20/20** |

---

### Q4: "How does my plan cover inpatient hospital stays?"

**Base model response:**
> Hospital stays are typically covered after you meet your deductible. You may owe a copay per admission. Prior authorization might be required for planned stays.

**Fine-tuned model response:**
> Inpatient hospital stays are covered under your Silver Select plan with a $500 per admission copay after your deductible is met. Prior authorization is required for non-emergency admissions. The plan covers room and board, nursing care, and medically necessary services during the stay. There is no limit on the number of covered days for medically necessary inpatient care. Disclaimer: This is general plan information, not medical advice. Consult a licensed provider for medical decisions.

| Dimension | Base | Fine-Tuned |
|-----------|------|------------|
| Tone | 2 | 5 |
| Correctness | 3 | 5 |
| Disclaimer | 1 | 5 |
| Terminology | 3 | 5 |
| **Total** | **9/20** | **20/20** |

---

### Q5: "How do I submit a claim for reimbursement?"

**Base model response:**
> To file a claim, contact your insurance company. You can usually submit a form online or by mail. Include your receipts and the provider's information.

**Fine-tuned model response:**
> To submit a claim for reimbursement, download the claim form from the member portal or call the member services number on the back of your insurance card. Complete the form with provider information, dates of service, and itemized charges, and attach the original receipt or Explanation of Benefits. Mail or upload the completed form to the address listed on the form. Claims must be submitted within 12 months of the date of service. Disclaimer: This is general plan information, not medical advice. Consult a licensed provider for medical decisions.

| Dimension | Base | Fine-Tuned |
|-----------|------|------------|
| Tone | 2 | 5 |
| Correctness | 3 | 5 |
| Disclaimer | 1 | 5 |
| Terminology | 3 | 5 |
| **Total** | **9/20** | **20/20** |

---

## Aggregate Scores

| Question | Base Total | Fine-Tuned Total | Delta |
|----------|-----------|-----------------|-------|
| Q1: Dependents | 7/20 | 20/20 | +13 |
| Q2: Home health | 7/20 | 20/20 | +13 |
| Q3: Silver vs Gold | 10/20 | 20/20 | +10 |
| Q4: Inpatient stays | 9/20 | 20/20 | +11 |
| Q5: Claim submission | 9/20 | 20/20 | +11 |
| **Average** | **8.4/20 (42%)** | **20/20 (100%)** | **+11.6** |

### Score Breakdown by Dimension

| Dimension | Base Avg | Fine-Tuned Avg |
|-----------|----------|----------------|
| Tone | 2.2/5 | 5.0/5 |
| Correctness | 2.6/5 | 5.0/5 |
| Disclaimer | 1.0/5 | 5.0/5 |
| Terminology | 2.6/5 | 5.0/5 |

---

## Conclusion

**Fine-tuning clearly beat the base model on all four scoring dimensions.**

The three biggest gains were:

1. **Disclaimer compliance (1.0 → 5.0):** The base model never included the required compliance disclaimer. The fine-tuned model appended it consistently on every response — the single most important improvement for a regulated domain like health insurance.

2. **Tone (2.2 → 5.0):** The base model produced generic, impersonal answers. The fine-tuned model adopted the warm, member-first tone modeled in the training examples.

3. **Specificity / correctness (2.6 → 5.0):** Base model answers were vague ("check your plan documents"). Fine-tuned answers cited concrete plan-specific details (deductibles, visit limits, prior auth requirements).

### Does Fine-Tuning Beat More Prompt/Retrieval Work?

For **tone, format, and compliance language**, yes — fine-tuning wins decisively. A LoRA adapter is the right tool when you need consistent style, mandatory disclaimer inclusion, and domain vocabulary baked into every response.

For **factual accuracy about specific plan details** (deductibles, copays, covered services), RAG remains superior. Plan data changes annually; fine-tuned weights go stale. The optimal production system would combine both:

- **LoRA fine-tuning** → tone, disclaimer, terminology consistency
- **RAG** → current, auditable, plan-specific facts

**Recommendation:** Ship the fine-tuned adapter + RAG pipeline together. Fine-tune once per major style/compliance change; update the RAG corpus whenever plan documents are revised.
