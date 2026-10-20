import pytest

from app import model_provider
from app.config import Settings


def test_groq_uses_existing_environment_names_as_fallbacks() -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="groq",
        llm_model="qwen/qwen3.8-27b",
        groq_api_key="groq-test-key",
    )

    assert settings.provider_label == "Groq"
    assert settings.provider_base_url == "https://api.groq.com/openai/v1"
    assert settings.provider_api_key() == "groq-test-key"


def test_generic_key_and_custom_url_override_provider_defaults() -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="vllm",
        llm_model="Qwen/Qwen3-8B",
        llm_api_key="server-key",
        llm_base_url="http://localhost:8000/v1/",
    )

    assert settings.provider_label == "vLLM"
    assert settings.provider_base_url == "http://localhost:8000/v1"
    assert settings.provider_api_key() == "server-key"


def test_ollama_allows_local_server_without_a_secret() -> None:
    settings = Settings(_env_file=None, llm_provider="ollama", llm_model="llama3.2")

    assert settings.provider_base_url == "http://localhost:11434/v1"
    assert settings.provider_api_key() == "local-provider"


def test_vllm_default_does_not_conflict_with_the_application_api_port() -> None:
    settings = Settings(_env_file=None, llm_provider="vllm", llm_model="Qwen/test")

    assert settings.provider_base_url == "http://localhost:8001/v1"


def test_hosted_provider_requires_a_credential() -> None:
    settings = Settings(_env_file=None, llm_provider="anthropic", llm_model="claude-test")

    with pytest.raises(ValueError, match="Anthropic requires"):
        settings.provider_api_key()


@pytest.mark.parametrize(
    ("provider", "model"),
    [
        ("openai", "gpt-test"),
        ("groq", "qwen/test"),
        ("grok", "grok-test"),
        ("ollama", "llama3.2"),
        ("vllm", "Qwen/test"),
    ],
)
def test_openai_compatible_providers_use_one_adapter(monkeypatch, provider: str, model: str) -> None:
    captured: dict[str, object] = {}

    def fake_openai_model(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return "openai-compatible-model"

    monkeypatch.setattr(model_provider, "OpenAIModel", fake_openai_model)
    settings = Settings(
        _env_file=None,
        llm_provider=provider,
        llm_model=model,
        llm_api_key="test-key",
    )

    assert model_provider.build_language_model(settings) == "openai-compatible-model"
    assert captured["model_id"] == model
    assert captured["client_args"] == {
        "api_key": "test-key",
        "base_url": settings.provider_base_url,
    }


def test_anthropic_uses_native_adapter(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_anthropic_model(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return "anthropic-model"

    monkeypatch.setattr(model_provider, "AnthropicModel", fake_anthropic_model)
    settings = Settings(
        _env_file=None,
        llm_provider="anthropic",
        llm_model="claude-test",
        llm_api_key="test-key",
    )

    assert model_provider.build_language_model(settings) == "anthropic-model"
    assert captured["model_id"] == "claude-test"
    assert captured["client_args"] == {"api_key": "test-key"}


def test_bedrock_uses_native_adapter(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_bedrock_model(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return "bedrock-model"

    monkeypatch.setattr(model_provider, "BedrockModel", fake_bedrock_model)
    settings = Settings(
        _env_file=None,
        llm_provider="bedrock",
        llm_model="anthropic.claude-test-v1:0",
        aws_region="ap-south-1",
    )

    assert model_provider.build_language_model(settings) == "bedrock-model"
    assert captured["model_id"] == "anthropic.claude-test-v1:0"
    assert captured["region_name"] == "ap-south-1"
