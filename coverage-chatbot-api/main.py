from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import time, uuid, json

app = FastAPI(title="Coverage Chatbot API")
sessions = {}


class ChatRequest(BaseModel):
    session_id: str = None
    member_id: str = None
    message: str


def generate_llm_tokens(message: str):
    """Fake token generator standing in for a real LLM streaming SDK call."""
    reply = f"Coverage info for: {message}"
    for word in reply.split(" "):
        yield word + " "


@app.post("/chat")
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = []
    sessions[session_id].append({"role": "user", "content": request.message})
    start = time.time()

    def event_stream():
        full_response = ""
        try:
            for token in generate_llm_tokens(request.message):
                full_response += token
                elapsed_ms = (time.time() - start) * 1000
                data = {"session_id": session_id, "token": token, "elapsed_ms": elapsed_ms}
                yield f"data: {json.dumps(data)}\n\n"
        except Exception as e:
            error_payload = {"session_id": session_id, "error": f"LLM error: {str(e)}"}
            yield f"data: {json.dumps(error_payload)}\n\n"
            return
        sessions[session_id].append({"role": "assistant", "content": full_response.strip()})
        yield f"data: {json.dumps({'session_id': session_id, 'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "history": sessions[session_id]}
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time, uuid

app = FastAPI(title="Coverage Chatbot API")
sessions = {}

class ChatRequest(BaseModel):
      session_id: str = None
      member_id: str = None
      message: str

@app.post("/chat")
async def chat(request: ChatRequest):
      session_id = request.session_id or str(uuid.uuid4())
      if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append({"role": "user", "content": request.message})
    start = time.time()
    try:
              llm_response = f"Coverage info for: {request.message}"
except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")
    elapsed_ms = (time.time() - start) * 1000
    print(f"[TIMING] {elapsed_ms:.1f}ms session={session_id}")
    sessions[session_id].append({"role": "assistant", "content": llm_response})
    return {"session_id": session_id, "response": llm_response, "elapsed_ms": elapsed_ms}

@app.get("/history/{session_id}")
async def get_history(session_id: str):
      if session_id not in sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            return {"session_id": session_id, "history": sessions[session_id]}
