from datetime import date as Date

from anthropic import Anthropic

from ...config import settings
from ..llm_config import AIServiceError
from .base import (
    ASSIGN_SYSTEM,
    ASSIGN_TOOL,
    MERGE_SYSTEM,
    MERGE_TOOL,
    Assignment,
    merge_user_message,
    plan_user_message,
)


def _client() -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key)


def generate_plan(
    empty_slots: list[tuple[Date, str]],
    recipes: list[dict],
) -> list[Assignment]:
    if not empty_slots or not recipes:
        return []

    try:
        resp = _client().messages.create(
            model=settings.anthropic_model,
            max_tokens=2048,
            system=[
                {"type": "text", "text": ASSIGN_SYSTEM, "cache_control": {"type": "ephemeral"}}
            ],
            tools=[ASSIGN_TOOL],
            tool_choice={"type": "tool", "name": "assign_meals"},
            messages=[{"role": "user", "content": plan_user_message(empty_slots, recipes)}],
        )
    except Exception as exc:
        raise AIServiceError(f"Anthropic API 调用失败：{exc}") from exc

    for block in resp.content:
        if block.type == "tool_use" and block.name == "assign_meals":
            return block.input["assignments"]
    return []


def merge_ingredients(ingredient_lines: list[str]) -> list[dict]:
    if not ingredient_lines:
        return []

    try:
        resp = _client().messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=[
                {"type": "text", "text": MERGE_SYSTEM, "cache_control": {"type": "ephemeral"}}
            ],
            tools=[MERGE_TOOL],
            tool_choice={"type": "tool", "name": "build_shopping_list"},
            messages=[{"role": "user", "content": merge_user_message(ingredient_lines)}],
        )
    except Exception as exc:
        raise AIServiceError(f"Anthropic API 调用失败：{exc}") from exc

    for block in resp.content:
        if block.type == "tool_use" and block.name == "build_shopping_list":
            return block.input["items"]
    return []
