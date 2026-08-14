"""
Day 13: Advanced Prompting — Function Calling & Structured Outputs
Defines 4 coverage tool schemas, runs an agentic tool-execution loop,
and validates every tool response with Pydantic before returning to the LLM.
"""

import json
import sqlite3
from typing import Optional
from openai import OpenAI
from pydantic import BaseModel, Field

# --- LLM Client (Ollama local, free, no API key) ---
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL = "llama3.1"

# ---------------------------------------------------------------------------
# Pydantic response models (validate every tool return before passing to LLM)
# ---------------------------------------------------------------------------

class CoverageResult(BaseModel):
    plan_id: str
    procedure: str
    covered: bool
    requires_prior_auth: bool = False
    copay: Optional[float] = None
    notes: str = ""

class ClaimStatusResult(BaseModel):
    claim_id: str
    status: str  # e.g. "Approved", "Pending", "Denied"
    amount_billed: float
    amount_approved: Optional[float] = None
    notes: str = ""

class PlanDetailsResult(BaseModel):
    plan_id: str
    plan_name: str
    plan_type: str  # e.g. "Silver", "Gold"
    deductible: float
    out_of_pocket_max: float
    monthly_premium: float

class OutOfPocketEstimate(BaseModel):
    procedure: str
    plan_id: str
    estimated_cost: float
    deductible_remaining: float = Field(default=0.0)
    notes: str = ""

