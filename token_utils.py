"""
Day 26: Token Governance & Cost Management
tiktoken-based token counting, used by /chat to log prompt/completion
tokens and estimate cost per call.
"""

import tiktoken

# cl100k_base covers GPT-3.5/4-class tokenizers and is a reasonable
# approximation for any OpenAI-compatible model (including the local
# Ollama llama3.1 endpoint used elsewhere in this repo, which doesn't
# ship its own token-counting library).
_ENCODING = tiktoken.get_encoding("cl100k_base")

# Published per-1K-token rates (USD) used for cost estimation/logging.
# These are illustrative placeholder rates for a mid-tier hosted model —
# swap in your actual provider's published rates before trusting the
# dollar figures for real budgeting.
PROMPT_RATE_PER_1K = 0.0015
COMPLETION_RATE_PER_1K = 0.0020


def count_tokens(text: str) -> int:
    """Count tokens in `text` using the cl100k_base tokenizer."""
    if not text:
        return 0
    return len(_ENCODING.encode(text))


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost for a call given prompt/completion token counts."""
    prompt_cost = (prompt_tokens / 1000) * PROMPT_RATE_PER_1K
    completion_cost = (completion_tokens / 1000) * COMPLETION_RATE_PER_1K
    return round(prompt_cost + completion_cost, 6)


if __name__ == "__main__":
    sample_prompt = "Is physical therapy covered under my Silver plan (silver_001)?"
    sample_completion = "Yes, physical therapy is covered with a $40 copay and a 30 visit/year limit."
    p_tokens = count_tokens(sample_prompt)
    c_tokens = count_tokens(sample_completion)
    print(f"prompt_tokens={p_tokens} completion_tokens={c_tokens} "
          f"est_cost=${estimate_cost(p_tokens, c_tokens)}")
