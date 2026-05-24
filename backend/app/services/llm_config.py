class AIServiceError(Exception):
    """Raised when AI provider is misconfigured or API calls fail."""


def resolve_provider() -> str:
    from ..config import settings

    explicit = settings.ai_provider.strip().lower()
    if explicit and explicit not in {"anthropic", "openai"}:
        raise AIServiceError(f"无效的 AI_PROVIDER：{settings.ai_provider}")
    if explicit:
        return explicit
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.openai_api_key:
        return "openai"
    return ""


def ensure_provider_ready(provider: str) -> None:
    from ..config import settings

    if provider == "anthropic" and not settings.anthropic_api_key:
        raise AIServiceError("未配置 Anthropic API Key，请在 backend/.env 中设置 ANTHROPIC_API_KEY")
    if provider == "openai" and not settings.openai_api_key:
        raise AIServiceError("未配置 OpenAI API Key，请在 backend/.env 中设置 OPENAI_API_KEY")


def get_active_provider() -> str:
    provider = resolve_provider()
    if not provider:
        raise AIServiceError(
            "未配置 AI 服务：请在 backend/.env 中设置 ANTHROPIC_API_KEY 或 OPENAI_API_KEY"
        )
    ensure_provider_ready(provider)
    return provider
