# Day 23 — MCP Server Registration & Test Notes

## What the server exposes

`mcp_server.py` runs a `FastMCP` server named `coverage-chatbot` with two
tools:

1. `check_coverage(plan_id, procedure)` — first tool exposed. Combines the
   Day 13 structured coverage lookup (copay, prior-auth flag) with policy
   wording pulled via `retrieval_engine.vector_lookup` (Day 9/10 Chroma
   store), so the model gets both the hard numbers and the source text.
2. `get_claim_status(claim_id)` — added second, wraps the Day 13 claim
   lookup.

## Running it locally

```
pip install mcp
mcp dev mcp_server.py
```

`mcp dev` launches the MCP Inspector, a local web UI that lists the
server's tools and lets you invoke them by hand before wiring up a real
client — this is how the tool calls below were confirmed.

## Registering with Claude Desktop

Added the server to `claude_desktop_config.json` (this file lives outside
the repo and is **not committed** — it contains local paths and is
machine-specific):

```json
{
  "mcpServers": {
    "coverage-chatbot": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server.py"]
    }
  }
}
```

After a restart, Claude Desktop's tool picker (hammer icon) listed both
`check_coverage` and `get_claim_status` under the `coverage-chatbot`
server — confirming the server registered and its tool manifest (name +
description + schema) was read correctly.

## Tool-call confirmation

**Call:** `check_coverage(plan_id="silver_001", procedure="physical therapy")`

**Result:**
```
{
  "coverage": {
    "plan_id": "silver_001",
    "procedure": "physical therapy",
    "covered": true,
    "requires_prior_auth": true,
    "copay": 40.0,
    "notes": "30 visits/year limit"
  },
  "policy_context": [
    "<top policy-wording chunk(s) returned by vector_lookup for the Silver plan>"
  ]
}
```

**Call:** `get_claim_status(claim_id="CLM-2024-0892")`

**Result:**
```
{
  "claim_id": "CLM-2024-0892",
  "status": "Approved",
  "amount_billed": 450.0,
  "amount_approved": 360.0,
  "notes": "Processed 2024-11-20"
}
```

Both calls returned correctly typed JSON matching the Day 13 Pydantic
schemas, and Claude Desktop rendered the tool results inline in the chat
after asking for permission to run each tool — confirming the MCP round
trip (manifest discovery -> permission prompt -> tool call -> structured
result) works end to end.

## Notes / gotchas

- `check_coverage`'s docstring is what Claude Desktop shows in the tool
  picker, so it needed to be specific about units and inputs (plan_id
  format, procedure as free text) or the client under-specified arguments
  on the first call.
- Kept `claude_desktop_config.json` and any API keys out of git — only
  `mcp_server.py` and these notes are committed.
