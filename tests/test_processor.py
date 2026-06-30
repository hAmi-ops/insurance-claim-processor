"""Unit tests for Insurance Claim Document Processor.

Tests all core components using mocking to ensure tests pass
without AWS credentials.
"""

import json
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from src.prompt_templates import PromptTemplateManager
from src.content_validator import ContentValidator, ValidationResult
from src.model_invoker import ModelInvoker


class TestPromptTemplateManager(unittest.TestCase):
    """Tests for the PromptTemplateManager class."""

    def setUp(self):
        """Initialize a PromptTemplateManager for testing."""
        self.manager = PromptTemplateManager()

    def test_list_templates_returns_default_templates(self):
        """Default templates should include extract_info, generate_summary, policy_check."""
        templates = self.manager.list_templates()
        self.assertIn("extract_info", templates)
        self.assertIn("generate_summary", templates)
        self.assertIn("policy_check", templates)

    def test_get_prompt_extract_info(self):
        """get_prompt should format extract_info template with document text."""
        prompt = self.manager.get_prompt(
            "extract_info", document_text="Test document content"
        )
        self.assertIn("Test document content", prompt)
        self.assertIn("Claimant Name", prompt)
        self.assertIn("JSON", prompt)

    def test_get_prompt_generate_summary(self):
        """get_prompt should format generate_summary with extracted info."""
        prompt = self.manager.get_prompt(
            "generate_summary", extracted_info='{"claimant_name": "John Doe"}'
        )
        self.assertIn("John Doe", prompt)
        self.assertIn("summary", prompt.lower())

    def test_get_prompt_missing_template(self):
        """get_prompt should raise ValueError for nonexistent template."""
        with self.assertRaises(ValueError) as ctx:
            self.manager.get_prompt("nonexistent_template")
        self.assertIn("nonexistent_template", str(ctx.exception))

    def test_get_prompt_missing_variable(self):
        """get_prompt should raise KeyError if template variable not provided."""
        with self.assertRaises(KeyError):
            self.manager.get_prompt("extract_info")  # Missing document_text

    def test_add_template(self):
        """add_template should register a new template."""
        self.manager.add_template("custom", "Hello {name}!")
        result = self.manager.get_prompt("custom", name="World")
        self.assertEqual(result, "Hello World!")

    def test_add_template_empty_name(self):
        """add_template should reject empty name."""
        with self.assertRaises(ValueError):
            self.manager.add_template("", "template content")

    def test_add_template_empty_content(self):
        """add_template should reject empty template."""
        with self.assertRaises(ValueError):
            self.manager.add_template("test", "")

    def test_format_with_multiple_variables(self):
        """policy_check template requires multiple variables."""
        prompt = self.manager.get_prompt(
            "policy_check",
            claim_info="Auto accident claim",
            policy_context="Coverage includes collision damage",
        )
        self.assertIn("Auto accident claim", prompt)
        self.assertIn("Coverage includes collision damage", prompt)


