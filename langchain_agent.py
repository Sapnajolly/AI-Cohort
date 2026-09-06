"""
Day 21: Agentic Frameworks — LangChain Agents & Tool Use
Wraps the Day 13 coverage tools as LangChain Tool objects, builds a ReAct
agent (Thought -> Action -> Observation -> Final Answer), and runs 5 test
questions with verbose=True so the reasoning trace is visible on stdout
(and logged to agent_traces.md by hand after review).
"""

from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from tool_calling_chatbot import check_coverage, get_claim_status, get_plan_details

# ---------------------------------------------------------------------------
# LLM (same local Ollama endpoint used since Day 2 — free, no API key)
# ---------------------------------------------------------------------------

llm = ChatOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    model="llama3.1",
    temperature=0,
)

# ---------------------------------------------------------------------------
# Wrap the Day 13 tool functions as LangChain Tool objects.
# The `name` + `description` are what drive the agent's tool-selection —
# they need to read like a human coverage rep's mental model of when to
# reach for each one.
# ---------------------------------------------------------------------------


def _check_coverage(query: str) -> str:
    """Expects 'plan_id, procedure' e.g. 'silver_001, physical therapy'."""
    plan_id, procedure = [p.strip() for p in query.split(",", 1)]
    return str(check_coverage(plan_id, procedure))


def _get_claim_status(query: str) -> str:
    """Expects a claim id, e.g. 'CLM-2024-0892'."""
    return str(get_claim_status(query.strip()))


def _get_plan_details(query: str) -> str:
    """Expects a plan id, e.g. 'silver_001'."""
    return str(get_plan_details(query.strip()))


tools = [
    Tool(
        name="check_coverage",
        func=_check_coverage,
        description=(
            "Use to check whether a specific medical procedure is covered under a "
            "member's plan, including copay and prior-authorization requirements. "
            "Input must be a comma-separated 'plan_id, procedure' string, e.g. "
            "'silver_001, physical therapy'."
        ),
    ),
    Tool(
        name="get_claim_status",
        func=_get_claim_status,
        description=(
            "Use to look up the current status (Approved/Pending/Denied), billed "
            "amount, and approved amount of a previously submitted claim. Input "
            "must be a claim id, e.g. 'CLM-2024-0892'."
        ),
    ),
    Tool(
        name="get_plan_details",
        func=_get_plan_details,
        description=(
            "Use to retrieve a plan's full details — name, tier, deductible, "
            "out-of-pocket max, and monthly premium. Input must be a plan id, "
            "e.g. 'silver_001'."
        ),
    ),
]

# ---------------------------------------------------------------------------
# ReAct prompt (self-contained so the agent doesn't depend on pulling
# hwchase17/react from the LangChain hub at runtime).
# ---------------------------------------------------------------------------

REACT_PROMPT = PromptTemplate.from_template(
    """You are a health insurance coverage assistant. Answer the member's
question as best you can using the tools below. Do NOT make up numbers —
always call a tool to get real data before answering.

You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question, in a clear,
empathetic tone for the member.

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
)

agent = create_react_agent(llm, tools, REACT_PROMPT)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,          # <-- prints the Thought -> Action -> Observation trace
    handle_parsing_errors=True,
    max_iterations=6,
)

# ---------------------------------------------------------------------------
# 5 test questions (mirrors the Day 13 tool-call test set so tool choices
# can be compared apples-to-apples against a human coverage rep).
# ---------------------------------------------------------------------------

TEST_QUESTIONS = [
    "Is physical therapy covered under my Silver plan (silver_001)? What would my copay be?",
    "What is the status of claim CLM-2024-0892, and how much was approved?",
    "Can you give me the full details of the silver_001 plan, including the deductible?",
    "Is mental health treatment covered under my silver_001 plan?",
    "I'm on the gold_001 plan — is physical therapy covered, and do I need prior authorization?",
]

if __name__ == "__main__":
    print("=== Day 21: ReAct Agent Test ===\n")
    for i, q in enumerate(TEST_QUESTIONS, 1):
        print(f"\n{'=' * 70}\nQ{i}: {q}\n{'=' * 70}")
        result = agent_executor.invoke({"input": q})
        print(f"\nFINAL ANSWER: {result['output']}\n")
