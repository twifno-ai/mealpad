def test_create_without_trailing_slash(client):
    response = client.post(
        "/api/recipes",
        json={"name": "No slash", "type": "soup", "description": "", "ingredients": []},
    )
    assert response.status_code == 201


def test_create_and_list(client):
    response = client.post(
        "/api/recipes",
        json={
            "name": "Tomato soup",
            "type": "soup",
            "description": "",
            "ingredients": ["3 tomatoes"],
        },
    )
    assert response.status_code == 201
    created = response.json()

    listed = client.get("/api/recipes").json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]


def test_invalid_type_returns_422(client):
    response = client.post(
        "/api/recipes",
        json={"name": "X", "type": "invalid", "description": "", "ingredients": []},
    )
    assert response.status_code == 422


def test_filter_by_type(client):
    client.post(
        "/api/recipes",
        json={"name": "Soup", "type": "soup", "description": "", "ingredients": []},
    )
    client.post(
        "/api/recipes",
        json={"name": "Steak", "type": "meat", "description": "", "ingredients": []},
    )

    soups = client.get("/api/recipes?type=soup").json()
    assert len(soups) == 1
    assert soups[0]["type"] == "soup"


def test_update_preserves_created_at(client):
    created = client.post(
        "/api/recipes",
        json={"name": "A", "type": "soup", "description": "", "ingredients": []},
    ).json()

    updated = client.put(
        f"/api/recipes/{created['id']}",
        json={"name": "B", "type": "soup", "description": "new", "ingredients": ["x"]},
    ).json()

    assert updated["name"] == "B"
    assert updated["created_at"] == created["created_at"]


def test_delete_recipe(client):
    created = client.post(
        "/api/recipes",
        json={"name": "A", "type": "soup", "description": "", "ingredients": []},
    ).json()
    recipe_id = created["id"]

    assert client.delete(f"/api/recipes/{recipe_id}").status_code == 204
    assert client.get(f"/api/recipes/{recipe_id}").status_code == 404
