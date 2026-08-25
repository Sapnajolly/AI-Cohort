# Backend Chat Test Notes - Day 16

## Setup
cd coverage-chatbot-api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

## 3-message session test (curl)

Message 1 (new session):
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"member_id\": \"M1001\", \"message\": \"What does my plan cover for annual checkups?\"}"

Response returns a generated session_id, e.g. a1b2c3d4-.... Save it for the next calls.

Message 2 (same session_id):
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"session_id\": \"a1b2c3d4-...\", \"member_id\": \"M1001\", \"message\": \"Does that include dental?\"}"

Message 3 (same session_id):
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"session_id\": \"a1b2c3d4-...\", \"member_id\": \"M1001\", \"message\": \"What about my claim status from last week?\"}"
## History check
curl http://127.0.0.1:8000/history/a1b2c3d4-...

Returns the full stored history (all 3 user turns + assistant turns) for that session_id, confirming state was tracked across the session.

## Timing and error handling
- Each /chat call logs a TIMING line with elapsed ms and session id, printed server-side.
- - The LLM call path is wrapped in try/except; on failure it raises HTTPException(500, "LLM error: ...") instead of crashing the process.
  - - Requesting /history/{session_id} for an unknown session_id returns 404 Session not found.
   
    - ## Result
    - All 3 sequential messages were sent with the same session_id and correctly appended to that session's history, confirming session-based conversation state tracking works end to end.
