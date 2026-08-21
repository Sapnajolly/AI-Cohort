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
