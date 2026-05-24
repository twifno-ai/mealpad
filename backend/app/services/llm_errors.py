"""Turn LLM SDK exceptions into concise Chinese messages for API responses."""


def _error_payload(body: object) -> dict | None:
    if not isinstance(body, dict):
        return None
    err = body.get("error")
    return err if isinstance(err, dict) else None


def _error_code(body: object) -> str | None:
    payload = _error_payload(body)
    if not payload:
        return None
    code = payload.get("code") or payload.get("type")
    return str(code) if code else None


def _error_message(body: object) -> str | None:
    payload = _error_payload(body)
    if payload:
        msg = payload.get("message")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
    if isinstance(body, dict):
        msg = body.get("message")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
    return None


def format_llm_api_error(provider: str, exc: Exception) -> str:
    label = "OpenAI" if provider == "openai" else "Anthropic"
    status = getattr(exc, "status_code", None)
    body = getattr(exc, "body", None)
    code = _error_code(body) or getattr(exc, "code", None)
    if code is not None:
        code = str(code)

    if status == 401:
        return f"{label} API Key 无效，请检查 backend/.env 中的密钥是否正确"
    if status == 403:
        return f"{label} 无权访问该模型或服务，请检查账户权限与模型名称"
    if status == 404:
        model_hint = "OPENAI_MODEL" if provider == "openai" else "ANTHROPIC_MODEL"
        return f"{label} 模型不存在或不可用，请检查 .env 中的 {model_hint}"
    if status == 429:
        if code in {"insufficient_quota", "billing_not_active"} or (
            isinstance(body, dict)
            and "insufficient_quota" in str(body).lower()
        ):
            other = "Anthropic（设置 AI_PROVIDER=anthropic）" if provider == "openai" else "OpenAI（设置 AI_PROVIDER=openai）"
            return f"{label} 账户额度已用尽，请检查计费/充值，或改用 {other}"
        return f"{label} 请求过于频繁或配额受限，请稍后重试"
    if status == 400:
        msg = _error_message(body)
        if msg:
            return f"{label} 请求无效：{msg}"
    if status == 503 or status == 529:
        return f"{label} 服务暂时不可用，请稍后重试"

    msg = _error_message(body)
    if msg:
        return f"{label} 调用失败：{msg}"
    if status is not None:
        return f"{label} 调用失败（HTTP {status}）"
    return f"{label} 调用失败：{exc}"
