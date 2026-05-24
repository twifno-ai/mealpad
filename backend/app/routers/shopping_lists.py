from datetime import date as Date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import MealPlanEntry, Recipe, ShoppingList, ShoppingListItem
from ..schemas import (
    SHOPPING_CATEGORIES,
    DateRange,
    ItemUpdate,
    ShoppingListItemRead,
    ShoppingListRead,
)
from ..services.ai import merge_ingredients
from ..services.llm_config import AIServiceError

router = APIRouter()


def _group_items(items: list[ShoppingListItem]) -> dict[str, list[ShoppingListItemRead]]:
    by_category: dict[str, list[ShoppingListItemRead]] = {c: [] for c in SHOPPING_CATEGORIES}
    for item in items:
        category = item.category if item.category in SHOPPING_CATEGORIES else "other"
        by_category[category].append(
            ShoppingListItemRead(
                id=item.id,
                text=item.text,
                category=category,
                checked=item.checked,
            )
        )
    return by_category


def _read_list(shopping_list: ShoppingList, session: Session) -> ShoppingListRead:
    items = session.exec(
        select(ShoppingListItem).where(ShoppingListItem.shopping_list_id == shopping_list.id)
    ).all()
    return ShoppingListRead(
        id=shopping_list.id,
        start_date=shopping_list.start_date,
        end_date=shopping_list.end_date,
        generated_at=shopping_list.generated_at,
        items_by_category=_group_items(items),
    )


@router.get("", response_model=ShoppingListRead)
def get_shopping_list(
    start: Date,
    end: Date,
    session: Session = Depends(get_session),
):
    shopping_list = session.exec(
        select(ShoppingList)
        .where(ShoppingList.start_date == start)
        .where(ShoppingList.end_date == end)
    ).first()
    if shopping_list is None:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return _read_list(shopping_list, session)


@router.post("", response_model=ShoppingListRead, status_code=201)
def generate_shopping_list(body: DateRange, session: Session = Depends(get_session)):
    entries = session.exec(
        select(MealPlanEntry)
        .where(MealPlanEntry.date >= body.start)
        .where(MealPlanEntry.date <= body.end)
    ).all()

    ingredient_lines: list[str] = []
    for entry in entries:
        recipe = session.get(Recipe, entry.recipe_id)
        if recipe:
            ingredient_lines.extend(recipe.ingredients)

    try:
        merged = merge_ingredients(ingredient_lines) if ingredient_lines else []
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    shopping_list = session.exec(
        select(ShoppingList)
        .where(ShoppingList.start_date == body.start)
        .where(ShoppingList.end_date == body.end)
    ).first()

    if shopping_list is None:
        shopping_list = ShoppingList(start_date=body.start, end_date=body.end)
        session.add(shopping_list)
        session.commit()
        session.refresh(shopping_list)
    else:
        old_items = session.exec(
            select(ShoppingListItem).where(ShoppingListItem.shopping_list_id == shopping_list.id)
        ).all()
        for item in old_items:
            session.delete(item)
        session.commit()

    for item_data in merged:
        category = item_data.get("category", "other")
        if category not in SHOPPING_CATEGORIES:
            category = "other"
        session.add(
            ShoppingListItem(
                shopping_list_id=shopping_list.id,
                text=item_data["text"],
                category=category,
                checked=False,
            )
        )
    session.commit()
    session.refresh(shopping_list)
    return _read_list(shopping_list, session)


items_router = APIRouter()


@items_router.patch("/{item_id}", response_model=ShoppingListItemRead)
def update_item(
    item_id: int,
    body: ItemUpdate,
    session: Session = Depends(get_session),
):
    item = session.get(ShoppingListItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    item.checked = body.checked
    session.add(item)
    session.commit()
    session.refresh(item)
    category = item.category if item.category in SHOPPING_CATEGORIES else "other"
    return ShoppingListItemRead(
        id=item.id,
        text=item.text,
        category=category,
        checked=item.checked,
    )