# ---------------------------------------------------------------------------
# Tool schemas (passed to OpenAI-compatible API via tools=)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_coverage",
            "description": "Check whether a medical procedure is covered under a given plan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The member's plan ID, e.g. 'silver_001'"},
                    "procedure": {"type": "string", "description": "Name of the medical procedure, e.g. 'physical therapy'"},
                },
                "required": ["plan_id", "procedure"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_claim_status",
            "description": "Retrieve the current status of a submitted insurance claim.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string", "description": "The claim ID, e.g. 'CLM-2024-0892'"},
                },
                "required": ["claim_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_plan_details",
            "description": "Get full details of a health insurance plan including deductible and premiums.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID, e.g. 'silver_001'"},
                },
                "required": ["plan_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_out_of_pocket_cost",
            "description": "Estimate the member's out-of-pocket cost for a procedure given their current deductible status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "procedure": {"type": "string", "description": "Medical procedure name"},
                    "plan_id": {"type": "string", "description": "The member's plan ID"},
                },
                "required": ["procedure", "plan_id"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Mock tool executors (replace with real DB queries in production)
# ---------------------------------------------------------------------------

MOCK_COVERAGE = {
    ("silver_001", "physical therapy"): {"covered": True, "requires_prior_auth": True, "copay": 40.0, "notes": "30 visits/year limit"},
    ("silver_001", "chiropractic care"): {"covered": True, "requires_prior_auth": False, "copay": 50.0, "notes": "20 visits/year limit"},
    ("silver_001", "mental health"): {"covered": True, "requires_prior_auth": False, "copay": 50.0, "notes": "Parity with medical"},
    ("gold_001", "physical therapy"): {"covered": True, "requires_prior_auth": False, "copay": 20.0, "notes": "Unlimited visits"},
}

MOCK_CLAIMS = {
    "CLM-2024-0892": {"status": "Approved", "amount_billed": 450.0, "amount_approved": 360.0, "notes": "Processed 2024-11-20"},
    "CLM-2024-1001": {"status": "Pending", "amount_billed": 1200.0, "amount_approved": None, "notes": "Under review"},
}

MOCK_PLANS = {
    "silver_001": {"plan_name": "Silver Select", "plan_type": "Silver", "deductible": 1500.0, "out_of_pocket_max": 7000.0, "monthly_premium": 320.0},
    "gold_001": {"plan_name": "Gold Plus", "plan_type": "Gold", "deductible": 500.0, "out_of_pocket_max": 4000.0, "monthly_premium": 520.0},
}


def check_coverage(plan_id: str, procedure: str) -> dict:
    key = (plan_id.lower(), procedure.lower())
    data = MOCK_COVERAGE.get(key, {"covered": False, "requires_prior_auth": False, "copay": None, "notes": "Procedure not found in plan"})
    result = CoverageResult(plan_id=plan_id, procedure=procedure, **data)
    return result.model_dump()


def get_claim_status(claim_id: str) -> dict:
    data = MOCK_CLAIMS.get(claim_id.upper(), {"status": "Not Found", "amount_billed": 0.0, "notes": "Claim ID not found"})
    result = ClaimStatusResult(claim_id=claim_id, **data)
    return result.model_dump()


def get_plan_details(plan_id: str) -> dict:
    data = MOCK_PLANS.get(plan_id.lower())
    if not data:
        return {"error": f"Plan {plan_id} not found"}
    result = PlanDetailsResult(plan_id=plan_id, **data)
    return result.model_dump()


def estimate_out_of_pocket_cost(procedure: str, plan_id: str) -> dict:
    plan = MOCK_PLANS.get(plan_id.lower())
    coverage = MOCK_COVERAGE.get((plan_id.lower(), procedure.lower()))
    if not plan or not coverage:
        return OutOfPocketEstimate(procedure=procedure, plan_id=plan_id, estimated_cost=0.0, notes="Data not found").model_dump()
    deductible_remaining = plan["deductible"] * 0.6  # assume 40% met
    copay = coverage.get("copay", 0.0) or 0.0
    estimated = min(copay, deductible_remaining)
    result = OutOfPocketEstimate(
        procedure=procedure,
        plan_id=plan_id,
        estimated_cost=round(estimated, 2),
        deductible_remaining=round(deductible_remaining, 2),
        notes=f"Estimate based on 40% deductible met; copay={copay}",
    )
    return result.model_dump()


TOOL_EXECUTORS = {
    "check_coverage": lambda args: check_coverage(**args),
    "get_claim_status": lambda args: get_claim_status(**args),
    "get_plan_details": lambda args: get_plan_details(**args),
    "estimate_out_of_pocket_cost": lambda args: estimate_out_of_pocket_cost(**args),
}

# ---------------------------------------------------------------------------
# Tool-execution loop
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a health insurance coverage assistant.
Use the available tools to look up accurate plan and claim information.
Do NOT make up numbers — always call the appropriate tool.
After receiving tool results, give a clear, empathetic answer to the member.
"""


def chat_with_tools(user_question: str) -> dict:
    """Single-turn agent: LLM decides whether to call a tool, executes if so, returns final answer."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_question},
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
    )
    msg = response.choices[0].message
    tool_calls_log = []

    if msg.tool_calls:
        messages.append(msg)
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)
            executor = TOOL_EXECUTORS.get(fn_name)
            result = executor(fn_args) if executor else {"error": "Unknown tool"}
            tool_calls_log.append({"tool": fn_name, "args": fn_args, "result": result})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })
        final = client.chat.completions.create(model=MODEL, messages=messages)
        answer = final.choices[0].message.content.strip()
    else:
        answer = msg.content.strip()

    return {
        "question": user_question,
        "tool_calls": tool_calls_log,
        "answer": answer,
    }


# ---------------------------------------------------------------------------
# Test harness — 5 tool questions + 1 no-tool control
# ---------------------------------------------------------------------------

TEST_QUESTIONS = [
    # Tool questions (expect tool invocation)
    "Is physical therapy covered under my Silver plan (silver_001)?",
    "What is the status of claim CLM-2024-0892?",
    "Can you give me the full details of the silver_001 plan?",
    "How much will I pay out of pocket for chiropractic care under silver_001?",
    "Is mental health treatment covered under my silver_001 plan?",
    # No-tool control question (expect direct answer, no tool call)
    "What is today's date?",
]

if __name__ == "__main__":
    print("=== Day 13: Tool-Calling Chatbot Test ===\n")
    for i, q in enumerate(TEST_QUESTIONS, 1):
        result = chat_with_tools(q)
        tag = "[NO-TOOL CONTROL]" if i == 6 else f"[Tool: {result['tool_calls'][0]['tool'] if result['tool_calls'] else 'NONE'}]"
        print(f"Q{i} {tag}: {q}")
        print(f"  Answer: {result['answer'][:200]}")
        print()
