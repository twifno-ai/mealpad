from datetime import date as Date
from typing import TypedDict

REQUIRED_MEAL_TYPES = ("meat", "veg", "soup")
TYPE_SORT_ORDER = {"meat": 0, "veg": 1, "soup": 2}


class DishAssignment(TypedDict):
    recipe_id: int
    type: str


class MealAssignment(TypedDict):
    date: str
    slot: str
    dishes: list[DishAssignment]


# Backward alias for exports
Assignment = MealAssignment

ASSIGN_TOOL = {
    "name": "assign_meals",
    "description": "Assign three recipes (meat, veg, soup) to each empty meal slot.",
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
                        "dishes": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 3,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "recipe_id": {"type": "integer"},
                                    "type": {
                                        "type": "string",
                                        "enum": ["meat", "veg", "soup"],
                                    },
                                },
                                "required": ["recipe_id", "type"],
                            },
                        },
                    },
                    "required": ["date", "slot", "dishes"],
                },
            }
        },
        "required": ["assignments"],
    },
}

ASSIGN_SYSTEM = (
    "You plan family meals. Given empty (date, slot) meal slots and available recipes, "
    "assign exactly three recipes per slot: one meat, one veg, and one soup. Rules: "
    "(1) each dish recipe_id must come from the provided recipes and match the declared type; "
    "(2) avoid repeating the same recipe within 2 days; "
    "(3) vary choices across consecutive meals; "
    "(4) limit reuse of any recipe within a 7-day window. "
    "Always call assign_meals with one assignment per empty slot, each with exactly 3 dishes."
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


def plan_user_message(empty_slots: list[tuple[Date, str]], recipes: list[dict]) -> str:
    return (
        f"Empty meal slots: {[(d.isoformat(), s) for d, s in empty_slots]}\n\n"
        f"Available recipes (id, name, type): "
        f"{[(r['id'], r['name'], r['type']) for r in recipes]}"
    )


def merge_user_message(ingredient_lines: list[str]) -> str:
    return "Raw ingredient lines:\n" + "\n".join(f"- {line}" for line in ingredient_lines)


def to_openai_tool(tool: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }
