def create_typed_recipes(client):
    meat = client.post(
        "/api/recipes",
        json={
            "name": "Meat Dish",
            "type": "meat",
            "description": "",
            "ingredients": ["pork"],
        },
    ).json()
    veg = client.post(
        "/api/recipes",
        json={
            "name": "Veg Dish",
            "type": "veg",
            "description": "",
            "ingredients": ["bok choy"],
        },
    ).json()
    soup = client.post(
        "/api/recipes",
        json={
            "name": "Soup Dish",
            "type": "soup",
            "description": "",
            "ingredients": ["broth"],
        },
    ).json()
    return {"meat": meat, "veg": veg, "soup": soup}


def meal_assignment(date_str, slot, typed):
    return {
        "date": date_str,
        "slot": slot,
        "dishes": [
            {"recipe_id": typed["meat"]["id"], "type": "meat"},
            {"recipe_id": typed["veg"]["id"], "type": "veg"},
            {"recipe_id": typed["soup"]["id"], "type": "soup"},
        ],
    }


def mock_generate_meals(meals, typed):
    return [meal_assignment(d.isoformat(), s, typed) for d, s in meals]
