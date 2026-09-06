from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import time, uuid, json, sqlite3, os
from collections import defaultdict, deque

from token_utils import count_tokens, estimate_cost

app = FastAPI(title="Coverage Chatbot API")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "coverage.db")
MAX_HISTORY_TOKENS = 2000
RECENT_TURNS = 6

# ---------------------------------------------------------------------------
# Day 26: rate limiting — per member, per minute, in-memory sliding window.
# (A production deployment would back this with Redis via slowapi's
# RedisBackend instead of an in-process dict, so limits survive restarts
# and are shared across workers.)
# ---------------------------------------------------------------------------

RATE_LIMIT_PER_MINUTE = 20
_request_log: dict[str, deque] = defaultdict(deque)


def check_rate_limit(member_id: str) -> bool:
    """Returns True if this member is still under the per-minute limit."""
    now = time.time()
    window = _request_log[member_id]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= RATE_LIMIT_PER_MINUTE:
        return False
    window.append(now)
    return True


# ---------------------------------------------------------------------------
# Day 26: exact-match cache for GENERAL questions only.
# Never cache anything keyed by member_id/plan_id/claim_id — those are
# member-specific and must always hit the real lookup.
# ---------------------------------------------------------------------------

_GENERAL_CACHE: dict[str, str] = {}

_MEMBER_SPECIFIC_MARKERS = ("claim", "clm-", "member_", "my plan", "my copay", "my claim")


def is_general_question(message: str) -> bool:
    """
    A question is cacheable only if it doesn't reference a specific
    member/claim — e.g. "What does prior authorization mean?" is general;
    "What's the status of claim CLM-2024-0892?" is member-specific and
    must never be served from cache.
    """
    lowered = message.lower()
    return not any(marker in lowered for marker in _MEMBER_SPECIFIC_MARKERS)


def cache_get(message: str) -> str | None:
    if is_general_question(message):
        return _GENERAL_CACHE.get(message.strip().lower())
    return None


def cache_set(message: str, response: str) -> None:
    if is_general_question(message):
        _GENERAL_CACHE[message.strip().lower()] = response


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS conversations ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "session_id TEXT, role TEXT, content TEXT, timestamp REAL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS token_usage ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "session_id TEXT, member_id TEXT, prompt_tokens INTEGER, "
        "completion_tokens INTEGER, est_cost_usd REAL, timestamp REAL)"
    )
    return conn


def log_token_usage(session_id: str, member_id: str, prompt_tokens: int, completion_tokens: int):
    cost = estimate_cost(prompt_tokens, completion_tokens)
    conn = get_db()
    conn.execute(
        "INSERT INTO token_usage (session_id, member_id, prompt_tokens, completion_tokens, est_cost_usd, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, member_id, prompt_tokens, completion_tokens, cost, time.time()),
    )
    conn.commit()
    conn.close()
    print(
        f"[TOKENS] session={session_id} member={member_id} "
        f"prompt={prompt_tokens} completion={completion_tokens} est_cost=${cost}"
    )
    return cost


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
    member_id = request.member_id or "anonymous"

    # --- Day 26: rate limit per member, per minute ---
    if not check_rate_limit(member_id):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded. Please wait a minute and try again."},
        )

    session_id = request.session_id or str(uuid.uuid4())
    plan_id = request.plan_id or "unknown"

    # --- Day 26: exact-match cache, general questions only ---
    cached = cache_get(request.message)
    if cached is not None:
        print(f"[CACHE] hit for general question: {request.message!r}")
        save_turn(session_id, "user", request.message)
        save_turn(session_id, "assistant", cached)
        prompt_tokens = count_tokens(request.message)
        completion_tokens = count_tokens(cached)
        log_token_usage(session_id, member_id, prompt_tokens, completion_tokens)

        def cached_stream():
            for word in cached.split(" "):
                yield f"data: {json.dumps({'session_id': session_id, 'token': word + ' ', 'cached': True})}\n\n"
            yield f"data: {json.dumps({'session_id': session_id, 'done': True, 'cached': True})}\n\n"

        return StreamingResponse(cached_stream(), media_type="text/event-stream")

    save_turn(session_id, "user", request.message)
    context = build_context(session_id, plan_id)
    prompt_tokens = count_tokens(request.message) + sum(count_tokens(h["content"]) for h in context)
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

        # --- Day 26: token/cost logging + cache write-through ---
        completion_tokens = count_tokens(full_response)
        log_token_usage(session_id, member_id, prompt_tokens, completion_tokens)
        cache_set(request.message, full_response.strip())

        yield f"data: {json.dumps({'session_id': session_id, 'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    history = load_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "history": history}


@app.get("/usage/{session_id}")
async def get_usage(session_id: str):
    """Day 26: expose logged token usage/cost for a session."""
    conn = get_db()
    rows = conn.execute(
        "SELECT prompt_tokens, completion_tokens, est_cost_usd, timestamp "
        "FROM token_usage WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    ).fetchall()
    conn.close()
    total_cost = sum(r[2] for r in rows)
    return {
        "session_id": session_id,
        "calls": [
            {"prompt_tokens": r[0], "completion_tokens": r[1], "est_cost_usd": r[2], "timestamp": r[3]}
            for r in rows
        ],
        "total_est_cost_usd": round(total_cost, 6),
    }
