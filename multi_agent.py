"""
Day 22 -> Day 24: Multi-Agent Orchestration, now calling real MCP tools.

Router -> Coverage Specialist / Claims Specialist, same as Day 22, but the
specialists now call the Day 23 MCP server (mcp_server.py) over stdio
instead of importing the tool functions directly. Every tool call is
wrapped with a 10s timeout, one retry on transient failure, and a canned
support fallback so a broken/slow tool never surfaces a raw error (or a
500) to the member.
"""

import asyncio
from typing import Literal, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

llm = ChatOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    model="llama3.1",
    temperature=0,
)

TOOL_TIMEOUT_SECONDS = 10
MAX_RETRIES = 1
CANNED_FALLBACK = (
    "I'm having trouble reaching our systems for that lookup right now. "
    "I don't want to guess at your coverage or claim details, so please try "
    "again in a moment, or reach a live support rep if this keeps happening."
)

MCP_SERVER_PARAMS = StdioServerParameters(command="python", args=["mcp_server.py"])


# ---------------------------------------------------------------------------
# Resilient MCP tool caller — 10s timeout, 1 retry, canned fallback.
# Used by both specialists so the resilience logic lives in exactly one place.
# ---------------------------------------------------------------------------


async def call_mcp_tool(tool_name: str, arguments: dict) -> dict | None:
    """
    Call an MCP tool with a timeout and one retry on failure.
    Returns the tool's structured result, or None if both attempts failed
    (caller is responsible for using CANNED_FALLBACK in that case).
    """
    attempts = MAX_RETRIES + 1
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            async with stdio_client(MCP_SERVER_PARAMS) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await asyncio.wait_for(
                        session.call_tool(tool_name, arguments),
                        timeout=TOOL_TIMEOUT_SECONDS,
                    )
                    return result
        except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001 - deliberately broad, this is the resilience boundary
            last_error = exc
            if attempt < attempts:
                continue  # one retry on transient failure
            break

    print(f"[chaos] {tool_name} failed after {attempts} attempt(s): {last_error}")
    return None


# ---------------------------------------------------------------------------
# Shared graph state
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    question: str
    route: str
    answer: str


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

ROUTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a Router agent for a health insurance support desk. "
            "Classify the member's question into exactly one category:\n"
            "- 'coverage' for coverage, copay, prior-auth, or plan-detail questions.\n"
            "- 'claims' for claim-status questions.\n"
            "Reply with a single word: coverage or claims.",
        ),
        ("human", "{question}"),
    ]
)


async def router_node(state: AgentState) -> dict:
    resp = await llm.ainvoke(ROUTER_PROMPT.format_messages(question=state["question"]))
    route = "claims" if "claim" in resp.content.strip().lower() else "coverage"
    return {"route": route}


def route_decision(state: AgentState) -> Literal["coverage_specialist", "claims_specialist"]:
    return "claims_specialist" if state["route"] == "claims" else "coverage_specialist"


# ---------------------------------------------------------------------------
# Coverage Specialist — now calls the MCP check_coverage tool.
# ---------------------------------------------------------------------------

COVERAGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the Coverage Specialist. Given the tool result below, "
            "answer the member's question clearly and empathetically. Never "
            "invent numbers that aren't in the tool result.\n\nTool result: {tool_result}",
        ),
        ("human", "{question}"),
    ]
)


async def coverage_specialist_node(state: AgentState) -> dict:
    q = state["question"].lower()
    plan_id = "gold_001" if "gold" in q else "silver_001"
    procedure = next(
        (p for p in ["physical therapy", "chiropractic care", "mental health"] if p in q),
        "physical therapy",
    )

    tool_result = await call_mcp_tool("check_coverage", {"plan_id": plan_id, "procedure": procedure})
    if tool_result is None:
        return {"answer": CANNED_FALLBACK}

    resp = await llm.ainvoke(
        COVERAGE_PROMPT.format_messages(question=state["question"], tool_result=str(tool_result))
    )
    return {"answer": resp.content.strip()}


# ---------------------------------------------------------------------------
# Claims Specialist — now calls the MCP get_claim_status tool.
# ---------------------------------------------------------------------------

CLAIMS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the Claims Specialist. Given the claim-status tool result "
            "below, answer clearly. Never invent numbers.\n\nTool result: {tool_result}",
        ),
        ("human", "{question}"),
    ]
)


async def claims_specialist_node(state: AgentState) -> dict:
    import re

    match = re.search(r"CLM-\d{4}-\d{4}", state["question"], re.IGNORECASE)
    claim_id = match.group(0).upper() if match else "CLM-2024-0892"

    tool_result = await call_mcp_tool("get_claim_status", {"claim_id": claim_id})
    if tool_result is None:
        return {"answer": CANNED_FALLBACK}

    resp = await llm.ainvoke(
        CLAIMS_PROMPT.format_messages(question=state["question"], tool_result=str(tool_result))
    )
    return {"answer": resp.content.strip()}


# ---------------------------------------------------------------------------
# Wire the graph
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

TEST_QUESTIONS = [
    "Is physical therapy covered under my Silver plan (silver_001)? What would my copay be?",
    "What is the status of claim CLM-2024-0892, and how much was approved?",
    "Can you give me the full details of the silver_001 plan, including the deductible?",
    "Is mental health treatment covered under my silver_001 plan?",
    "I'm on the gold_001 plan — is physical therapy covered, and do I need prior authorization?",
]


async def main() -> None:
    print("=== Day 24: Full Integration (MCP + Multi-Agent + Resilience) Test ===\n")
    for i, q in enumerate(TEST_QUESTIONS, 1):
        result = await workflow.ainvoke({"question": q, "route": "", "answer": ""})
        print(f"Q{i}: {q}")
        print(f"  Router -> {result['route']}")
        print(f"  Answer: {result['answer'][:200]}\n")


if __name__ == "__main__":
    asyncio.run(main())
