from sqlmodel import Session, select

from app.migrate import migrate_db
from app.models import Recipe


def test_create_with_cuisine(client):
    response = client.post(
        "/api/recipes",
        json={
            "name": "韩式拌饭",
            "type": "other",
            "cuisine": "korean",
            "description": "",
            "ingredients": ["米饭 1碗"],
        },
    )
    assert response.status_code == 201
    assert response.json()["cuisine"] == "korean"


def test_create_without_cuisine_is_null(client):
    response = client.post(
        "/api/recipes",
        json={"name": "未分类菜", "type": "soup", "description": "", "ingredients": ["水"]},
    )
    assert response.status_code == 201
    assert response.json()["cuisine"] is None


def test_invalid_cuisine_returns_422(client):
    response = client.post(
        "/api/recipes",
        json={
            "name": "X",
            "type": "soup",
            "cuisine": "italian",
            "description": "",
            "ingredients": [],
        },
    )
    assert response.status_code == 422


def test_filter_by_cuisine(client):
    client.post(
        "/api/recipes",
        json={
            "name": "A",
            "type": "meat",
            "cuisine": "chinese",
            "description": "",
            "ingredients": [],
        },
    )
    client.post(
        "/api/recipes",
        json={"name": "B", "type": "meat", "description": "", "ingredients": []},
    )

    chinese = client.get("/api/recipes?cuisine=chinese").json()
    assert len(chinese) == 1
    assert chinese[0]["name"] == "A"

    unset = client.get("/api/recipes?cuisine=").json()
    assert len(unset) == 1
    assert unset[0]["name"] == "B"


def test_migration_backfills_chinese_seed_name(session: Session):
    session.add(
        Recipe(
            name="番茄炒蛋",
            type="meat",
            description="",
            ingredients=["鸡蛋"],
        )
    )
    session.commit()
    migrate_db()
    recipe = session.exec(select(Recipe).where(Recipe.name == "番茄炒蛋")).one()
    assert recipe.cuisine == "chinese"


def test_migration_does_not_overwrite_user_cuisine(session: Session):
    session.add(
        Recipe(
            name="番茄炒蛋",
            type="meat",
            description="",
            ingredients=["鸡蛋"],
            cuisine="western",
        )
    )
    session.commit()
    migrate_db()
    recipe = session.exec(select(Recipe).where(Recipe.name == "番茄炒蛋")).one()
    assert recipe.cuisine == "western"
