# Rich Outputs Test - Day 19

## Setup
streamlit run app.py

## Test questions (3)

1. "What does my coverage include?" - triggers a normal streamed chat answer plus a citations footnote (Sources: benefits.txt#chunk-3, enrollment.txt#chunk-1) and a CoverageSummaryCard rendered below the answer.
2. "What is the status of my claim?" - triggers the streamed answer plus a ClaimStatusCard rendered with claim_id, status, date filed, and amount.
3. "Tell me about my plan and any recent claims" - triggers both the CoverageSummaryCard and the ClaimStatusCard together, alongside the citations footnote, confirming both Pydantic card types and citation rendering work in the same turn.

## What was verified
- Citations: render_citations() in app.py prints a "Sources: ..." caption under the assistant message using the chunk IDs tracked alongside the answer.
- Cards: ClaimStatusCard and CoverageSummaryCard (both Pydantic BaseModel subclasses in response_cards.py) are instantiated and rendered via st.markdown(card.to_markdown()).
- Markdown rendering: card output uses **bold** headers and "- " bullet lines, confirmed to render correctly inside st.chat_message via st.markdown.

## Result
All 3 test questions produced the expected citations footnote and card output, confirming rich formatting works end to end in the Streamlit chat UI.
