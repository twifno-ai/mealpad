from io import BytesIO

from PIL import Image
from meal_plan_helpers import create_typed_recipes, mock_generate_meals


def _minimal_jpeg() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 8), color="blue").save(buf, format="JPEG")
    return buf.getvalue()


FAKE_JPEG = _minimal_jpeg()


def _add_plan_entry(client, date: str, slot: str, recipe_id: int):
    return client.post(
        f"/api/meal-plan/{date}/{slot}/items",
        json={"recipe_id": recipe_id},
    ).json()


def test_mark_planned_dish(client):
    typed = create_typed_recipes(client)
    entry = _add_plan_entry(client, "2026-06-02", "lunch", typed["meat"]["id"])
    res = client.post(f"/api/cooked-dishes/planned/{entry['id']}")
    assert res.status_code == 201
    body = res.json()
    assert body["kind"] == "planned"
    assert body["recipe_name"] == "Meat Dish"
    assert body["meal_plan_entry_id"] == entry["id"]


def test_mark_planned_twice_returns_409(client):
    typed = create_typed_recipes(client)
    entry = _add_plan_entry(client, "2026-06-02", "lunch", typed["meat"]["id"])
    client.post(f"/api/cooked-dishes/planned/{entry['id']}")
    res = client.post(f"/api/cooked-dishes/planned/{entry['id']}")
    assert res.status_code == 409


def test_extra_and_duplicate_422(client):
    typed = create_typed_recipes(client)
    data = {"date": "2026-06-02", "slot": "dinner", "recipe_id": typed["veg"]["id"]}
    assert client.post("/api/cooked-dishes/extra", data=data).status_code == 201
    assert client.post("/api/cooked-dishes/extra", data=data).status_code == 422


def test_list_by_date_range(client):
    typed = create_typed_recipes(client)
    entry = _add_plan_entry(client, "2026-06-03", "lunch", typed["soup"]["id"])
    client.post(f"/api/cooked-dishes/planned/{entry['id']}")
    listed = client.get("/api/cooked-dishes?start=2026-06-01&end=2026-06-07").json()
    assert len(listed) == 1
    assert listed[0]["date"] == "2026-06-03"


def test_delete_plan_entry_keeps_log(client):
    typed = create_typed_recipes(client)
    entry = _add_plan_entry(client, "2026-06-04", "dinner", typed["meat"]["id"])
    log = client.post(f"/api/cooked-dishes/planned/{entry['id']}").json()
    assert client.delete(f"/api/meal-plan/items/{entry['id']}").status_code == 204
    listed = client.get("/api/cooked-dishes?start=2026-06-04&end=2026-06-04").json()
    assert len(listed) == 1
    assert listed[0]["id"] == log["id"]
    assert listed[0]["meal_plan_entry_id"] is None


def test_mark_planned_with_photo(client, upload_root):
    typed = create_typed_recipes(client)
    entry = _add_plan_entry(client, "2026-06-05", "lunch", typed["veg"]["id"])
    res = client.post(
        f"/api/cooked-dishes/planned/{entry['id']}",
        files={"photo": ("x.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["photo_url"] is not None
    assert (upload_root / body["photo_url"].removeprefix("/uploads/")).is_file()


def test_delete_log(client, upload_root):
    typed = create_typed_recipes(client)
    entry = _add_plan_entry(client, "2026-06-06", "lunch", typed["soup"]["id"])
    log = client.post(
        f"/api/cooked-dishes/planned/{entry['id']}",
        files={"photo": ("x.jpg", FAKE_JPEG, "image/jpeg")},
    ).json()
    rel = log["photo_url"].removeprefix("/uploads/")
    assert client.delete(f"/api/cooked-dishes/{log['id']}").status_code == 204
    assert not (upload_root / rel).exists()


def test_regenerate_keeps_cooked_logs(client, monkeypatch):
    typed = create_typed_recipes(client)
    start = "2026-06-09"
    end = "2026-06-15"
    entry = _add_plan_entry(client, "2026-06-10", "lunch", typed["meat"]["id"])
    client.post(f"/api/cooked-dishes/planned/{entry['id']}")

    from datetime import date

    meals = []
    d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    while d <= end_d:
        for slot in ("lunch", "dinner"):
            meals.append((d, slot))
        d = date.fromordinal(d.toordinal() + 1)

    def fake_generate(empty_meals, _recipes):
        return mock_generate_meals(empty_meals, typed)

    monkeypatch.setattr("app.services.ai.generate_plan", fake_generate)
    client.post("/api/meal-plan/regenerate", json={"start": start, "end": end})

    listed = client.get(f"/api/cooked-dishes?start={start}&end={end}").json()
    assert len(listed) == 1
    assert listed[0]["meal_plan_entry_id"] is None
