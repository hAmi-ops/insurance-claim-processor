"""Insurance Claim Document Processor.

Core processing logic that orchestrates document retrieval from S3,
information extraction via Amazon Bedrock, and summary generation.
"""

import json
import logging
from typing import Any, Dict, Optional

import boto3

from .content_validator import ContentValidator
from .model_invoker import ModelInvoker
from .prompt_templates import PromptTemplateManager

logger = logging.getLogger(__name__)

# Default model - Claude 3 Sonnet (replaces deprecated anthropic.claude-v2)
DEFAULT_MODEL_ID = "us.anthropic.claude-sonnet-4-6"


def process_document(
    bucket: str,
    key: str,
    model_id: Optional[str] = None,
    profile_name: Optional[str] = None,
    region_name: str = "us-east-1",
) -> Dict[str, Any]:
    """Process an insurance claim document from S3.

    Retrieves the document from S3, extracts structured information using
    Amazon Bedrock, validates the extraction, and generates a summary.

    Args:
        bucket: S3 bucket name containing the claim document.
        key: S3 object key for the claim document.
        model_id: Bedrock model ID to use. Defaults to Claude 3 Sonnet.
        profile_name: AWS profile name for credentials.
        region_name: AWS region for services.

    Returns:
        Dictionary containing:
            - extracted_info: Parsed JSON dict of extracted claim fields.
            - summary: Generated text summary of the claim.
            - validation: Validation result details.

    Raises:
        Exception: If document retrieval or processing fails.
    """
    if model_id is None:
        model_id = DEFAULT_MODEL_ID

    logger.info("Processing document: s3://%s/%s with model %s", bucket, key, model_id)

    # Initialize components
    template_manager = PromptTemplateManager()
    model_invoker = ModelInvoker(
        profile_name=profile_name, region_name=region_name
    )
    validator = ContentValidator()

    # Retrieve document from S3
    session_kwargs = {}
    if profile_name:
        session_kwargs["profile_name"] = profile_name
    session = boto3.Session(**session_kwargs)
    s3_client = session.client("s3", region_name=region_name)

    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        document_text = response["Body"].read().decode("utf-8")
        logger.info("Retrieved document (%d chars) from S3", len(document_text))
    except Exception as e:
        logger.error("Failed to retrieve document from S3: %s", str(e))
        raise

    # Extract information using Bedrock
    extraction_prompt = template_manager.get_prompt(
        "extract_info", document_text=document_text
    )

    extraction_response = model_invoker.invoke(
        prompt=extraction_prompt,
        model_id=model_id,
        temperature=0.0,
        max_tokens=1000,
    )

    # Parse and validate extraction
    parsed_data, parse_error = validator.validate_json_string(extraction_response)

    if parse_error:
        logger.warning("JSON parsing issue: %s", parse_error)
        extracted_info = {"raw_response": extraction_response, "parse_error": parse_error}
        validation_result = validator.validate_extraction({})
    else:
        extracted_info = parsed_data
        validation_result = validator.validate_extraction(parsed_data)

    # Generate summary
    summary_prompt = template_manager.get_prompt(
        "generate_summary", extracted_info=json.dumps(extracted_info, indent=2)
    )

    summary = model_invoker.invoke(
        prompt=summary_prompt,
        model_id=model_id,
        temperature=0.7,
        max_tokens=500,
    )

    logger.info("Document processing complete. Valid extraction: %s", validation_result.is_valid)

    return {
        "extracted_info": extracted_info,
        "summary": summary,
        "validation": {
            "is_valid": validation_result.is_valid,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
        },
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = process_document(
        bucket="claim-documents-poc-jh",
        key="claims/claim1.txt",
        profile_name="wbr-admin",
    )
    print(json.dumps(result, indent=2))
