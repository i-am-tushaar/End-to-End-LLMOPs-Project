"""
Application-level output safety for the RAG chatbot.

Purpose:
1. Block direct requests to extract personal information.
2. Redact common PII patterns from generated answers as a
   second layer of protection.

Note:
Regex-based detection is a basic safeguard, not a complete
privacy detector.
"""

import re


# Detect requests to extract personal information from documents.
PII_REQUEST_PATTERN = re.compile(
    r"\b(show|print|list|reveal|extract|provide|give|display|"
    r"tell me|copy|disclose)\b",
    re.IGNORECASE,
)

PII_TYPE_PATTERN = re.compile(
    r"\b(email addresses?|phone numbers?|mobile numbers?|"
    r"home addresses?|identity numbers?|personal information|"
    r"private information|PII|Aadhaar|passport numbers?|"
    r"social security numbers?)\b",
    re.IGNORECASE,
)

SAFE_REFUSAL = (
    "I can help summarize the document, but I can't provide "
    "a list of private or sensitive personal information."
)


def is_sensitive_extraction_request(user_input: str) -> bool:
    """Return True when a request appears to extract personal data."""
    return bool(
        PII_REQUEST_PATTERN.search(user_input)
        and PII_TYPE_PATTERN.search(user_input)
    )


def redact_common_pii(answer: str) -> str:
    """Redact common email, phone, and identity-number patterns."""

    # Redact email addresses.
    answer = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "[REDACTED_EMAIL]",
        answer,
    )

    # Redact phone-like numbers containing 10–15 digits.
    # This can occasionally match non-phone numeric identifiers.
    answer = re.sub(
        r"(?<!\w)(?:\+?\d[\d\s().-]{8,}\d)(?!\w)",
        "[REDACTED_NUMBER]",
        answer,
    )

    # Redact Aadhaar-like 12-digit sequences, including spaced groups.
    answer = re.sub(
        r"(?<!\d)(?:\d{4}[\s-]?){2}\d{4}(?!\d)",
        "[REDACTED_ID]",
        answer,
    )

    return answer


def apply_output_safety(user_input: str, answer: str) -> str:
    """
    Apply output safeguards before returning the answer to the user.
    """
    if is_sensitive_extraction_request(user_input):
        return SAFE_REFUSAL

    return redact_common_pii(answer)