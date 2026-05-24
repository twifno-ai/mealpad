import pytest

from app.services.llm_errors import format_llm_api_error


class FakeApiError(Exception):
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Error code: {status_code}")


def test_openai_insufficient_quota():
    exc = FakeApiError(
        429,
        {
            "error": {
                "message": "You exceeded your current quota",
                "type": "insufficient_quota",
                "code": "insufficient_quota",
            }
        },
    )
    msg = format_llm_api_error("openai", exc)
    assert "额度已用尽" in msg
    assert "Anthropic" in msg


def test_openai_invalid_api_key():
    exc = FakeApiError(
        401,
        {"error": {"message": "Incorrect API key", "code": "invalid_api_key"}},
    )
    msg = format_llm_api_error("openai", exc)
    assert "API Key 无效" in msg


def test_anthropic_auth_error():
    exc = FakeApiError(
        401,
        {"error": {"type": "authentication_error", "message": "invalid x-api-key"}},
    )
    msg = format_llm_api_error("anthropic", exc)
    assert "Anthropic" in msg
    assert "API Key 无效" in msg


def test_generic_status_with_message():
    exc = FakeApiError(400, {"error": {"message": "model not found", "code": "model_not_found"}})
    msg = format_llm_api_error("openai", exc)
    assert "model not found" in msg
