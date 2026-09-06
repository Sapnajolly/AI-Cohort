"""
Day 23: Model Context Protocol (MCP)
Exposes the coverage-chatbot tools as an MCP server so Claude Desktop / Cline
can discover and call them directly.

Run locally with:
    mcp dev mcp_server.py
or register it in Claude Desktop's claude_desktop_config.json and run via:
    python mcp_server.py
"""

from mcp.server.fastmcp import FastMCP

from retrieval_engine import vector_lookup
from tool_calling_chatbot import check_coverage as _check_coverage_lookup
from tool_calling_chatbot import get_claim_status as _get_claim_status_lookup

mcp = FastMCP("coverage-chatbot")


@mcp.tool()
def check_coverage(plan_id: str, procedure: str) -> dict:
    """
    Check whether a medical procedure is covered under a member's plan.

    Combines the structured coverage record (copay, prior-auth flag) from
    Day 13's mock coverage table with the relevant policy-wording chunks
    pulled from the Day 9/10 vector store (retrieval_engine.vector_lookup),
    so the caller gets both the hard numbers and the underlying policy text.

    Args:
        plan_id: The member's plan ID, e.g. 'silver_001'.
        procedure: The medical procedure name, e.g. 'physical therapy'.
    """
    structured = _check_coverage_lookup(plan_id, procedure)
    plan_type = "Silver" if "silver" in plan_id.lower() else "Gold"
    policy_chunks = vector_lookup(
        f"Is {procedure} covered? {procedure} coverage rules",
        n_results=3,
        plan_filter=plan_type,
    )
    return {
        "coverage": structured,
        "policy_context": [c["text"] for c in policy_chunks],
    }


@mcp.tool()
def get_claim_status(claim_id: str) -> dict:
    """
    Retrieve the current status of a submitted insurance claim.

    Args:
        claim_id: The claim ID, e.g. 'CLM-2024-0892'.
    """
    return _get_claim_status_lookup(claim_id)


if __name__ == "__main__":
    mcp.run()
