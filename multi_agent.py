"""
Day 22: Multi-Agent Orchestration
Splits the Day 21 single ReAct agent into three roles, wired with LangGraph:
  - Router              -> classifies the question and picks a specialist
  - Coverage Specialist -> handles check_coverage / get_plan_details questions
  - Claims Specialist   -> handles get_claim_status questions
"""

from typing import Literal, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from tool_calling_chatbot import check_coverage, get_claim_status, get_plan_details

llm = ChatOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    model="llama3.1",
    temperature=0,
)

# ---------------------------------------------------------------------------
# Shared graph state
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    question: str
    route: str
    answer: str


# ---------------------------------------------------------------------------
# Router — classifies the question and decides which specialist runs.
# ---------------------------------------------------------------------------

ROUTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a Router agent for a health insurance support desk. "
            "Classify the member's question into exactly one category:\n"
            "- 'coverage' for questions about whether a procedure is covered, "
            "copays, prior authorization, or plan details (deductible, premium, tier).\n"
            "- 'claims' for questions about the status of a submitted claim, "
            "billed amount, or approved amount.\n"
            "Reply with a single word: coverage or claims.",
        ),
        ("human", "{question}"),
    ]
)


def router_node(state: AgentState) -> dict:
    resp = llm.invoke(ROUTER_PROMPT.format_messages(question=state["question"]))
    route = "claims" if "claim" in resp.content.strip().lower() else "coverage"
    return {"route": route}


def route_decision(state: AgentState) -> Literal["coverage_specialist", "claims_specialist"]:
    return "claims_specialist" if state["route"] == "claims" else "coverage_specialist"


# ---------------------------------------------------------------------------
# Coverage Specialist — owns check_coverage + get_plan_details.
# ---------------------------------------------------------------------------

COVERAGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the Coverage Specialist. You know each member's plan_id "
            "(e.g. 'silver_001', 'gold_001') from context. Given the tool result "
            "below, answer the member's question clearly and empathetically. "
            "Never invent numbers that aren't in the tool result.\n\nTool result: {tool_result}",
        ),
        ("human", "{question}"),
    ]
)


def coverage_specialist_node(state: AgentState) -> dict:
    q = state["question"].lower()
    plan_id = "gold_001" if "gold" in q else "silver_001"

    if "deductible" in q or "premium" in q or "plan detail" in q or "out-of-pocket max" in q:
        tool_result = get_plan_details(plan_id)
    else:
        for procedure in ["physical therapy", "chiropractic care", "mental health"]:
            if procedure in q:
                tool_result = check_coverage(plan_id, procedure)
                break
        else:
            tool_result = get_plan_details(plan_id)

    resp = llm.invoke(
        COVERAGE_PROMPT.format_messages(question=state["question"], tool_result=str(tool_result))
    )
    return {"answer": resp.content.strip()}


# ---------------------------------------------------------------------------
# Claims Specialist — owns get_claim_status.
# ---------------------------------------------------------------------------

CLAIMS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the Claims Specialist. Given the claim-status tool result "
            "below, answer the member's question clearly. Never invent numbers "
            "that aren't in the tool result.\n\nTool result: {tool_result}",
        ),
        ("human", "{question}"),
    ]
)


def claims_specialist_node(state: AgentState) -> dict:
    import re

    match = re.search(r"CLM-\d{4}-\d{4}", state["question"], re.IGNORECASE)
    claim_id = match.group(0).upper() if match else "CLM-2024-0892"
    tool_result = get_claim_status(claim_id)
    resp = llm.invoke(
        CLAIMS_PROMPT.format_messages(question=state["question"], tool_result=str(tool_result))
    )
    return {"answer": resp.content.strip()}


# ---------------------------------------------------------------------------
# Wire the graph: Router -> (Coverage Specialist | Claims Specialist) -> END
# ---------------------------------------------------------------------------

graph = StateGraph(AgentState)
graph.add_node("router", router_node)
graph.add_node("coverage_specialist", coverage_specialist_node)
graph.add_node("claims_specialist", claims_specialist_node)

graph.set_entry_point("router")
graph.add_conditional_edges("router", route_decision)
graph.add_edge("coverage_specialist", END)
graph.add_edge("claims_specialist", END)

workflow = graph.compile()

# ---------------------------------------------------------------------------
# 5 test questions — same coverage/claims mix as Day 21 so results are
# directly comparable.
# ---------------------------------------------------------------------------

TEST_QUESTIONS = [
    "Is physical therapy covered under my Silver plan (silver_001)? What would my copay be?",
    "What is the status of claim CLM-2024-0892, and how much was approved?",
    "Can you give me the full details of the silver_001 plan, including the deductible?",
    "Is mental health treatment covered under my silver_001 plan?",
    "I'm on the gold_001 plan — is physical therapy covered, and do I need prior authorization?",
]

if __name__ == "__main__":
    print("=== Day 22: Multi-Agent (Router + Specialists) Test ===\n")
    for i, q in enumerate(TEST_QUESTIONS, 1):
        result = workflow.invoke({"question": q, "route": "", "answer": ""})
        print(f"Q{i}: {q}")
        print(f"  Router -> {result['route']}")
        print(f"  Answer: {result['answer'][:200]}\n")
