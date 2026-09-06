"""
Day 25: PHI/PII Redaction
Regex-based redaction for the fields this coverage chatbot's logs can see:
member IDs, claim IDs, plan IDs, SSNs, emails, phone numbers, and dates of
birth. Wired into coverage-chatbot-api/main.py's /chat request logging so
raw PHI never lands in application logs.
"""

import re
import unittest

_PATTERNS = [
    # SSN: 123-45-6789 or 123456789 in an SSN-shaped context
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED-SSN]"),
    # Claim IDs: CLM-2024-0892
    (re.compile(r"\bCLM-\d{4}-\d{4}\b", re.IGNORECASE), "[REDACTED-CLAIM-ID]"),
    # Member / plan IDs: silver_001, gold_002, member_12345
    (re.compile(r"\b(?:member|silver|gold|bronze)_\d+\b", re.IGNORECASE), "[REDACTED-MEMBER-ID]"),
    # Email addresses
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[REDACTED-EMAIL]"),
    # Phone numbers: (555) 123-4567, 555-123-4567, 555.123.4567
    (re.compile(r"(?:\(\d{3}\)\s?|\b\d{3}[-.])\d{3}[-.]\d{4}\b"), "[REDACTED-PHONE]"),
    # Dates of birth in common formats: MM/DD/YYYY, YYYY-MM-DD
    (re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"), "[REDACTED-DOB]"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "[REDACTED-DATE]"),
]


def redact_pii(text: str) -> str:
    """
    Redact PHI/PII from a string before it's logged or persisted.
    Applies each pattern in order; order matters so claim IDs are caught
    before the more general member-ID pattern could partially match them.
    """
    if not text:
        return text
    redacted = text
    for pattern, replacement in _PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestRedactPII(unittest.TestCase):
    def test_ssn(self):
        self.assertEqual(
            redact_pii("My SSN is 123-45-6789, please help."),
            "My SSN is [REDACTED-SSN], please help.",
        )

    def test_claim_id(self):
        self.assertEqual(
            redact_pii("What is the status of claim CLM-2024-0892?"),
            "What is the status of claim [REDACTED-CLAIM-ID]?",
        )

    def test_member_id(self):
        self.assertEqual(
            redact_pii("I'm on plan silver_001 and my member id is member_48213."),
            "I'm on plan [REDACTED-MEMBER-ID] and my member id is [REDACTED-MEMBER-ID].",
        )

    def test_email(self):
        self.assertEqual(
            redact_pii("Contact me at jane.doe@example.com"),
            "Contact me at [REDACTED-EMAIL]",
        )

    def test_phone(self):
        self.assertEqual(
            redact_pii("Call me at (555) 123-4567 or 555-987-6543."),
            "Call me at [REDACTED-PHONE] or [REDACTED-PHONE].",
        )

    def test_dob(self):
        self.assertEqual(
            redact_pii("My date of birth is 04/12/1990."),
            "My date of birth is [REDACTED-DOB].",
        )

    def test_no_pii_passthrough(self):
        clean = "Is physical therapy covered under my plan?"
        self.assertEqual(redact_pii(clean), clean)

    def test_empty_string(self):
        self.assertEqual(redact_pii(""), "")

    def test_multiple_pii_in_one_string(self):
        text = "Member member_1001, claim CLM-2024-1001, email a@b.com, SSN 987-65-4321."
        result = redact_pii(text)
        self.assertNotIn("member_1001", result)
        self.assertNotIn("CLM-2024-1001", result)
        self.assertNotIn("a@b.com", result)
        self.assertNotIn("987-65-4321", result)


if __name__ == "__main__":
    unittest.main()
