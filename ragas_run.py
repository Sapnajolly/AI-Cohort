"""
Day 27: Evaluation Frameworks — RAGAS
Runs the Day 10/11 RAG pipeline (retrieval_engine.retrieve + rag_chatbot)
over the 20-pair eval set and scores it with RAGAS's four core metrics:
faithfulness, answer_relevancy, context_precision, context_recall.
"""

import json

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

from rag_chatbot import retrieve_and_answer  # Day 11 RAG pipeline under test
from retrieval_engine import retrieve

EVAL_SET_PATH = "ragas_eval_set.jsonl"


def load_eval_set(path: str) -> list[dict]:
    pairs = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                pairs.append(json.loads(line))
    return pairs


def build_ragas_dataset(pairs: list[dict]) -> Dataset:
    """
    For each eval pair, run the real RAG pipeline to get the retrieved
    contexts and the generated answer, so RAGAS scores the pipeline as it
    actually behaves today — not hand-picked contexts.
    """
    questions, answers, contexts_list, ground_truths = [], [], [], []

    for pair in pairs:
        question = pair["question"]
        ground_truth = pair["ground_truth"]

        retrieval_result = retrieve(question)
        contexts = [c["text"] for c in retrieval_result.get("vector_results", [])]
        if not contexts:
            # Structured-only answers (deductible, claim status, etc.) still
            # need a non-empty context list for RAGAS — fall back to the
            # stringified structured rows as the "context" it was grounded in.
            contexts = [str(row) for row in retrieval_result.get("sql_results", [])] or [""]

        answer = retrieve_and_answer(question)["answer"]  # Day 11's rag_chatbot entry point

        questions.append(question)
        answers.append(answer)
        contexts_list.append(contexts)
        ground_truths.append(ground_truth)

    return Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts_list,
            "ground_truth": ground_truths,
        }
    )


def run_eval(dataset: Dataset):
    return evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )


if __name__ == "__main__":
    pairs = load_eval_set(EVAL_SET_PATH)
    print(f"Loaded {len(pairs)} eval pairs from {EVAL_SET_PATH}")

    dataset = build_ragas_dataset(pairs)
    results = run_eval(dataset)

    print("\n=== RAGAS Scores ===")
    print(results)

    results.to_pandas().to_csv("ragas_run_results.csv", index=False)
    print("\nPer-question results written to ragas_run_results.csv")
