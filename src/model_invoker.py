"""Model Invoker for Amazon Bedrock.

Provides a wrapper around the Amazon Bedrock Runtime client with
retry logic, error handling, and logging for foundation model invocations.
"""

import json
import logging
import time
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ModelInvoker:
    """Wrapper for Amazon Bedrock Runtime model invocations.

    Handles model invocation with retry logic, exponential backoff,
    and comprehensive error handling.

    Attributes:
        client: The boto3 bedrock-runtime client.
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds for exponential backoff.
    """

    # Default model ID using Claude Sonnet 4.6 via inference profile
    DEFAULT_MODEL_ID = "us.anthropic.claude-sonnet-4-6"

    def __init__(
        self,
        profile_name: Optional[str] = None,
        region_name: str = "us-east-1",
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> None:
        """Initialize the ModelInvoker.

        Args:
            profile_name: AWS profile name to use. If None, uses default credentials.
            region_name: AWS region for the Bedrock service.
            max_retries: Maximum number of retry attempts on transient failures.
            base_delay: Base delay in seconds for exponential backoff.
        """
        session_kwargs = {}
        if profile_name:
            session_kwargs["profile_name"] = profile_name

        session = boto3.Session(**session_kwargs)
        self.client = session.client("bedrock-runtime", region_name=region_name)
        self.max_retries = max_retries
        self.base_delay = base_delay

    def invoke(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> str:
        """Invoke a Bedrock foundation model with retry logic.

        Uses the Claude 3 Messages API format for all invocations.

        Args:
            prompt: The prompt text to send to the model.
            model_id: The Bedrock model ID. Defaults to Claude 3 Sonnet.
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Maximum tokens in the response.

        Returns:
            The model's text response.

        Raises:
            ClientError: If all retry attempts are exhausted.
            Exception: For unexpected errors during invocation.
        """
        if model_id is None:
            model_id = self.DEFAULT_MODEL_ID

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        })

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    "Invoking model %s (attempt %d/%d)",
                    model_id,
                    attempt + 1,
                    self.max_retries,
                )

                response = self.client.invoke_model(
                    modelId=model_id,
                    body=body,
                    contentType="application/json",
                    accept="application/json",
                )

                response_body = json.loads(response["body"].read())
                result = response_body["content"][0]["text"]

                logger.info(
                    "Model invocation successful. Response length: %d chars",
                    len(result),
                )
                return result

            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                last_exception = e

                if error_code in ("ThrottlingException", "ModelTimeoutException"):
                    if attempt < self.max_retries - 1:
                        delay = self.base_delay * (2 ** attempt)
                        logger.warning(
                            "Received %s on attempt %d/%d. Retrying in %.1f seconds.",
                            error_code,
                            attempt + 1,
                            self.max_retries,
                            delay,
                        )
                        time.sleep(delay)
                    else:
                        logger.warning(
                            "Received %s on final attempt %d/%d.",
                            error_code,
                            attempt + 1,
                            self.max_retries,
                        )
                else:
                    logger.error(
                        "Non-retryable error from Bedrock: %s - %s",
                        error_code,
                        e.response["Error"]["Message"],
                    )
                    raise

            except Exception as e:
                logger.error("Unexpected error during model invocation: %s", str(e))
                raise

        logger.error("All %d retry attempts exhausted.", self.max_retries)
        raise last_exception
