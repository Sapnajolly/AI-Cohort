"""
Day 11: RAG End-to-End & LLM API Basics
Full RAG pipeline: retrieve -> augment -> generate -> return
Uses Ollama (llama3.1) via OpenAI-compatible SDK (free, local, no key required)
"""

import os
from openai import OpenAI
from retrieval_engine import retrieve

# --- LLM Client Setup (Ollama local) ---
# Run: ollama pull llama3.1
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)
MODEL = "llama3.1"

# --- Grounding System Prompt ---
GROUNDING_SYSTEM_PROMPT = """You are a health insurance coverage assistant.
Answer ONLY using the context provided below.
Do NOT use any outside knowledge or make assumptions.
If the context does not contain enough information to answer, say:
"I don't have enough information in the provided context to answer that question."

Context:
{context}
"""


def generate_answer(question: str, context_chunks: list, context_sql: list = None) -> str:
    """
    Generate a grounded LLM answer using retrieved context.
    Uses the grounding system prompt to ensure answers come only from context.
    """
    vector_context = "\n\n".join(
        [f"[Policy chunk {i+1}]: {c['text']}" for i, c in enumerate(context_chunks)]
    ) if context_chunks else ""

    sql_context = ""
    if context_sql:
        sql_rows = "\n".join([str(row) for row in context_sql[:3]])
        sql_context = f"\n\n[Structured plan data]:\n{sql_rows}"

    full_context = vector_context + sql_context
    system_prompt = GROUNDING_SYSTEM_PROMPT.format(context=full_context or "No context retrieved.")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.1,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


def retrieve_and_answer(question: str, plan_filter: str = None) -> dict:
    """
    End-to-end RAG function: retrieve context, then generate a grounded answer.
    Returns a dict with question, classification, context counts, and answer.
    """
    retrieval = retrieve(question, plan_filter=plan_filter)
    answer = generate_answer(
        question=question,
        context_chunks=retrieval["vector_results"],
        context_sql=retrieval["sql_results"],
    )
    return {
        "question": question,
        "classification": retrieval["classification"],
        "vector_chunks": len(retrieval["vector_results"]),
        "sql_rows": len(retrieval["sql_results"]),
        "answer": answer,
    }


def stream_answer(question: str):
    """Smoke-test streaming completion."""
    print(f"\n[Streaming] Q: {question}\n")
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful insurance assistant. Answer briefly."},
            {"role": "user", "content": question},
        ],
        stream=True,
        max_tokens=200,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
    print()


TEST_QUESTIONS = [
    "What is my deductible for the Silver plan?",
    "Is physical therapy covered under the Silver plan?",
    "What is the status of my recent claim?",
    "Does my plan cover mental health treatment?",
    "What is the monthly premium for the Gold plan?",
    "Is chiropractic care covered?",
    "How much is my copay for specialist visits?",
    "What does the Silver plan say about prior authorization?",
    "What is my out-of-pocket maximum?",
    "Are out-of-network providers covered for emergency care?",
]

if __name__ == "__main__":
    print("=== Day 11: RAG End-to-End Test Harness ===\n")
    stream_answer("What does the Silver plan cover for physical therapy?")
    for i, question in enumerate(TEST_QUESTIONS, 1):
        result = retrieve_and_answer(question, plan_filter="Silver")
        print(f"Q{i}: {question}")
        print(f"  Classification: {result['classification']}")
        print(f"  Answer: {result['answer'][:200]}")
        print()
