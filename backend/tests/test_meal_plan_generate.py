
def test_generate_requires_recipes(client):
    response = client.post(
        "/api/meal-plan/generate",
        json={"start": "2026-05-12", "end": "2026-05-12"},
    )
    assert response.status_code == 422
    assert "食谱" in response.json()["detail"]
