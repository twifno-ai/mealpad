from datetime import date


def _create_recipe(client, name="Recipe"):
    return client.post(
        "/api/recipes/",
        json={"name": name, "type": "soup", "description": "", "ingredients": []},
    ).json()


def test_empty_range_returns_empty_list(client):
    response = client.get("/api/meal-plan/?start=2026-05-12&end=2026-05-18")
    assert response.status_code == 200
    assert response.json() == []


def test_put_then_get(client):
    recipe = _create_recipe(client)
    put = client.put(
        "/api/meal-plan/2026-05-12/lunch",
        json={"recipe_id": recipe["id"]},
    )
    assert put.status_code == 200
    entry = put.json()
    assert entry["recipe"]["name"] == "Recipe"

    listed = client.get("/api/meal-plan/?start=2026-05-12&end=2026-05-18").json()
    assert len(listed) == 1


def test_put_replaces_recipe(client):
    r1 = _create_recipe(client, "A")
    r2 = _create_recipe(client, "B")
    client.put("/api/meal-plan/2026-05-12/lunch", json={"recipe_id": r1["id"]})
    client.put("/api/meal-plan/2026-05-12/lunch", json={"recipe_id": r2["id"]})

    listed = client.get("/api/meal-plan/?start=2026-05-12&end=2026-05-12").json()
    assert len(listed) == 1
    assert listed[0]["recipe"]["name"] == "B"


def test_put_missing_recipe_returns_422(client):
    response = client.put(
        "/api/meal-plan/2026-05-12/lunch",
        json={"recipe_id": 9999},
    )
    assert response.status_code == 422


def test_delete_entry(client):
    recipe = _create_recipe(client)
    client.put("/api/meal-plan/2026-05-12/lunch", json={"recipe_id": recipe["id"]})
    assert client.delete("/api/meal-plan/2026-05-12/lunch").status_code == 204
    assert client.get("/api/meal-plan/?start=2026-05-12&end=2026-05-12").json() == []
    assert client.delete("/api/meal-plan/2026-05-12/lunch").status_code == 204


def test_range_crosses_weeks(client):
    recipe = _create_recipe(client)
    client.put("/api/meal-plan/2026-05-12/lunch", json={"recipe_id": recipe["id"]})
    client.put("/api/meal-plan/2026-05-19/dinner", json={"recipe_id": recipe["id"]})

    listed = client.get("/api/meal-plan/?start=2026-05-12&end=2026-05-19").json()
    assert len(listed) == 2
