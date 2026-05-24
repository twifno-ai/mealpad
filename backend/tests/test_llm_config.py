import pytest

from app.config import settings
from app.services.llm_config import AIServiceError, ensure_provider_ready, resolve_provider


@pytest.fixture(autouse=True)
def reset_settings(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "")
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")


def test_auto_detect_prefers_anthropic():
    settings.anthropic_api_key = "sk-ant"
    settings.openai_api_key = "sk-openai"
    assert resolve_provider() == "anthropic"


def test_auto_detect_falls_back_to_openai():
    settings.openai_api_key = "sk-openai"
    assert resolve_provider() == "openai"


def test_auto_detect_empty_when_no_keys():
    assert resolve_provider() == ""


def test_explicit_openai():
    settings.ai_provider = "openai"
    assert resolve_provider() == "openai"


def test_explicit_openai_requires_key():
    settings.ai_provider = "openai"
    with pytest.raises(AIServiceError, match="OPENAI_API_KEY"):
        ensure_provider_ready("openai")


def test_invalid_provider():
    settings.ai_provider = "gemini"
    with pytest.raises(AIServiceError, match="无效的 AI_PROVIDER"):
        resolve_provider()
