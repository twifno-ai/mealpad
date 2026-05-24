from datetime import date


def _create_recipe(client, name="Recipe", recipe_type="soup"):
    return client.post(
        "/api/recipes",
        json={
            "name": name,
            "type": recipe_type,
            "description": "",
            "ingredients": [],
        },
    ).json()


def test_empty_range_returns_empty_list(client):
    response = client.get("/api/meal-plan?start=2026-05-12&end=2026-05-18")
    assert response.status_code == 200
    assert response.json() == []


def test_post_then_get(client):
    recipe = _create_recipe(client)
    post = client.post(
        "/api/meal-plan/2026-05-12/lunch/items",
        json={"recipe_id": recipe["id"]},
    )
    assert post.status_code == 201
    entry = post.json()
    assert entry["recipe"]["name"] == "Recipe"

    listed = client.get("/api/meal-plan?start=2026-05-12&end=2026-05-18").json()
    assert len(listed) == 1


def test_two_dishes_same_meal(client):
    r1 = _create_recipe(client, "A")
    r2 = _create_recipe(client, "B", "meat")
    client.post("/api/meal-plan/2026-05-12/lunch/items", json={"recipe_id": r1["id"]})
    client.post("/api/meal-plan/2026-05-12/lunch/items", json={"recipe_id": r2["id"]})

    listed = client.get("/api/meal-plan?start=2026-05-12&end=2026-05-12").json()
    assert len(listed) == 2


def test_post_duplicate_recipe_returns_422(client):
    recipe = _create_recipe(client)
    client.post("/api/meal-plan/2026-05-12/lunch/items", json={"recipe_id": recipe["id"]})
    response = client.post(
        "/api/meal-plan/2026-05-12/lunch/items",
        json={"recipe_id": recipe["id"]},
    )
    assert response.status_code == 422
    assert "该餐已包含此食谱" in response.json()["detail"]


def test_put_updates_item(client):
    r1 = _create_recipe(client, "A")
    r2 = _create_recipe(client, "B", "meat")
    created = client.post(
        "/api/meal-plan/2026-05-12/lunch/items",
        json={"recipe_id": r1["id"]},
    ).json()
    client.put(
        f"/api/meal-plan/items/{created['id']}",
        json={"recipe_id": r2["id"]},
    )

    listed = client.get("/api/meal-plan?start=2026-05-12&end=2026-05-12").json()
    assert len(listed) == 1
    assert listed[0]["recipe"]["name"] == "B"


def test_post_missing_recipe_returns_422(client):
    response = client.post(
        "/api/meal-plan/2026-05-12/lunch/items",
        json={"recipe_id": 9999},
    )
    assert response.status_code == 422


def test_delete_item(client):
    recipe = _create_recipe(client)
    created = client.post(
        "/api/meal-plan/2026-05-12/lunch/items",
        json={"recipe_id": recipe["id"]},
    ).json()
    assert client.delete(f"/api/meal-plan/items/{created['id']}").status_code == 204
    assert client.get("/api/meal-plan?start=2026-05-12&end=2026-05-12").json() == []


def test_delete_meal_clears_all_dishes(client):
    r1 = _create_recipe(client, "A")
    r2 = _create_recipe(client, "B", "meat")
    client.post("/api/meal-plan/2026-05-12/lunch/items", json={"recipe_id": r1["id"]})
    client.post("/api/meal-plan/2026-05-12/lunch/items", json={"recipe_id": r2["id"]})
    assert client.delete("/api/meal-plan/2026-05-12/lunch").status_code == 204
    assert client.get("/api/meal-plan?start=2026-05-12&end=2026-05-12").json() == []


def test_range_crosses_weeks(client):
    recipe = _create_recipe(client)
    client.post("/api/meal-plan/2026-05-12/lunch/items", json={"recipe_id": recipe["id"]})
    client.post("/api/meal-plan/2026-05-19/dinner/items", json={"recipe_id": recipe["id"]})

    listed = client.get("/api/meal-plan?start=2026-05-12&end=2026-05-19").json()
    assert len(listed) == 2
