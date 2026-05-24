from meal_plan_helpers import create_typed_recipes


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
        json={"recipe_id": typed["soup"]["id"]},
    )
    return typed


def test_generate_persists_items(client, monkeypatch):
    _seed_meal_plan(client)
    lines_seen = []

    def mock_merge(lines):
        lines_seen.extend(lines)
        return [
            {"text": "garlic, 5 cloves", "category": "produce"},
            {"text": "onion, 1", "category": "produce"},
            {"text": "salt", "category": "pantry"},
        ]

    monkeypatch.setattr("app.routers.shopping_lists.merge_ingredients", mock_merge)

    response = client.post(
        "/api/shopping-lists",
        json={"start": "2026-05-12", "end": "2026-05-13"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "garlic" in data["items_by_category"]["produce"][0]["text"]
    assert len(lines_seen) == 3


def test_regenerate_resets_checks(client, monkeypatch):
    _seed_meal_plan(client)

    def mock_merge(lines):
        return [{"text": "garlic", "category": "produce"}]

    monkeypatch.setattr("app.routers.shopping_lists.merge_ingredients", mock_merge)

    first = client.post(
        "/api/shopping-lists",
        json={"start": "2026-05-12", "end": "2026-05-13"},
    ).json()
    list_id = first["id"]
    item_id = first["items_by_category"]["produce"][0]["id"]
    client.patch(f"/api/shopping-list-items/{item_id}", json={"checked": True})

    second = client.post(
        "/api/shopping-lists",
        json={"start": "2026-05-12", "end": "2026-05-13"},
    ).json()
    assert second["id"] == list_id
    assert second["items_by_category"]["produce"][0]["checked"] is False


def test_get_groups_by_category(client, monkeypatch):
    _seed_meal_plan(client)

    def mock_merge(lines):
        return [
            {"text": "apple", "category": "produce"},
            {"text": "chicken", "category": "meat"},
        ]

    monkeypatch.setattr("app.routers.shopping_lists.merge_ingredients", mock_merge)
    client.post("/api/shopping-lists", json={"start": "2026-05-12", "end": "2026-05-13"})

    data = client.get("/api/shopping-lists?start=2026-05-12&end=2026-05-13").json()
    assert len(data["items_by_category"]["produce"]) == 1
    assert len(data["items_by_category"]["meat"]) == 1


def test_patch_toggle(client, monkeypatch):
    _seed_meal_plan(client)

    def mock_merge(lines):
        return [{"text": "garlic", "category": "produce"}]

    monkeypatch.setattr("app.routers.shopping_lists.merge_ingredients", mock_merge)
    created = client.post(
        "/api/shopping-lists",
        json={"start": "2026-05-12", "end": "2026-05-13"},
    ).json()
    item_id = created["items_by_category"]["produce"][0]["id"]

    patched = client.patch(f"/api/shopping-list-items/{item_id}", json={"checked": True}).json()
    assert patched["checked"] is True

    fetched = client.get("/api/shopping-lists?start=2026-05-12&end=2026-05-13").json()
    assert fetched["items_by_category"]["produce"][0]["checked"] is True


def test_get_missing_returns_404(client):
    response = client.get("/api/shopping-lists?start=2026-05-12&end=2026-05-18")
    assert response.status_code == 404


def test_generate_empty_plan_no_mock_call(client, monkeypatch):
    called = {"value": False}

    def mock_merge(lines):
        called["value"] = True
        return []

    monkeypatch.setattr("app.routers.shopping_lists.merge_ingredients", mock_merge)

    response = client.post(
        "/api/shopping-lists",
        json={"start": "2026-05-12", "end": "2026-05-18"},
    )
    assert response.status_code == 201
    assert called["value"] is False
    assert response.json()["items_by_category"]["produce"] == []
