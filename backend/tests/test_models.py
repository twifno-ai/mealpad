from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import MealPlanEntry, Recipe, ShoppingList


def test_recipe_ingredients_round_trip(session: Session):
    recipe = Recipe(
        name="Garlic soup",
        type="soup",
        ingredients=["2 cloves garlic", "salt"],
    )
    session.add(recipe)
    session.commit()
    session.refresh(recipe)

    loaded = session.get(Recipe, recipe.id)
    assert loaded is not None
    assert loaded.ingredients == ["2 cloves garlic", "salt"]


def test_meal_plan_entries_by_date_range(session: Session):
    recipe = Recipe(name="A", type="soup", ingredients=["x"])
    session.add(recipe)
    session.commit()
    session.refresh(recipe)

    entries = [
        MealPlanEntry(date=date(2026, 5, 12), slot="lunch", recipe_id=recipe.id),
        MealPlanEntry(date=date(2026, 5, 12), slot="dinner", recipe_id=recipe.id),
        MealPlanEntry(date=date(2026, 5, 19), slot="lunch", recipe_id=recipe.id),
    ]
    for entry in entries:
        session.add(entry)
    session.commit()

    result = session.exec(
        select(MealPlanEntry)
        .where(MealPlanEntry.date >= date(2026, 5, 12))
        .where(MealPlanEntry.date <= date(2026, 5, 18))
        .order_by(MealPlanEntry.date, MealPlanEntry.slot)
    ).all()

    assert len(result) == 2
    assert result[0].slot == "dinner"
    assert result[1].slot == "lunch"


def test_meal_plan_duplicate_date_slot_raises(session: Session):
    recipe = Recipe(name="A", type="soup", ingredients=["x"])
    session.add(recipe)
    session.commit()
    session.refresh(recipe)

    session.add(MealPlanEntry(date=date(2026, 5, 12), slot="lunch", recipe_id=recipe.id))
    session.commit()
    session.add(MealPlanEntry(date=date(2026, 5, 12), slot="lunch", recipe_id=recipe.id))

    with pytest.raises(IntegrityError):
        session.commit()


def test_delete_recipe_cascades_meal_plan_entry(session: Session):
    recipe = Recipe(name="A", type="soup", ingredients=["x"])
    session.add(recipe)
    session.commit()
    session.refresh(recipe)

    entry = MealPlanEntry(date=date(2026, 5, 12), slot="lunch", recipe_id=recipe.id)
    session.add(entry)
    session.commit()
    entry_id = entry.id

    session.delete(recipe)
    session.commit()

    assert session.get(MealPlanEntry, entry_id) is None


def test_shopping_list_unique_date_range(session: Session):
    session.add(ShoppingList(start_date=date(2026, 5, 12), end_date=date(2026, 5, 18)))
    session.commit()
    session.add(ShoppingList(start_date=date(2026, 5, 12), end_date=date(2026, 5, 18)))

    with pytest.raises(IntegrityError):
        session.commit()
