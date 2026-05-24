from meal_plan_helpers import create_typed_recipes, meal_assignment, mock_generate_meals


def test_generate_fills_empty_meals(client, monkeypatch):
    typed = create_typed_recipes(client)

    def mock_generate(empty_meals, recipes):
        return mock_generate_meals(empty_meals, typed)

    monkeypatch.setattr("app.services.ai.generate_plan", mock_generate)

    response = client.post(
        "/api/meal-plan/generate",
        json={"start": "2026-05-12", "end": "2026-05-13"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 12


def test_generate_ignores_filled_meal(client, monkeypatch):
    typed = create_typed_recipes(client)
    client.post(
        "/api/meal-plan/2026-05-12/lunch/items",
        json={"recipe_id": typed["soup"]["id"]},
    )

    def mock_generate(empty_meals, recipes):
        assignments = mock_generate_meals(empty_meals, typed)
        assignments.append(meal_assignment("2026-05-12", "lunch", typed))
        return assignments

    monkeypatch.setattr("app.services.ai.generate_plan", mock_generate)

    response = client.post(
        "/api/meal-plan/generate",
        json={"start": "2026-05-12", "end": "2026-05-12"},
    )
    entries = response.json()
    lunch = [e for e in entries if e["slot"] == "lunch"]
    assert len(lunch) == 1
    assert lunch[0]["recipe_id"] == typed["soup"]["id"]


def test_generate_missing_recipe_type_returns_422(client):
    client.post(
        "/api/recipes",
        json={
            "name": "Only soup",
            "type": "soup",
            "description": "",
            "ingredients": ["water"],
        },
    )
    response = client.post(
        "/api/meal-plan/generate",
        json={"start": "2026-05-12", "end": "2026-05-12"},
    )
    assert response.status_code == 422
    assert "荤菜" in response.json()["detail"]


def test_generate_invalid_ai_output_returns_502(client, monkeypatch):
    create_typed_recipes(client)

    def mock_generate(empty_meals, recipes):
        return [
            {
                "date": "2026-05-12",
                "slot": "lunch",
                "dishes": [
                    {"recipe_id": 99999, "type": "meat"},
                    {"recipe_id": 99998, "type": "veg"},
                    {"recipe_id": 99997, "type": "soup"},
                ],
            }
        ]

    monkeypatch.setattr("app.services.ai.generate_plan", mock_generate)

    response = client.post(
        "/api/meal-plan/generate",
        json={"start": "2026-05-12", "end": "2026-05-12"},
    )
    assert response.status_code == 502


def test_generate_skips_api_when_no_empty_meals(client, monkeypatch):
    typed = create_typed_recipes(client)
    called = {"value": False}

    def mock_generate(empty_meals, recipes):
        called["value"] = True
        return []

    monkeypatch.setattr("app.services.ai.generate_plan", mock_generate)

    client.post(
        "/api/meal-plan/2026-05-12/lunch/items",
        json={"recipe_id": typed["soup"]["id"]},
    )
    client.post(
        "/api/meal-plan/2026-05-12/dinner/items",
        json={"recipe_id": typed["meat"]["id"]},
    )

    response = client.post(
        "/api/meal-plan/generate",
        json={"start": "2026-05-12", "end": "2026-05-12"},
    )
    assert response.status_code == 200
    assert called["value"] is False
