from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import time, uuid, json, sqlite3, os

app = FastAPI(title="Coverage Chatbot API")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "coverage.db")
MAX_HISTORY_TOKENS = 2000
RECENT_TURNS = 6


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS conversations ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "session_id TEXT, role TEXT, content TEXT, timestamp REAL)"
    )
    return conn


def count_tokens(text: str) -> int:
    # Simple whitespace-based token estimate, avoids an extra dependency.
    return len(text.split())


def save_turn(session_id: str, role: str, content: str):
    conn = get_db()
    conn.execute(
        "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, content, time.time()),
    )
    conn.commit()
    conn.close()


def load_history(session_id: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    ).fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in rows]


def summarize_if_needed(session_id: str):
    """If total history tokens exceed MAX_HISTORY_TOKENS, collapse the older
    half into a single summary turn so the context stays bounded."""
    history = load_history(session_id)
    total_tokens = sum(count_tokens(h["content"]) for h in history)
    if total_tokens <= MAX_HISTORY_TOKENS or len(history) < 4:
        return
    split = len(history) // 2
    older = history[:split]
    summary_text = "Summary of earlier conversation: " + " | ".join(
        h["content"][:80] for h in older
    )
    conn = get_db()
    conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
    conn.execute(
        "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, "system", summary_text, time.time()),
    )
    for h in history[split:]:
        conn.execute(
            "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, h["role"], h["content"], time.time()),
        )
    conn.commit()
    conn.close()
    print(f"[MEMORY] session={session_id} summarized {len(older)} older turns, tokens_before={total_tokens}")


def build_context(session_id: str, plan_id: str):
    history = load_history(session_id)
    recent = history[-RECENT_TURNS:]
    context_tokens = sum(count_tokens(h["content"]) for h in recent)
    print(f"[MEMORY] session={session_id} plan={plan_id} recent_turns={len(recent)} context_tokens={context_tokens}")
    return recent


class ChatRequest(BaseModel):
    session_id: str = None
    member_id: str = None
    plan_id: str = None
    message: str


def generate_llm_tokens(message: str, context):
    reply = f"Coverage info for: {message}"
    for word in reply.split(" "):
        yield word + " "


@app.post("/chat")
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    plan_id = request.plan_id or "unknown"
    save_turn(session_id, "user", request.message)
    context = build_context(session_id, plan_id)
    start = time.time()

    def event_stream():
        full_response = ""
        try:
            for token in generate_llm_tokens(request.message, context):
                full_response += token
                elapsed_ms = (time.time() - start) * 1000
                data = {"session_id": session_id, "token": token, "elapsed_ms": elapsed_ms}
                yield f"data: {json.dumps(data)}\n\n"
        except Exception as e:
            error_payload = {"session_id": session_id, "error": f"LLM error: {str(e)}"}
            yield f"data: {json.dumps(error_payload)}\n\n"
            return
        save_turn(session_id, "assistant", full_response.strip())
        summarize_if_needed(session_id)
        yield f"data: {json.dumps({'session_id': session_id, 'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    history = load_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "history": history}
