from datetime import date


def _create_recipes(client, count=5):
    ids = []
    for i in range(count):
        recipe = client.post(
            "/api/recipes/",
            json={
                "name": f"Recipe {i}",
                "type": "soup",
                "description": "",
                "ingredients": [f"item {i}"],
            },
        ).json()
        ids.append(recipe["id"])
    return ids


def test_generate_fills_empty_slots(client, monkeypatch):
    _create_recipes(client, 5)

    def mock_generate(empty_slots, recipes):
        return [
            {"date": d.isoformat(), "slot": s, "recipe_id": recipes[i % len(recipes)]["id"]}
            for i, (d, s) in enumerate(empty_slots)
        ]

    monkeypatch.setattr("app.services.ai.generate_plan", mock_generate)

    response = client.post(
        "/api/meal-plan/generate",
        json={"start": "2026-05-12", "end": "2026-05-13"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 4


def test_generate_ignores_filled_slot(client, monkeypatch):
    recipe_ids = _create_recipes(client, 5)
    client.put("/api/meal-plan/2026-05-12/lunch", json={"recipe_id": recipe_ids[0]})

    def mock_generate(empty_slots, recipes):
        assignments = [
            {"date": d.isoformat(), "slot": s, "recipe_id": recipes[0]["id"]}
            for d, s in empty_slots
        ]
        assignments.append(
            {"date": "2026-05-12", "slot": "lunch", "recipe_id": recipes[1]["id"]}
        )
        return assignments

    monkeypatch.setattr("app.services.ai.generate_plan", mock_generate)

    response = client.post(
        "/api/meal-plan/generate",
        json={"start": "2026-05-12", "end": "2026-05-12"},
    )
    entries = response.json()
    lunch = next(e for e in entries if e["slot"] == "lunch")
    assert lunch["recipe_id"] == recipe_ids[0]


def test_generate_ignores_invalid_recipe_id(client, monkeypatch):
    _create_recipes(client, 2)

    def mock_generate(empty_slots, recipes):
        return [
            {"date": "2026-05-12", "slot": "lunch", "recipe_id": 99999},
            {"date": "2026-05-12", "slot": "dinner", "recipe_id": recipes[0]["id"]},
        ]

    monkeypatch.setattr("app.services.ai.generate_plan", mock_generate)

    response = client.post(
        "/api/meal-plan/generate",
        json={"start": "2026-05-12", "end": "2026-05-12"},
    )
    assert len(response.json()) == 1


def test_generate_ignores_out_of_range_date(client, monkeypatch):
    _create_recipes(client, 2)

    def mock_generate(empty_slots, recipes):
        return [
            {"date": "2026-05-20", "slot": "lunch", "recipe_id": recipes[0]["id"]},
            {"date": "2026-05-12", "slot": "lunch", "recipe_id": recipes[0]["id"]},
        ]

    monkeypatch.setattr("app.services.ai.generate_plan", mock_generate)

    response = client.post(
        "/api/meal-plan/generate",
        json={"start": "2026-05-12", "end": "2026-05-12"},
    )
    assert len(response.json()) == 1


def test_generate_skips_api_when_no_empty_slots(client, monkeypatch):
    recipe_ids = _create_recipes(client, 2)
    called = {"value": False}

    def mock_generate(empty_slots, recipes):
        called["value"] = True
        return []

    monkeypatch.setattr("app.services.ai.generate_plan", mock_generate)

    client.put("/api/meal-plan/2026-05-12/lunch", json={"recipe_id": recipe_ids[0]})
    client.put("/api/meal-plan/2026-05-12/dinner", json={"recipe_id": recipe_ids[1]})

    response = client.post(
        "/api/meal-plan/generate",
        json={"start": "2026-05-12", "end": "2026-05-12"},
    )
    assert response.status_code == 200
    assert called["value"] is False
