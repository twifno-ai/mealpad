def _seed_meal_plan(client):
    r1 = client.post(
        "/api/recipes",
        json={
            "name": "A",
            "type": "soup",
            "description": "",
            "ingredients": ["garlic"],
        },
    ).json()
    r2 = client.post(
        "/api/recipes",
        json={
            "name": "B",
            "type": "meat",
            "description": "",
            "ingredients": ["salt"],
        },
    ).json()
    client.put("/api/meal-plan/2026-05-12/lunch", json={"recipe_id": r1["id"]})
    client.put("/api/meal-plan/2026-05-12/dinner", json={"recipe_id": r2["id"]})
    client.put("/api/meal-plan/2026-05-13/lunch", json={"recipe_id": r1["id"]})
    return r1, r2


def test_regenerate_replaces_week_and_deletes_shopping_list(client, monkeypatch):
    _seed_meal_plan(client)

    def mock_merge(lines):
        return [{"text": "garlic", "category": "pantry"}]

    monkeypatch.setattr("app.routers.shopping_lists.merge_ingredients", mock_merge)
    client.post(
        "/api/shopping-lists",
        json={"start": "2026-05-12", "end": "2026-05-13"},
    )

    def mock_generate(all_slots, recipes):
        return [
            {"date": d.isoformat(), "slot": s, "recipe_id": recipes[0]["id"]}
            for d, s in all_slots
        ]

    monkeypatch.setattr("app.services.ai.generate_plan", mock_generate)

    response = client.post(
        "/api/meal-plan/regenerate",
        json={"start": "2026-05-12", "end": "2026-05-13"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 4

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
