# Streaming Notes - Day 18

## What changed
- coverage-chatbot-api/main.py: /chat now returns a StreamingResponse with media_type="text/event-stream". It yields SSE lines of the form "data: {json}\n\n", one per generated token, ending with a done event.
- app.py: the client now calls requests.post(..., stream=True) and iterates resp.iter_lines(), parsing each SSE data line as JSON and appending tokens into a single st.empty() placeholder so the message appears to type in real time.

## Typing / loading UX
- Before the first token arrives, the assistant bubble shows "Thinking...".
- As soon as the first SSE token event is received, the placeholder is overwritten with the growing response text, giving a live typing effect.
- If the stream ends with zero tokens received, the UI falls back to "No response received before stream ended." instead of showing a blank bubble.

## Timeout handling
- The requests.post call uses timeout=30. If the backend does not respond in time, requests.exceptions.Timeout is caught and the UI shows "Error: request timed out waiting for the backend to respond."

## Mid-stream error handling
- The backend wraps token generation in try/except; on failure it yields a single SSE event containing an "error" field instead of a normal token.
- The frontend checks each parsed event for an "error" key; if present it stops consuming the stream and shows "Error from backend: <message>" in place of a partial response.
- Any other connection failure during streaming (dropped connection, DNS error, etc.) is caught by requests.exceptions.RequestException and shown as "Error reaching chatbot backend: <details>".

## Manual test
Ran the Streamlit app against the streaming backend and sent a message. Observed the assistant bubble filling in token by token instead of appearing all at once, confirming SSE streaming end to end from FastAPI through to the Streamlit UI.