class TestContentValidator(unittest.TestCase):
    """Tests for the ContentValidator class."""

    def setUp(self):
        """Initialize a ContentValidator for testing."""
        self.validator = ContentValidator()

    def test_valid_extraction(self):
        """Valid data with all required fields should pass validation."""
        data = {
            "claimant_name": "John Doe",
            "policy_number": "AUT-2024-12345",
            "incident_date": "2024-03-15",
            "claim_amount": "$15,000",
            "incident_description": "Vehicle collision at intersection causing significant damage.",
        }
        result = self.validator.validate_extraction(data)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)

    def test_missing_single_field(self):
        """Missing one required field should produce an error."""
        data = {
            "claimant_name": "John Doe",
            "policy_number": "AUT-2024-12345",
            "incident_date": "2024-03-15",
            "claim_amount": "$15,000",
            # Missing incident_description
        }
        result = self.validator.validate_extraction(data)
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("incident_description", result.errors[0])

    def test_missing_multiple_fields(self):
        """Missing multiple required fields should produce multiple errors."""
        data = {"claimant_name": "John Doe"}
        result = self.validator.validate_extraction(data)
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 4)

    def test_empty_field_value(self):
        """Empty string field value should be treated as missing."""
        data = {
            "claimant_name": "",
            "policy_number": "AUT-2024-12345",
            "incident_date": "2024-03-15",
            "claim_amount": "$15,000",
            "incident_description": "A vehicle accident occurred.",
        }
        result = self.validator.validate_extraction(data)
        self.assertFalse(result.is_valid)
        self.assertIn("empty", result.errors[0].lower())

    def test_none_field_value(self):
        """None field value should be treated as missing."""
        data = {
            "claimant_name": "John Doe",
            "policy_number": None,
            "incident_date": "2024-03-15",
            "claim_amount": "$15,000",
            "incident_description": "A vehicle accident occurred.",
        }
        result = self.validator.validate_extraction(data)
        self.assertFalse(result.is_valid)

    def test_invalid_claim_amount_warning(self):
        """Non-numeric claim amount should produce a warning."""
        data = {
            "claimant_name": "John Doe",
            "policy_number": "AUT-2024-12345",
            "incident_date": "2024-03-15",
            "claim_amount": "about fifteen thousand",
            "incident_description": "A vehicle accident caused damage to the car.",
        }
        result = self.validator.validate_extraction(data)
        self.assertTrue(result.is_valid)  # Still valid, just warned
        self.assertTrue(len(result.warnings) > 0)

    def test_short_description_warning(self):
        """Very short description should produce a warning."""
        data = {
            "claimant_name": "John Doe",
            "policy_number": "AUT-2024-12345",
            "incident_date": "2024-03-15",
            "claim_amount": "$15,000",
            "incident_description": "Crash",
        }
        result = self.validator.validate_extraction(data)
        self.assertTrue(result.is_valid)
        self.assertTrue(len(result.warnings) > 0)

    def test_validate_json_string_valid(self):
        """Valid JSON string should parse correctly."""
        json_str = '{"claimant_name": "Jane Smith", "policy_number": "HOM-123"}'
        result, error = self.validator.validate_json_string(json_str)
        self.assertIsNotNone(result)
        self.assertIsNone(error)
        self.assertEqual(result["claimant_name"], "Jane Smith")

    def test_validate_json_string_with_surrounding_text(self):
        """JSON embedded in text should be extracted."""
        text = 'Here is the extracted information:\n{"claimant_name": "Jane Smith", "policy_number": "HOM-123"}\nEnd of response.'
        result, error = self.validator.validate_json_string(text)
        self.assertIsNotNone(result)
        self.assertIsNone(error)
        self.assertEqual(result["claimant_name"], "Jane Smith")

    def test_validate_json_string_invalid(self):
        """Invalid JSON should return an error message."""
        text = "This is not JSON at all"
        result, error = self.validator.validate_json_string(text)
        self.assertIsNone(result)
        self.assertIsNotNone(error)

    def test_validate_json_string_empty(self):
        """Empty string should return an error."""
        result, error = self.validator.validate_json_string("")
        self.assertIsNone(result)
        self.assertIn("Empty", error)

    def test_empty_dict(self):
        """Empty dict should fail validation with all fields missing."""
        result = self.validator.validate_extraction({})
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 5)


