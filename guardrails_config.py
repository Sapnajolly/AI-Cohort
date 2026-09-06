"""
Day 25: Input + Output Guardrails
Lightweight, dependency-free guardrails for the coverage chatbot. Designed
to sit in front of (input) and behind (output) the agent call in
coverage-chatbot-api/main.py. A Guardrails AI / Presidio-based version is
noted as a follow-up in GOVERNANCE.md — this pass covers the three highest
priority risks: prompt injection, PHI/system-prompt leakage, and
unlicensed medical advice.
"""

import re
from dataclasses import dataclass


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str = ""
    safe_text: str = ""


# ---------------------------------------------------------------------------
# INPUT guardrail — blocks prompt-injection / jailbreak attempts before the
# member's message reaches the agent.
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS = [
    re.compile(r"ignore (all|any|every|the)?\s*(all|previous|prior|earlier)?\s*instructions", re.IGNORECASE),
    re.compile(r"disregard (your|the) (system|previous) prompt", re.IGNORECASE),
    re.compile(r"you are now (in )?(dan|developer|jailbreak) mode", re.IGNORECASE),
    re.compile(r"reveal (your|the) system prompt", re.IGNORECASE),
    re.compile(r"print (your|the) instructions", re.IGNORECASE),
    re.compile(r"act as (an?|the) unrestricted", re.IGNORECASE),
]


def check_input(user_message: str) -> GuardrailResult:
    """
    Reject messages that look like prompt-injection / jailbreak attempts.
    Everything else passes through unchanged.
    """
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(user_message):
            return GuardrailResult(
                allowed=False,
                reason="prompt_injection_attempt",
                safe_text=(
                    "I can't follow instructions that try to change how I operate. "
                    "I'm happy to help with your coverage or claims question directly."
                ),
            )
    return GuardrailResult(allowed=True, safe_text=user_message)


# ---------------------------------------------------------------------------
# OUTPUT guardrail — scrubs system-prompt/PHI leakage and redirects
# unlicensed medical-advice responses before they reach the member.
# ---------------------------------------------------------------------------

_LEAKAGE_MARKERS = [
    "SYSTEM_PROMPT",
    "you are a health insurance coverage assistant",  # our own system prompt text
    "MOCK_COVERAGE",
    "MOCK_CLAIMS",
    "MOCK_PLANS",
]

_MEDICAL_ADVICE_PATTERNS = [
    re.compile(r"\byou should (take|stop taking|increase|decrease)\b.{0,25}\b(mg|dose|dosage|pills?)\b", re.IGNORECASE),
    re.compile(r"\bi diagnose you with\b", re.IGNORECASE),
    re.compile(r"\byou (definitely|probably) have (cancer|diabetes|a tumor)\b", re.IGNORECASE),
]

MEDICAL_ADVICE_REDIRECT = (
    "I can help with your plan's coverage, copays, and claim status, but I'm "
    "not able to give medical advice or a diagnosis. Please talk to your "
    "doctor or a licensed clinician about that — I can help you check "
    "whether it's covered once you know what's being recommended."
)


def check_output(agent_response: str) -> GuardrailResult:
    """
    Block responses that leak internal prompt/data structures, and redirect
    anything that reads as medical advice/diagnosis instead of a coverage
    or claims answer.
    """
    for marker in _LEAKAGE_MARKERS:
        if marker.lower() in agent_response.lower():
            return GuardrailResult(
                allowed=False,
                reason="internal_leakage",
                safe_text=(
                    "Sorry, I hit an internal error putting that answer together. "
                    "Could you rephrase your question?"
                ),
            )

    for pattern in _MEDICAL_ADVICE_PATTERNS:
        if pattern.search(agent_response):
            return GuardrailResult(
                allowed=False,
                reason="medical_advice_redirect",
                safe_text=MEDICAL_ADVICE_REDIRECT,
            )

    return GuardrailResult(allowed=True, safe_text=agent_response)


# ---------------------------------------------------------------------------
# Convenience wrapper for the /chat endpoint
# ---------------------------------------------------------------------------


def guarded_chat_turn(user_message: str, run_agent) -> str:
    """
    run_agent: callable that takes the (already-checked) user message and
    returns the agent's raw response string. Wraps it with input/output
    guardrails so /chat only ever calls run_agent on safe input and only
    ever returns safe output.
    """
    input_check = check_input(user_message)
    if not input_check.allowed:
        return input_check.safe_text

    raw_response = run_agent(input_check.safe_text)

    output_check = check_output(raw_response)
    return output_check.safe_text
