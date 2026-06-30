"""Model Comparison for Insurance Claim Processing.

Compares performance of different Amazon Bedrock foundation models
on insurance claim document processing tasks.
"""

import argparse
import json
import logging
import time
from typing import Any, Dict, List, Optional

from .content_validator import ContentValidator
from .model_invoker import ModelInvoker
from .prompt_templates import PromptTemplateManager

logger = logging.getLogger(__name__)

# Updated model IDs - Claude 4 family via inference profiles (replacing Legacy Claude 3 Sonnet/Haiku)
DEFAULT_MODELS = [
    "us.anthropic.claude-sonnet-4-6",
    "us.anthropic.claude-haiku-4-5-20251001-v1:0",
]


def compare_models(
    document_text: str,
    models_list: Optional[List[str]] = None,
    profile_name: Optional[str] = None,
    region_name: str = "us-east-1",
) -> Dict[str, Any]:
    """Compare multiple Bedrock models on the same document.

    Measures latency, output length, and extraction completeness for
    each model processing the same insurance claim document.

    Args:
        document_text: The insurance claim document text to process.
        models_list: List of Bedrock model IDs to compare.
            Defaults to Claude 3 Sonnet and Claude 3 Haiku.
        profile_name: AWS profile name for credentials.
        region_name: AWS region for Bedrock.

    Returns:
        Dictionary with model comparison results including:
            - Per-model metrics (latency, output length, completeness)
            - Summary comparison
    """
    if models_list is None:
        models_list = DEFAULT_MODELS

    template_manager = PromptTemplateManager()
    model_invoker = ModelInvoker(
        profile_name=profile_name, region_name=region_name
    )
    validator = ContentValidator()

    prompt = template_manager.get_prompt("extract_info", document_text=document_text)

    results: Dict[str, Any] = {}

    for model_id in models_list:
        logger.info("Testing model: %s", model_id)

        try:
            start_time = time.time()
            response = model_invoker.invoke(
                prompt=prompt,
                model_id=model_id,
                temperature=0.0,
                max_tokens=1000,
            )
            elapsed_time = time.time() - start_time

            # Attempt to parse and validate
            parsed_data, parse_error = validator.validate_json_string(response)

            if parsed_data:
                validation = validator.validate_extraction(parsed_data)
                fields_found = sum(
                    1
                    for f in ContentValidator.REQUIRED_FIELDS
                    if f in parsed_data and parsed_data[f]
                )
            else:
                validation = None
                fields_found = 0

            results[model_id] = {
                "latency_seconds": round(elapsed_time, 3),
                "output_length": len(response),
                "fields_found": fields_found,
                "total_required_fields": len(ContentValidator.REQUIRED_FIELDS),
                "extraction_completeness": fields_found / len(ContentValidator.REQUIRED_FIELDS),
                "parse_successful": parse_error is None,
                "validation_passed": validation.is_valid if validation else False,
                "output_sample": response[:200] + "..." if len(response) > 200 else response,
            }

            logger.info(
                "Model %s: %.3fs, %d chars, %d/%d fields",
                model_id,
                elapsed_time,
                len(response),
                fields_found,
                len(ContentValidator.REQUIRED_FIELDS),
            )

        except Exception as e:
            logger.error("Error testing model %s: %s", model_id, str(e))
            results[model_id] = {
                "error": str(e),
                "latency_seconds": None,
                "output_length": 0,
                "fields_found": 0,
                "total_required_fields": len(ContentValidator.REQUIRED_FIELDS),
                "extraction_completeness": 0.0,
            }

    # Add summary comparison
    successful_models = {k: v for k, v in results.items() if "error" not in v}
    if successful_models:
        fastest = min(successful_models, key=lambda k: successful_models[k]["latency_seconds"])
        most_complete = max(successful_models, key=lambda k: successful_models[k]["fields_found"])
        results["_summary"] = {
            "fastest_model": fastest,
            "fastest_latency": successful_models[fastest]["latency_seconds"],
            "most_complete_model": most_complete,
            "most_complete_fields": successful_models[most_complete]["fields_found"],
            "models_tested": len(models_list),
            "models_successful": len(successful_models),
        }

    return results


def main() -> None:
    """CLI entry point for model comparison."""
    parser = argparse.ArgumentParser(
        description="Compare Bedrock models on insurance claim processing"
    )
    parser.add_argument(
        "document_path",
        help="Path to the claim document text file",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Model IDs to compare",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="AWS profile name",
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path for results JSON",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Read document
    with open(args.document_path, "r") as f:
        document_text = f.read()

    logger.info("Document loaded: %d chars", len(document_text))
    logger.info("Comparing models: %s", ", ".join(args.models))

    # Run comparison
    results = compare_models(
        document_text=document_text,
        models_list=args.models,
        profile_name=args.profile,
        region_name=args.region,
    )

    # Output results
    output_json = json.dumps(results, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)
        logger.info("Results saved to: %s", args.output)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
