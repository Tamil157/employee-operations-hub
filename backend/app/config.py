from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Pydantic reads settings from this file, while the OpenAI-compatible client
# needs the same key at runtime. Loading it once supports both mechanisms.
load_dotenv(ROOT_ENV_FILE, override=False)

ProviderName = Literal["openai", "groq", "grok", "anthropic", "bedrock", "ollama", "vllm"]


class Settings(BaseSettings):
    app_name: str = "Employee Operations Hub API"
    environment: str = "development"
    database_path: Path = Path("data/employees.db")
    cors_origins: str = "http://localhost:5173"

    llm_provider: ProviderName = "groq"
    llm_model: str = Field(
        default="qwen/qwen3.8-27b",
        validation_alias=AliasChoices("LLM_MODEL", "GROQ_MODEL"),
    )
    llm_api_key: SecretStr = SecretStr("")
    llm_base_url: str | None = None
    llm_max_tokens: int = Field(default=1024, ge=1, le=16_384)

    openai_api_key: SecretStr = SecretStr("")
    groq_api_key: SecretStr = SecretStr("")
    xai_api_key: SecretStr = SecretStr("")
    anthropic_api_key: SecretStr = SecretStr("")
    ollama_api_key: SecretStr = SecretStr("")
    vllm_api_key: SecretStr = SecretStr("")
    aws_region: str = "us-east-1"
    aws_profile: str | None = None

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def provider_label(self) -> str:
        return {
            "openai": "OpenAI",
            "groq": "Groq",
            "grok": "Grok (xAI)",
            "anthropic": "Anthropic",
            "bedrock": "Amazon Bedrock",
            "ollama": "Ollama",
            "vllm": "vLLM",
        }[self.llm_provider]

    @property
    def provider_base_url(self) -> str | None:
        if self.llm_provider == "bedrock":
            return self.llm_base_url
        if self.llm_base_url:
            return self.llm_base_url.rstrip("/")
        return {
            "openai": "https://api.openai.com/v1",
            "groq": "https://api.groq.com/openai/v1",
            "grok": "https://api.x.ai/v1",
            "ollama": "http://localhost:11434/v1",
            "vllm": "http://localhost:8001/v1",
        }.get(self.llm_provider)

    def provider_api_key(self) -> str:
        generic_key = self.llm_api_key.get_secret_value().strip()
        if generic_key:
            return generic_key

        provider_keys = {
            "openai": self.openai_api_key,
            "groq": self.groq_api_key,
            "grok": self.xai_api_key,
            "anthropic": self.anthropic_api_key,
            "ollama": self.ollama_api_key,
            "vllm": self.vllm_api_key,
        }
        provider_key = provider_keys.get(self.llm_provider)
        if provider_key:
            key = provider_key.get_secret_value().strip()
            if key:
                return key

        if self.llm_provider in {"ollama", "vllm"}:
            return "local-provider"
        raise ValueError(
            f"{self.provider_label} requires LLM_API_KEY or its provider-specific API key in .env."
        )
