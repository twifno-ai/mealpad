import json
from datetime import date
from types import SimpleNamespace

import pytest

from app.services.providers import openai_provider


class FakeFunction:
    def __init__(self, name: str, arguments: dict):
        self.name = name
        self.arguments = json.dumps(arguments)


class FakeToolCall:
    def __init__(self, name: str, arguments: dict):
        self.function = FakeFunction(name, arguments)


class FakeMessage:
    def __init__(self, tool_calls):
        self.tool_calls = tool_calls


class FakeChoice:
    def __init__(self, message):
        self.message = message


class FakeCompletion:
    def __init__(self, tool_name: str, arguments: dict):
        self.choices = [FakeChoice(FakeMessage([FakeToolCall(tool_name, arguments)]))]


class FakeCompletions:
    def __init__(self, response):
        self._response = response

    def create(self, **kwargs):
        return self._response


class FakeChat:
    def __init__(self, response):
        self.completions = FakeCompletions(response)


class FakeOpenAI:
    def __init__(self, response):
        self.chat = FakeChat(response)


@pytest.fixture
def empty_slots():
    return [(date(2026, 5, 12), "lunch")]


@pytest.fixture
def recipes():
    return [{"id": 1, "name": "Soup", "type": "soup"}]


def test_openai_generate_plan_parses_tool_call(monkeypatch, empty_slots, recipes):
    response = FakeCompletion(
        "assign_meals",
        {
            "assignments": [
                {
                    "date": "2026-05-12",
                    "slot": "lunch",
                    "dishes": [
                        {"recipe_id": 1, "type": "meat"},
                        {"recipe_id": 2, "type": "veg"},
                        {"recipe_id": 1, "type": "soup"},
                    ],
                }
            ]
        },
    )
    monkeypatch.setattr(openai_provider, "_client", lambda: FakeOpenAI(response))

    result = openai_provider.generate_plan(empty_slots, recipes)
    assert len(result) == 1
    assert len(result[0]["dishes"]) == 3


def test_openai_merge_ingredients_parses_tool_call(monkeypatch):
    response = FakeCompletion(
        "build_shopping_list",
        {"items": [{"text": "garlic, 5 cloves", "category": "produce"}]},
    )
    monkeypatch.setattr(openai_provider, "_client", lambda: FakeOpenAI(response))

    result = openai_provider.merge_ingredients(["2 cloves garlic", "3 cloves garlic"])
    assert len(result) == 1
    assert result[0]["category"] == "produce"


def test_openai_generate_plan_empty_input():
    assert openai_provider.generate_plan([], [{"id": 1, "name": "x", "type": "soup"}]) == []
    assert openai_provider.generate_plan([(date(2026, 5, 12), "lunch")], []) == []


def test_output_limit_kwargs_gpt5():
    assert openai_provider._output_limit_kwargs("gpt-5.5", 2048) == {
        "max_completion_tokens": 2048
    }


def test_output_limit_kwargs_legacy():
    assert openai_provider._output_limit_kwargs("gpt-4o-mini", 2048) == {"max_tokens": 2048}
