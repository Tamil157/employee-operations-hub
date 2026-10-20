from typing import Any

import boto3
from strands.models.anthropic import AnthropicModel
from strands.models.bedrock import BedrockModel
from strands.models.openai import OpenAIModel

from app.config import Settings


def _openai_compatible_params(settings: Settings) -> dict[str, Any]:
    if settings.llm_provider == "groq" and settings.llm_model.startswith("qwen/"):
        return {"extra_body": {"reasoning_effort": "none"}}
    if settings.llm_provider == "groq" and settings.llm_model.startswith("openai/gpt-oss-"):
        return {"extra_body": {"include_reasoning": False, "reasoning_effort": "low"}}
    return {}


def build_language_model(settings: Settings) -> Any:
    """Build the selected Strands model without exposing credentials to the browser."""
    if settings.llm_provider == "anthropic":
        return AnthropicModel(
            model_id=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            client_args={"api_key": settings.provider_api_key()},
        )

    if settings.llm_provider == "bedrock":
        session = None
        if settings.aws_profile:
            session = boto3.Session(profile_name=settings.aws_profile, region_name=settings.aws_region)
        return BedrockModel(
            model_id=settings.llm_model,
            boto_session=session,
            region_name=settings.aws_region,
            endpoint_url=settings.provider_base_url,
            max_tokens=settings.llm_max_tokens,
        )

    return OpenAIModel(
        model_id=settings.llm_model,
        params=_openai_compatible_params(settings),
        client_args={
            "api_key": settings.provider_api_key(),
            "base_url": settings.provider_base_url,
        },
    )
