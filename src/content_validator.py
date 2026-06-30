"""Content Validator for Insurance Claim Extractions.

Validates the structure and completeness of data extracted from
insurance claim documents by the foundation model.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation operation.

    Attributes:
        is_valid: Whether the data passed all required validations.
        errors: List of critical validation errors.
        warnings: List of non-critical validation warnings.
    """

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ContentValidator:
    """Validates extracted insurance claim data.

    Checks for required fields, data format, and completeness
    of information extracted from claim documents.
    """

    REQUIRED_FIELDS = [
        "claimant_name",
        "policy_number",
        "incident_date",
        "claim_amount",
        "incident_description",
    ]

    def validate_extraction(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate extracted claim data for required fields and quality.

        Args:
            data: Dictionary of extracted claim information.

        Returns:
            ValidationResult with is_valid status, errors, and warnings.
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Check for required fields
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in data:
                errors.append(f"Missing required field: {field_name}")
            elif data[field_name] is None or str(data[field_name]).strip() == "":
                errors.append(f"Required field is empty: {field_name}")

        # Additional quality checks
        if "claim_amount" in data and data["claim_amount"]:
            amount_str = str(data["claim_amount"])
            # Remove common currency symbols and commas for validation
            cleaned = amount_str.replace("$", "").replace(",", "").strip()
            try:
                float(cleaned)
            except (ValueError, TypeError):
                warnings.append(
                    f"claim_amount may not be a valid number: '{data['claim_amount']}'"
                )

        if "incident_description" in data and data["incident_description"]:
            desc = str(data["incident_description"])
            if len(desc) < 10:
                warnings.append(
                    "incident_description seems unusually short (less than 10 chars)"
                )

        is_valid = len(errors) == 0

        logger.info(
            "Validation result: valid=%s, errors=%d, warnings=%d",
            is_valid,
            len(errors),
            len(warnings),
        )

        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)

    def validate_json_string(
        self, text: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Parse and validate a JSON string.

        Attempts to parse the text as JSON. Handles cases where the model
        may include extra text around the JSON.

        Args:
            text: String that should contain JSON data.

        Returns:
            Tuple of (parsed_dict, error_message).
            On success: (dict, None)
            On failure: (None, error_description)
        """
        if not text or not text.strip():
            return None, "Empty input text"

        # First try direct parsing
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, dict):
                return parsed, None
            return None, f"Expected JSON object, got {type(parsed).__name__}"
        except json.JSONDecodeError:
            pass

        # Try to find JSON object within the text
        text_stripped = text.strip()
        start_idx = text_stripped.find("{")
        end_idx = text_stripped.rfind("}")

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_candidate = text_stripped[start_idx:end_idx + 1]
            try:
                parsed = json.loads(json_candidate)
                if isinstance(parsed, dict):
                    logger.info(
                        "Extracted JSON from surrounding text (chars %d-%d)",
                        start_idx,
                        end_idx,
                    )
                    return parsed, None
            except json.JSONDecodeError as e:
                return None, f"Found JSON-like structure but failed to parse: {str(e)}"

        return None, "No valid JSON object found in text"