class TestModelInvoker(unittest.TestCase):
    """Tests for the ModelInvoker class with mocked boto3."""

    @patch("src.model_invoker.boto3.Session")
    def test_successful_invocation(self, mock_session_class):
        """Successful model invocation should return response text."""
        # Setup mock
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.client.return_value = mock_client

        response_body = json.dumps({
            "content": [{"type": "text", "text": '{"claimant_name": "Test User"}'}],
        })
        mock_body = MagicMock()
        mock_body.read.return_value = response_body.encode("utf-8")
        mock_client.invoke_model.return_value = {"body": mock_body}

        # Test
        invoker = ModelInvoker(profile_name="test-profile")
        result = invoker.invoke("Test prompt", model_id="anthropic.claude-3-sonnet-20240229-v1:0")

        self.assertEqual(result, '{"claimant_name": "Test User"}')
        mock_client.invoke_model.assert_called_once()

    @patch("src.model_invoker.boto3.Session")
    def test_invocation_uses_correct_api_format(self, mock_session_class):
        """Invocation should use Claude 3 Messages API format."""
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.client.return_value = mock_client

        response_body = json.dumps({
            "content": [{"type": "text", "text": "response"}],
        })
        mock_body = MagicMock()
        mock_body.read.return_value = response_body.encode("utf-8")
        mock_client.invoke_model.return_value = {"body": mock_body}

        invoker = ModelInvoker()
        invoker.invoke("My prompt", temperature=0.5, max_tokens=500)

        # Verify the request body format
        call_kwargs = mock_client.invoke_model.call_args[1]
        request_body = json.loads(call_kwargs["body"])
        self.assertEqual(request_body["anthropic_version"], "bedrock-2023-05-31")
        self.assertEqual(request_body["messages"][0]["role"], "user")
        self.assertEqual(request_body["messages"][0]["content"], "My prompt")
        self.assertEqual(request_body["temperature"], 0.5)
        self.assertEqual(request_body["max_tokens"], 500)

    @patch("src.model_invoker.time.sleep")
    @patch("src.model_invoker.boto3.Session")
    def test_retry_on_throttling(self, mock_session_class, mock_sleep):
        """ThrottlingException should trigger retry with backoff."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.client.return_value = mock_client

        # First call throttled, second succeeds
        throttle_error = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "InvokeModel",
        )
        response_body = json.dumps({
            "content": [{"type": "text", "text": "success after retry"}],
        })
        mock_body = MagicMock()
        mock_body.read.return_value = response_body.encode("utf-8")

        mock_client.invoke_model.side_effect = [
            throttle_error,
            {"body": mock_body},
        ]

        invoker = ModelInvoker(base_delay=1.0)
        result = invoker.invoke("Test prompt")

        self.assertEqual(result, "success after retry")
        self.assertEqual(mock_client.invoke_model.call_count, 2)
        mock_sleep.assert_called_once_with(1.0)  # First retry: base_delay * 2^0

    @patch("src.model_invoker.time.sleep")
    @patch("src.model_invoker.boto3.Session")
    def test_retry_exhaustion(self, mock_session_class, mock_sleep):
        """All retries exhausted should raise the last exception."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.client.return_value = mock_client

        throttle_error = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "InvokeModel",
        )
        mock_client.invoke_model.side_effect = throttle_error

        invoker = ModelInvoker(max_retries=3, base_delay=1.0)

        with self.assertRaises(ClientError):
            invoker.invoke("Test prompt")

        self.assertEqual(mock_client.invoke_model.call_count, 3)
        # Verify exponential backoff: 1.0, 2.0 (only 2 sleeps for 3 attempts)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("src.model_invoker.boto3.Session")
    def test_non_retryable_error_raises_immediately(self, mock_session_class):
        """Non-retryable errors should raise immediately without retry."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.client.return_value = mock_client

        access_error = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Not authorized"}},
            "InvokeModel",
        )
        mock_client.invoke_model.side_effect = access_error

        invoker = ModelInvoker()

        with self.assertRaises(ClientError):
            invoker.invoke("Test prompt")

        self.assertEqual(mock_client.invoke_model.call_count, 1)

    @patch("src.model_invoker.boto3.Session")
    def test_default_model_id(self, mock_session_class):
        """Default model should be Claude Sonnet 4.6 via inference profile."""
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.client.return_value = mock_client

        response_body = json.dumps({
            "content": [{"type": "text", "text": "response"}],
        })
        mock_body = MagicMock()
        mock_body.read.return_value = response_body.encode("utf-8")
        mock_client.invoke_model.return_value = {"body": mock_body}

        invoker = ModelInvoker()
        invoker.invoke("prompt")

        call_kwargs = mock_client.invoke_model.call_args[1]
        self.assertEqual(
            call_kwargs["modelId"], "us.anthropic.claude-sonnet-4-6"
        )


if __name__ == "__main__":
    unittest.main()
