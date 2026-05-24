import json
from datetime import date as Date

from openai import OpenAI

from ...config import settings
from ..llm_config import AIServiceError
from ..llm_errors import format_llm_api_error
from .base import (
    ASSIGN_SYSTEM,
    ASSIGN_TOOL,
    MERGE_SYSTEM,
    MERGE_TOOL,
    Assignment,
    merge_user_message,
    plan_user_message,
    to_openai_tool,
)


def _client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key)


def _parse_tool_arguments(resp, tool_name: str, result_key: str) -> list:
    message = resp.choices[0].message
    if not message.tool_calls:
        return []
    for call in message.tool_calls:
        if call.function.name == tool_name:
            data = json.loads(call.function.arguments)
            return data.get(result_key, [])
    return []


def generate_plan(
    empty_slots: list[tuple[Date, str]],
    recipes: list[dict],
) -> list[Assignment]:
    if not empty_slots or not recipes:
        return []

    try:
        resp = _client().chat.completions.create(
            model=settings.openai_model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": ASSIGN_SYSTEM},
                {"role": "user", "content": plan_user_message(empty_slots, recipes)},
            ],
            tools=[to_openai_tool(ASSIGN_TOOL)],
            tool_choice={"type": "function", "function": {"name": "assign_meals"}},
        )
    except Exception as exc:
        raise AIServiceError(format_llm_api_error("openai", exc)) from exc

    return _parse_tool_arguments(resp, "assign_meals", "assignments")


def merge_ingredients(ingredient_lines: list[str]) -> list[dict]:
    if not ingredient_lines:
        return []

    try:
        resp = _client().chat.completions.create(
            model=settings.openai_model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": MERGE_SYSTEM},
                {"role": "user", "content": merge_user_message(ingredient_lines)},
            ],
            tools=[to_openai_tool(MERGE_TOOL)],
            tool_choice={"type": "function", "function": {"name": "build_shopping_list"}},
        )
    except Exception as exc:
        raise AIServiceError(format_llm_api_error("openai", exc)) from exc

    return _parse_tool_arguments(resp, "build_shopping_list", "items")
