"""Content Filter for Sensitive Information.

Provides PII (Personally Identifiable Information) detection and redaction
for insurance claim documents and extracted data.
"""

import re
from typing import Any, Dict, List, Tuple


class ContentFilter:
    """Filters sensitive information from text and structured data.

    Detects and redacts PII patterns including Social Security Numbers,
    phone numbers, email addresses, and other sensitive fields.

    Attributes:
        pii_patterns: List of tuples (pattern_name, regex_pattern, replacement).
    """

    def __init__(self) -> None:
        """Initialize ContentFilter with default PII patterns."""
        self.pii_patterns: List[Tuple[str, re.Pattern, str]] = [
            (
                "ssn",
                re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
                "[SSN REDACTED]",
            ),
            (
                "ssn_no_dashes",
                re.compile(r"\b\d{9}\b(?!\d)"),
                "[SSN REDACTED]",
            ),
            (
                "phone",
                re.compile(
                    r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
                ),
                "[PHONE REDACTED]",
            ),
            (
                "email",
                re.compile(
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
                ),
                "[EMAIL REDACTED]",
            ),
            (
                "credit_card",
                re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
                "[CREDIT CARD REDACTED]",
            ),
            (
                "bank_account",
                re.compile(r"\b(?:account|acct)[\s#:]*\d{8,17}\b", re.IGNORECASE),
                "[BANK ACCOUNT REDACTED]",
            ),
            (
                "drivers_license",
                re.compile(
                    r"\b(?:DL|driver'?s?\s*license)[\s#:]*[A-Z0-9]{6,12}\b",
                    re.IGNORECASE,
                ),
                "[DRIVER'S LICENSE REDACTED]",
            ),
        ]

        # Fields that should be masked in structured data
        self.sensitive_fields = [
            "ssn",
            "social_security",
            "social_security_number",
            "drivers_license",
            "driver_license",
            "bank_account",
            "account_number",
            "credit_card",
            "credit_card_number",
            "routing_number",
            "date_of_birth",
            "dob",
        ]

    def filter_pii(self, text: str) -> str:
        """Redact PII patterns from text.

        Scans text for known PII patterns (SSN, phone, email, etc.)
        and replaces them with redaction markers.

        Args:
            text: Input text that may contain PII.

        Returns:
            Text with PII patterns replaced by redaction markers.
        """
        if not text:
            return text

        filtered_text = text
        for pattern_name, pattern, replacement in self.pii_patterns:
            filtered_text = pattern.sub(replacement, filtered_text)

        return filtered_text

    def filter_sensitive_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive fields in a dictionary.

        Replaces values of known sensitive fields with masked versions,
        showing only the last 4 characters.

        Args:
            data: Dictionary that may contain sensitive field values.

        Returns:
            New dictionary with sensitive fields masked.
        """
        if not data:
            return data

        filtered = {}
        for key, value in data.items():
            key_lower = key.lower().replace("-", "_").replace(" ", "_")

            if key_lower in self.sensitive_fields:
                filtered[key] = self._mask_value(value)
            elif isinstance(value, dict):
                filtered[key] = self.filter_sensitive_fields(value)
            elif isinstance(value, str):
                filtered[key] = self.filter_pii(value)
            else:
                filtered[key] = value

        return filtered

    def _mask_value(self, value: Any) -> str:
        """Mask a sensitive value, showing only last 4 characters.

        Args:
            value: The value to mask.

        Returns:
            Masked string showing '***' prefix and last 4 chars.
        """
        if value is None:
            return "[REDACTED]"

        str_value = str(value).strip()
        if len(str_value) <= 4:
            return "[REDACTED]"

        return "***" + str_value[-4:]

    def get_pii_report(self, text: str) -> Dict[str, int]:
        """Generate a report of PII found in text (without modifying it).

        Args:
            text: Input text to scan for PII.

        Returns:
            Dictionary mapping PII type names to count of occurrences.
        """
        if not text:
            return {}

        report = {}
        for pattern_name, pattern, _ in self.pii_patterns:
            matches = pattern.findall(text)
            if matches:
                report[pattern_name] = len(matches)

        return report


if __name__ == "__main__":
    # Demo usage
    filter_instance = ContentFilter()

    sample_text = """
    Claimant: John Smith
    SSN: 123-45-6789
    Phone: (555) 123-4567
    Email: john.smith@example.com
    Policy: AUT-2024-12345
    The accident occurred on January 15, 2024.
    Please contact me at john.smith@example.com or 555-987-6543.
    """

    print("Original text:")
    print(sample_text)

    print("\nFiltered text:")
    print(filter_instance.filter_pii(sample_text))

    print("\nPII Report:")
    report = filter_instance.get_pii_report(sample_text)
    for pii_type, count in report.items():
        print(f"  {pii_type}: {count} occurrence(s)")

    print("\n--- Structured Data Filtering ---")
    data = {
        "claimant_name": "John Smith",
        "ssn": "123-45-6789",
        "phone": "(555) 123-4567",
        "email": "john.smith@example.com",
        "policy_number": "AUT-2024-12345",
        "claim_amount": "$15,000",
    }

    print("\nOriginal data:")
    for k, v in data.items():
        print(f"  {k}: {v}")

    print("\nFiltered data:")
    filtered = filter_instance.filter_sensitive_fields(data)
    for k, v in filtered.items():
        print(f"  {k}: {v}")
