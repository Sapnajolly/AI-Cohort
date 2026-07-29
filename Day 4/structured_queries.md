# Structured Queries — Coverage Chatbot (Day 4)

Five working SQL queries against `coverage.db`, each mapped to a realistic
question a member might ask the chatbot. All data is synthetic — no real
member PHI. Run `python3 ingest.py` first to (re)build `coverage.db` from
`data/plans.csv` and `data/claims.csv`.

---

## Q1 — "What's my deductible and out-of-pocket max?"

Simple `SELECT ... WHERE` lookup on the plans table.

```sql
SELECT plan_id, plan_name, plan_type, deductible, out_of_pocket_max,
       copay_primary_care, copay_specialist, coinsurance_pct
FROM plans
WHERE plan_id = 'PLN-003';
```

**Sample result:**

| plan_id | plan_name | plan_type | deductible | out_of_pocket_max | copay_primary_care | copay_specialist | coinsurance_pct |
|---|---|---|---|---|---|---|---|
| PLN-003 | Gold Preferred PPO | PPO | 1500 | 5000 | 15.0 | 40.0 | 20 |

---

## Q2 — "What are all my claims and their status?"

Member-scoped claim history, ordered chronologically.

```sql
SELECT claim_id, service_date, service_type, provider_name,
       claim_status, billed_amount, paid_amount
FROM claims
WHERE member_id = 'MBR-1021'
ORDER BY service_date;
```

**Sample result:**

| claim_id | service_date | service_type | provider_name | claim_status | billed_amount | paid_amount |
|---|---|---|---|---|---|---|
| CLM-00049 | 2026-01-24 | Imaging | Downtown Pharmacy | Paid | 3445.55 | 1703.16 |
| CLM-00287 | 2026-01-31 | Specialist | Downtown Pharmacy | Paid | 1036.27 | 318.72 |
| CLM-00264 | 2026-03-05 | Imaging | Lakeside Specialists | Paid | 3007.97 | 1267.27 |
| CLM-00080 | 2026-06-05 | Primary Care | St. Elena Hospital ER | Denied | 2521.91 | 0.0 |
| CLM-00017 | 2026-07-14 | Lab | Northgate Family Clinic | Paid | 2258.39 | 1104.58 |

---

## Q3 — "How much has my plan paid out, broken down by service type?"

`JOIN` + `GROUP BY` aggregation across plans and claims.

```sql
SELECT p.plan_name, c.service_type,
       COUNT(*) AS claim_count,
       ROUND(SUM(c.paid_amount), 2) AS total_paid
FROM claims c
JOIN plans p ON c.plan_id = p.plan_id
WHERE c.plan_id = 'PLN-002'
GROUP BY c.service_type
ORDER BY total_paid DESC;
```

**Sample result:**

| plan_name | service_type | claim_count | total_paid |
|---|---|---|---|
| Silver Standard PPO | Urgent Care | 9 | 8652.90 |
| Silver Standard PPO | Pharmacy | 9 | 7175.56 |
| Silver Standard PPO | Specialist | 7 | 5275.60 |
| Silver Standard PPO | Imaging | 7 | 5038.81 |
| Silver Standard PPO | Lab | 8 | 4894.87 |
| Silver Standard PPO | Emergency Room | 4 | 1130.79 |
| Silver Standard PPO | Primary Care | 5 | 304.53 |

---

## Q4 — "Which of my claims were denied?"

Filtered lookup a chatbot would use to explain a bill discrepancy.

```sql
SELECT claim_id, service_date, provider_name, service_type,
       billed_amount, diagnosis_code
FROM claims
WHERE claim_status = 'Denied' AND member_id = 'MBR-1089'
ORDER BY service_date;
```

**Sample result:**

| claim_id | service_date | provider_name | service_type | billed_amount | diagnosis_code |
|---|---|---|---|---|---|
| CLM-00133 | 2026-01-30 | Downtown Pharmacy | Imaging | 3213.63 | E11.9 |
| CLM-00234 | 2026-05-16 | St. Elena Hospital ER | Specialist | 574.13 | E11.9 |

---

## Q5 — "Which plans tend to have the most expensive claims?"

Nested query: subquery computes per-plan averages, outer query filters
against the overall average billed amount.

```sql
SELECT plan_id, plan_name,
       ROUND(avg_cost, 2) AS avg_billed_amount
FROM (
    SELECT p.plan_id, p.plan_name, AVG(c.billed_amount) AS avg_cost
    FROM claims c
    JOIN plans p ON c.plan_id = p.plan_id
    GROUP BY p.plan_id, p.plan_name
) sub
WHERE avg_cost > (SELECT AVG(billed_amount) FROM claims)
ORDER BY avg_billed_amount DESC;
```

**Sample result:**

| plan_id | plan_name | avg_billed_amount |
|---|---|---|
| PLN-008 | Gold Choice HMO | 2556.68 |
| PLN-006 | Silver Plus PPO | 2223.98 |

---

## Cleaning notes (pandas → SQLite)

Applied in `ingest.py` before loading `coverage.db`:

- **Dedupe**: exact duplicate rows dropped, then duplicate `plan_id` /
  `claim_id` values collapsed (`keep="first"`).
- **Type coercion**: currency columns (`monthly_premium`, `deductible`,
  `billed_amount`, etc.) arrive as mixed strings (`"$1,234.56"`, `"972.44"`,
  `"invalid"`) and are stripped/coerced to numeric, with unparseable values
  becoming `NaN` before being filled.
- **Mixed date formats**: `service_date` in the raw CSV mixes `YYYY-MM-DD`,
  `MM/DD/YYYY`, and `DD-Mon-YYYY`; all are normalized to `YYYY-MM-DD`.
- **Nulls**: missing `paid_amount` → `0.0`; missing `provider_name` →
  `"Unknown Provider"`; missing `diagnosis_code` → `"UNSPECIFIED"`; missing
  copay fields on catastrophic plans → `0`.
