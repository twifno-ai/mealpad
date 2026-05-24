from datetime import date

from app.services.llm_config import AIServiceError


def _create_recipes(client, count=2):
    ids = []
    for i in range(count):
        recipe = client.post(
            "/api/recipes",
            json={
                "name": f"Recipe {i}",
                "type": "soup",
                "description": "",
                "ingredients": [f"item {i}"],
            },
        ).json()
        ids.append(recipe["id"])
    return ids


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
    recipe_ids = _create_recipes(client, 1)
    client.put(f"/api/meal-plan/{date(2026, 5, 12).isoformat()}/lunch", json={"recipe_id": recipe_ids[0]})

    def raise_unconfigured(*args, **kwargs):
        raise AIServiceError("未配置 OpenAI API Key，请在 backend/.env 中设置 OPENAI_API_KEY")

    monkeypatch.setattr("app.routers.shopping_lists.merge_ingredients", raise_unconfigured)

    response = client.post(
        "/api/shopping-lists",
        json={"start": "2026-05-12", "end": "2026-05-12"},
    )
    assert response.status_code == 502
    assert "OPENAI_API_KEY" in response.json()["detail"]
