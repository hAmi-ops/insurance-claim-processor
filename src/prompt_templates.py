"""Prompt Template Manager for Insurance Claim Processing.

Provides a centralized template management system for all prompts used
in document processing, information extraction, and policy checking.
"""

from typing import Dict, List


class PromptTemplateManager:
    """Manages prompt templates for insurance claim document processing.

    Provides methods to retrieve, add, and list prompt templates used
    for interacting with Amazon Bedrock foundation models.

    Attributes:
        templates: Dictionary mapping template names to template strings.
    """

    def __init__(self) -> None:
        """Initialize the PromptTemplateManager with default templates."""
        self.templates: Dict[str, str] = {
            "extract_info": (
                "Extract the following information from this insurance claim document:\n"
                "- Claimant Name\n"
                "- Policy Number\n"
                "- Incident Date\n"
                "- Claim Amount\n"
                "- Incident Description\n\n"
                "Document:\n{document_text}\n\n"
                "Return the information in JSON format with these exact keys:\n"
                "claimant_name, policy_number, incident_date, claim_amount, "
                "incident_description\n\n"
                "Return ONLY valid JSON, no additional text."
            ),
            "generate_summary": (
                "Based on this extracted claim information:\n"
                "{extracted_info}\n\n"
                "Generate a concise summary of the insurance claim in 2-3 sentences. "
                "Include the type of incident, the claimant, and the amount claimed."
            ),
            "policy_check": (
                "Given the following insurance claim information:\n"
                "{claim_info}\n\n"
                "And the following relevant policy excerpts:\n"
                "{policy_context}\n\n"
                "Determine whether this claim is likely covered under the policy. "
                "Provide a brief explanation of your assessment including:\n"
                "- Coverage determination (likely covered / likely not covered / unclear)\n"
                "- Relevant policy provisions\n"
                "- Any concerns or additional information needed"
            ),
        }

    def get_prompt(self, template_name: str, **kwargs: str) -> str:
        """Retrieve and format a prompt template.

        Args:
            template_name: Name of the template to retrieve.
            **kwargs: Keyword arguments to format into the template.

        Returns:
            Formatted prompt string.

        Raises:
            ValueError: If template_name is not found.
            KeyError: If required template variables are not provided.
        """
        template = self.templates.get(template_name)
        if template is None:
            raise ValueError(
                f"Template '{template_name}' not found. "
                f"Available templates: {self.list_templates()}"
            )
        return template.format(**kwargs)

    def add_template(self, name: str, template: str) -> None:
        """Add a new prompt template.

        Args:
            name: Name for the new template.
            template: Template string with {variable} placeholders.

        Raises:
            ValueError: If name is empty or template is empty.
        """
        if not name or not name.strip():
            raise ValueError("Template name cannot be empty.")
        if not template or not template.strip():
            raise ValueError("Template content cannot be empty.")
        self.templates[name] = template

    def list_templates(self) -> List[str]:
        """List all available template names.

        Returns:
            List of template name strings.
        """
        return list(self.templates.keys())
