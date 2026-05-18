from datetime import date as Date
from typing import TypedDict

from anthropic import Anthropic

from ..config import settings


class Assignment(TypedDict):
    date: str
    slot: str
    recipe_id: int


ASSIGN_TOOL = {
    "name": "assign_meals",
    "description": "Assign one recipe_id to each empty slot, optimizing for variety.",
    "input_schema": {
        "type": "object",
        "properties": {
            "assignments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "YYYY-MM-DD"},
                        "slot": {"type": "string", "enum": ["lunch", "dinner"]},
                        "recipe_id": {"type": "integer"},
                    },
                    "required": ["date", "slot", "recipe_id"],
                },
            }
        },
        "required": ["assignments"],
    },
}

ASSIGN_SYSTEM = (
    "You plan family meals. Given a list of empty (date, slot) pairs and "
    "available recipes, return one assignment per empty slot. Rules: "
    "(1) only use recipe_id values from the provided recipes; "
    "(2) avoid repeating the same recipe within 2 days; "
    "(3) vary recipe types across consecutive meals; "
    "(4) limit reuse of any recipe within a 7-day window. "
    "Always call the assign_meals tool with one assignment per empty slot."
)

MERGE_TOOL = {
    "name": "build_shopping_list",
    "description": "Consolidate ingredient lines into a deduped, summed, categorized shopping list.",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": [
                                "produce",
                                "meat",
                                "dairy",
                                "pantry",
                                "frozen",
                                "bakery",
                                "other",
                            ],
                        },
                    },
                    "required": ["text", "category"],
                },
            }
        },
        "required": ["items"],
    },
}

MERGE_SYSTEM = (
    "You build grocery shopping lists. Given raw ingredient lines from "
    "multiple recipes (with duplicates), produce a consolidated list. "
    "Rules: (1) sum quantities when the same ingredient appears multiple times "
    "(e.g. '2 cloves garlic' + '3 cloves garlic' -> 'garlic, 5 cloves'); "
    "(2) keep quantities human-readable; "
    "(3) assign each item to one category from the enum; "
    "(4) don't invent items the user didn't list. "
    "Always call build_shopping_list."
)


def _client() -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key)


def generate_plan(
    empty_slots: list[tuple[Date, str]],
    recipes: list[dict],
) -> list[Assignment]:
    if not empty_slots or not recipes:
        return []

    user_msg = (
        f"Empty slots: {[(d.isoformat(), s) for d, s in empty_slots]}\n\n"
        f"Available recipes (id, name, type): "
        f"{[(r['id'], r['name'], r['type']) for r in recipes]}"
    )
    resp = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=[{"type": "text", "text": ASSIGN_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        tools=[ASSIGN_TOOL],
        tool_choice={"type": "tool", "name": "assign_meals"},
        messages=[{"role": "user", "content": user_msg}],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "assign_meals":
            return block.input["assignments"]
    return []


def merge_ingredients(ingredient_lines: list[str]) -> list[dict]:
    if not ingredient_lines:
        return []

    resp = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[{"type": "text", "text": MERGE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        tools=[MERGE_TOOL],
        tool_choice={"type": "tool", "name": "build_shopping_list"},
        messages=[
            {
                "role": "user",
                "content": "Raw ingredient lines:\n" + "\n".join(f"- {line}" for line in ingredient_lines),
            }
        ],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "build_shopping_list":
            return block.input["items"]
    return []
