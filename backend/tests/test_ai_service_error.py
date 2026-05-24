from datetime import date

from app.services.llm_config import AIServiceError
from meal_plan_helpers import create_typed_recipes


def _create_recipes(client, count=2):
    typed = create_typed_recipes(client)
    return [typed["soup"], typed["meat"], typed["veg"]][:count]


def test_generate_returns_502_when_ai_unconfigured(client, monkeypatch):
    _create_recipes(client, 2)

    def raise_unconfigured(*args, **kwargs):
        raise AIServiceError("未配置 AI 服务：请在 backend/.env 中设置 ANTHROPIC_API_KEY 或 OPENAI_API_KEY")

    monkeypatch.setattr("app.services.ai.generate_plan", raise_unconfigured)

    response = client.post(
        "/api/meal-plan/generate",
        json={"start": "2026-05-12", "end": "2026-05-12"},
    )
    assert response.status_code == 502
    assert "未配置 AI 服务" in response.json()["detail"]


def test_shopping_list_returns_502_when_ai_unconfigured(client, monkeypatch):
    recipe_ids = _create_recipes(client, 3)
    client.post(
        "/api/meal-plan/2026-05-12/lunch/items",
        json={"recipe_id": recipe_ids[0]["id"]},
    )

    def raise_unconfigured(*args, **kwargs):
        raise AIServiceError("未配置 OpenAI API Key，请在 backend/.env 中设置 OPENAI_API_KEY")

    monkeypatch.setattr("app.routers.shopping_lists.merge_ingredients", raise_unconfigured)

    response = client.post(
        "/api/shopping-lists",
        json={"start": "2026-05-12", "end": "2026-05-12"},
    )
    assert response.status_code == 502
    assert "OPENAI_API_KEY" in response.json()["detail"]
