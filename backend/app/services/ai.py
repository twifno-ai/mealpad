from datetime import date as Date

from .llm_config import get_active_provider
from .providers import anthropic, openai_provider
from .providers.base import Assignment

__all__ = ["Assignment", "generate_plan", "merge_ingredients"]


def generate_plan(
    empty_slots: list[tuple[Date, str]],
    recipes: list[dict],
) -> list[Assignment]:
    provider = get_active_provider()
    if provider == "openai":
        return openai_provider.generate_plan(empty_slots, recipes)
    return anthropic.generate_plan(empty_slots, recipes)


def merge_ingredients(ingredient_lines: list[str]) -> list[dict]:
    provider = get_active_provider()
    if provider == "openai":
        return openai_provider.merge_ingredients(ingredient_lines)
    return anthropic.merge_ingredients(ingredient_lines)
