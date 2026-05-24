from meal_plan_helpers import create_typed_recipes, mock_generate_meals


def _seed_meal_plan(client):
    typed = create_typed_recipes(client)
    client.post(
        "/api/meal-plan/2026-05-12/lunch/items",
        json={"recipe_id": typed["soup"]["id"]},
    )
    client.post(
        "/api/meal-plan/2026-05-12/dinner/items",
        json={"recipe_id": typed["meat"]["id"]},
    )
    client.post(
        "/api/meal-plan/2026-05-13/lunch/items",
        json={"recipe_id": typed["veg"]["id"]},
    )
    return typed


def test_regenerate_replaces_week_and_deletes_shopping_list(client, monkeypatch):
    typed = _seed_meal_plan(client)

    def mock_merge(lines):
        return [{"text": "garlic", "category": "pantry"}]

    monkeypatch.setattr("app.routers.shopping_lists.merge_ingredients", mock_merge)
    client.post(
        "/api/shopping-lists",
        json={"start": "2026-05-12", "end": "2026-05-13"},
    )

    def mock_generate(all_meals, recipes):
        return mock_generate_meals(all_meals, typed)

    monkeypatch.setattr("app.services.ai.generate_plan", mock_generate)

    response = client.post(
        "/api/meal-plan/regenerate",
        json={"start": "2026-05-12", "end": "2026-05-13"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 12

    list_resp = client.get("/api/shopping-lists?start=2026-05-12&end=2026-05-13")
    assert list_resp.status_code == 404


def test_regenerate_requires_recipes(client):
    response = client.post(
        "/api/meal-plan/regenerate",
        json={"start": "2026-05-12", "end": "2026-05-12"},
    )
    assert response.status_code == 422
    assert "食谱" in response.json()["detail"]


def test_regenerate_empty_ai_preserves_data(client, monkeypatch):
    _seed_meal_plan(client)

    def mock_merge(lines):
        return [{"text": "garlic", "category": "pantry"}]

    monkeypatch.setattr("app.routers.shopping_lists.merge_ingredients", mock_merge)
    client.post(
        "/api/shopping-lists",
        json={"start": "2026-05-12", "end": "2026-05-13"},
    )

    monkeypatch.setattr("app.services.ai.generate_plan", lambda *args, **kwargs: [])

    response = client.post(
        "/api/meal-plan/regenerate",
        json={"start": "2026-05-12", "end": "2026-05-13"},
    )
    assert response.status_code == 502

    plan = client.get("/api/meal-plan?start=2026-05-12&end=2026-05-13").json()
    assert len(plan) == 3

    list_resp = client.get("/api/shopping-lists?start=2026-05-12&end=2026-05-13")
    assert list_resp.status_code == 200
