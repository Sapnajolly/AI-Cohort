"""
Day 10: Retrieval / Matching Engine
Structured + Vector Search with Query Routing
"""

import sqlite3
import json
import chromadb
from sentence_transformers import SentenceTransformer

# --- Configuration ---
DB_PATH = "coverage.db"
CHROMA_PATH = "./chroma_data"
COLLECTION_NAME = "coverage_kb"
EMBED_MODEL = "all-MiniLM-L6-v2"

# Load embedding model and Chroma collection
_model = SentenceTransformer(EMBED_MODEL)
_client = chromadb.PersistentClient(path=CHROMA_PATH)
_collection = _client.get_or_create_collection(COLLECTION_NAME)


# --- Question Classifier ---
STRUCTURED_KEYWORDS = [
      "deductible", "premium", "copay", "co-pay", "out-of-pocket",
      "claim", "claims", "status", "balance", "plan name", "plan id",
      "member id", "enrollment", "effective date", "cost", "price",
      "how much", "what is my", "what are my", "what plan",
]

UNSTRUCTURED_KEYWORDS = [
      "covered", "coverage", "does my plan", "is it covered", "procedure",
      "therapy", "treatment", "benefit", "eligible", "qualify", "allowed",
      "policy", "wording", "what does", "does insurance", "can i get",
      "prior authorization", "referral", "in-network", "out-of-network",
]


def classify(question: str) -> str:
      """
          Classify a question as 'structured', 'unstructured', or 'both'.
              structured  -> SQL lookup (plan data, claims, costs)
                  unstructured -> vector DB lookup (policy wording, coverage rules)
                      both        -> hybrid search
                          """
      q = question.lower()
      is_structured = any(kw in q for kw in STRUCTURED_KEYWORDS)
      is_unstructured = any(kw in q for kw in UNSTRUCTURED_KEYWORDS)

    if is_structured and is_unstructured:
              return "both"
elif is_structured:
          return "structured"
else:
          return "unstructured"


# --- SQL Lookup ---
def sql_lookup(question: str) -> list[dict]:
      """
          Query the SQLite coverage.db for structured data (plans, claims).
              Returns a list of result dicts.
                  """
      results = []
      try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

          q = question.lower()

        if "deductible" in q or "premium" in q or "plan" in q or "copay" in q:
                      cursor.execute(
                                        "SELECT * FROM plans WHERE plan_name LIKE '%Silver%' OR plan_name LIKE '%Gold%' OR plan_name LIKE '%Bronze%' LIMIT 5"
                      )
                      rows = cursor.fetchall()
                      results = [dict(row) for row in rows]

elif "claim" in q or "status" in q:
            cursor.execute("SELECT * FROM claims LIMIT 5")
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]

else:
            cursor.execute("SELECT * FROM plans LIMIT 3")
              rows = cursor.fetchall()
            results = [dict(row) for row in rows]

        conn.close()
except Exception as e:
        results = [{"error": str(e)}]

    return results


# --- Vector Lookup ---
def vector_lookup(question: str, n_results: int = 5, plan_filter: str = None) -> list[dict]:
      """
          Query the ChromaDB vector store for relevant policy chunks.
              Optionally filter by plan_type metadata.
                  Returns a list of chunk dicts with text and metadata.
                      """
    embedding = _model.encode([question]).tolist()

    query_kwargs = {
              "query_embeddings": embedding,
              "n_results": n_results,
    }
    if plan_filter:
              query_kwargs["where"] = {"plan_type": plan_filter}

    results = _collection.query(**query_kwargs)

    chunks = []
    if results and results.get("documents"):
              for i, doc in enumerate(results["documents"][0]):
                            chunks.append({
                                              "text": doc,
                                              "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                                              "distance": results["distances"][0][i] if results.get("distances") else None,
                            })
                    return chunks


# --- Main Routing Function ---
def retrieve(question: str, plan_filter: str = None) -> dict:
      """
          Route the question to SQL, vector DB, or both based on classification.
              Returns a dict with classification, sql_results, and vector_results.
                  """
    label = classify(question)
    sql_results = []
    vector_results = []

    if label in ("structured", "both"):
              sql_results = sql_lookup(question)

    if label in ("unstructured", "both"):
              vector_results = vector_lookup(question, plan_filter=plan_filter)

    return {
              "question": question,
              "classification": label,
              "sql_results": sql_results,
              "vector_results": vector_results,
    }


# --- Test Harness (10 questions) ---
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
      print("=== Day 10: Retrieval Engine Test Harness ===\n")
    for i, question in enumerate(TEST_QUESTIONS, 1):
              result = retrieve(question, plan_filter="Silver")
        print(f"Q{i}: {question}")
        print(f"  Classification: {result['classification']}")
        print(f"  SQL results: {len(result['sql_results'])} rows")
        print(f"  Vector results: {len(result['vector_results'])} chunks")
        if result['vector_results']:
                      top = result['vector_results'][0]
                      print(f"  Top chunk: {top['text'][:120]}...")
                  print()
