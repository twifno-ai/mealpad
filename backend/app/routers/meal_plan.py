from datetime import date as Date
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import MealPlanEntry, Recipe, ShoppingList
from ..schemas import DateRange, EntryUpsert, MealPlanEntryRead, RecipeSummary
from ..services import ai as ai_service
from ..services.llm_config import AIServiceError
from ..services.providers.base import REQUIRED_MEAL_TYPES, TYPE_SORT_ORDER
from ..services.recipe_images import cover_url_for_recipe

router = APIRouter()

VALID_SLOTS = {"lunch", "dinner"}
TYPE_LABELS = {"meat": "荤菜", "veg": "素菜", "soup": "汤类"}


def _entry_read(session: Session, entry: MealPlanEntry, recipe: Recipe) -> MealPlanEntryRead:
    return MealPlanEntryRead(
        id=entry.id,
        date=entry.date,
        slot=entry.slot,
        recipe_id=entry.recipe_id,
        sort_order=entry.sort_order,
        recipe=RecipeSummary(
            id=recipe.id,
            name=recipe.name,
            type=recipe.type,
            cuisine=recipe.cuisine,
            cover_url=cover_url_for_recipe(session, recipe.id),
        ),
        created_at=entry.created_at,
    )


def _require_ai_recipe_types(recipes: list[Recipe]) -> None:
    available = {r.type for r in recipes}
    missing = [t for t in REQUIRED_MEAL_TYPES if t not in available]
    if missing:
        labels = "、".join(TYPE_LABELS[t] for t in missing)
        raise HTTPException(status_code=422, detail=f"缺少{labels}食谱，无法生成完整一餐")


def _iter_slots(start: Date, end: Date) -> list[tuple[Date, str]]:
    slots: list[tuple[Date, str]] = []
    current = start
    while current <= end:
        for slot in ("lunch", "dinner"):
            slots.append((current, slot))
        current += timedelta(days=1)
    return slots


def _meals_with_entries(
    entries: list[MealPlanEntry],
) -> set[tuple[Date, str]]:
    return {(e.date, e.slot) for e in entries}


def _parse_meal_assignments(
    assignments: list,
    allowed_meals: set[tuple[Date, str]],
    recipe_by_id: dict[int, Recipe],
    start: Date,
    end: Date,
) -> tuple[list[tuple[Date, str, int, int]], set[tuple[Date, str]]]:
    rows: list[tuple[Date, str, int, int]] = []
    covered: set[tuple[Date, str]] = set()

    for assignment in assignments:
        try:
            assign_date = Date.fromisoformat(assignment["date"])
        except (KeyError, ValueError, TypeError):
            continue
        slot = assignment.get("slot")
        if slot not in VALID_SLOTS:
            continue
        meal_key = (assign_date, slot)
        if meal_key not in allowed_meals:
            continue
        if assign_date < start or assign_date > end:
            continue

        dishes = assignment.get("dishes")
        if not isinstance(dishes, list) or len(dishes) != 3:
            continue

        meal_rows: list[tuple[Date, str, int, int]] = []
        seen_types: set[str] = set()
        for dish in dishes:
            if not isinstance(dish, dict):
                break
            dish_type = dish.get("type")
            recipe_id = dish.get("recipe_id")
            if dish_type not in REQUIRED_MEAL_TYPES or dish_type in seen_types:
                break
            recipe = recipe_by_id.get(recipe_id)
            if recipe is None or recipe.type != dish_type:
                break
            seen_types.add(dish_type)
            meal_rows.append(
                (assign_date, slot, recipe_id, TYPE_SORT_ORDER[dish_type]),
            )

        if len(meal_rows) != 3:
            continue

        rows.extend(meal_rows)
        covered.add(meal_key)

    return rows, covered


def _delete_plan_and_shopping_list(session: Session, start: Date, end: Date) -> None:
    entries = session.exec(
        select(MealPlanEntry)
        .where(MealPlanEntry.date >= start)
        .where(MealPlanEntry.date <= end)
    ).all()
    for entry in entries:
        session.delete(entry)

    shopping_list = session.exec(
        select(ShoppingList)
        .where(ShoppingList.start_date == start)
        .where(ShoppingList.end_date == end)
    ).first()
    if shopping_list:
        session.delete(shopping_list)


def _delete_meal_entries(
    session: Session, entry_date: Date, slot: str
) -> None:
    entries = session.exec(
        select(MealPlanEntry)
        .where(MealPlanEntry.date == entry_date)
        .where(MealPlanEntry.slot == slot)
    ).all()
    for entry in entries:
        session.delete(entry)


def _next_sort_order(session: Session, entry_date: Date, slot: str) -> int:
    entries = session.exec(
        select(MealPlanEntry)
        .where(MealPlanEntry.date == entry_date)
        .where(MealPlanEntry.slot == slot)
    ).all()
    if not entries:
        return 0
    return max(e.sort_order for e in entries) + 1


@router.get("", response_model=list[MealPlanEntryRead])
def get_meal_plan(
    start: Date,
    end: Date,
    session: Session = Depends(get_session),
):
    entries = session.exec(
        select(MealPlanEntry)
        .where(MealPlanEntry.date >= start)
        .where(MealPlanEntry.date <= end)
        .order_by(MealPlanEntry.date, MealPlanEntry.slot, MealPlanEntry.sort_order)
    ).all()
    result = []
    for entry in entries:
        recipe = session.get(Recipe, entry.recipe_id)
        if recipe is not None:
            result.append(_entry_read(session, entry, recipe))
    return result


@router.post("/{entry_date}/{slot}/items", response_model=MealPlanEntryRead, status_code=201)
def add_meal_item(
    entry_date: Date,
    slot: str,
    body: EntryUpsert,
    session: Session = Depends(get_session),
):
    if slot not in VALID_SLOTS:
        raise HTTPException(status_code=422, detail="Invalid slot")
    recipe = session.get(Recipe, body.recipe_id)
    if recipe is None:
        raise HTTPException(status_code=422, detail="Recipe not found")

    duplicate = session.exec(
        select(MealPlanEntry)
        .where(MealPlanEntry.date == entry_date)
        .where(MealPlanEntry.slot == slot)
        .where(MealPlanEntry.recipe_id == body.recipe_id)
    ).first()
    if duplicate:
        raise HTTPException(status_code=422, detail="该餐已包含此食谱")

    entry = MealPlanEntry(
        date=entry_date,
        slot=slot,
        recipe_id=body.recipe_id,
        sort_order=_next_sort_order(session, entry_date, slot),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return _entry_read(session, entry, recipe)


@router.put("/items/{entry_id}", response_model=MealPlanEntryRead)
def update_meal_item(
    entry_id: int,
    body: EntryUpsert,
    session: Session = Depends(get_session),
):
    entry = session.get(MealPlanEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="未找到")
    recipe = session.get(Recipe, body.recipe_id)
    if recipe is None:
        raise HTTPException(status_code=422, detail="Recipe not found")

    if body.recipe_id != entry.recipe_id:
        duplicate = session.exec(
            select(MealPlanEntry)
            .where(MealPlanEntry.date == entry.date)
            .where(MealPlanEntry.slot == entry.slot)
            .where(MealPlanEntry.recipe_id == body.recipe_id)
        ).first()
        if duplicate:
            raise HTTPException(status_code=422, detail="该餐已包含此食谱")

    entry.recipe_id = body.recipe_id
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return _entry_read(session, entry, recipe)


@router.delete("/items/{entry_id}", status_code=204)
def delete_meal_item(entry_id: int, session: Session = Depends(get_session)):
    entry = session.get(MealPlanEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="未找到")
    session.delete(entry)
    session.commit()


@router.delete("/{entry_date}/{slot}", status_code=204)
def delete_meal(
    entry_date: Date,
    slot: str,
    session: Session = Depends(get_session),
):
    if slot not in VALID_SLOTS:
        raise HTTPException(status_code=422, detail="Invalid slot")
    _delete_meal_entries(session, entry_date, slot)
    session.commit()


@router.post("/generate", response_model=list[MealPlanEntryRead])
def generate_meal_plan(body: DateRange, session: Session = Depends(get_session)):
    all_meals = set(_iter_slots(body.start, body.end))
    existing = session.exec(
        select(MealPlanEntry)
        .where(MealPlanEntry.date >= body.start)
        .where(MealPlanEntry.date <= body.end)
    ).all()
    filled_meals = _meals_with_entries(existing)
    empty_meals = sorted(all_meals - filled_meals)

    if not empty_meals:
        return get_meal_plan(body.start, body.end, session)

    recipes = session.exec(select(Recipe)).all()
    if not recipes:
        raise HTTPException(status_code=422, detail="请先添加至少一个食谱，再进行 AI 填充")
    _require_ai_recipe_types(recipes)

    recipe_dicts = [{"id": r.id, "name": r.name, "type": r.type} for r in recipes]
    recipe_by_id = {r.id: r for r in recipes}

    try:
        assignments = ai_service.generate_plan(empty_meals, recipe_dicts)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    rows, covered = _parse_meal_assignments(
        assignments, set(empty_meals), recipe_by_id, body.start, body.end
    )
    if covered != set(empty_meals) or not rows:
        raise HTTPException(
            status_code=502,
            detail="AI 未返回有效的膳食安排，请稍后重试或手动选择食谱",
        )

    for assign_date, slot, recipe_id, sort_order in rows:
        session.add(
            MealPlanEntry(
                date=assign_date,
                slot=slot,
                recipe_id=recipe_id,
                sort_order=sort_order,
            )
        )

    session.commit()
    return get_meal_plan(body.start, body.end, session)


@router.post("/regenerate", response_model=list[MealPlanEntryRead])
def regenerate_meal_plan(body: DateRange, session: Session = Depends(get_session)):
    all_meals = _iter_slots(body.start, body.end)

    recipes = session.exec(select(Recipe)).all()
    if not recipes:
        raise HTTPException(status_code=422, detail="请先添加至少一个食谱，再进行 AI 填充")
    _require_ai_recipe_types(recipes)

    recipe_dicts = [{"id": r.id, "name": r.name, "type": r.type} for r in recipes]
    recipe_by_id = {r.id: r for r in recipes}

    try:
        assignments = ai_service.generate_plan(all_meals, recipe_dicts)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    rows, covered = _parse_meal_assignments(
        assignments, set(all_meals), recipe_by_id, body.start, body.end
    )
    if covered != set(all_meals) or not rows:
        raise HTTPException(
            status_code=502,
            detail="AI 未返回有效的膳食安排，请稍后重试或手动选择食谱",
        )

    _delete_plan_and_shopping_list(session, body.start, body.end)
    for assign_date, slot, recipe_id, sort_order in rows:
        session.add(
            MealPlanEntry(
                date=assign_date,
                slot=slot,
                recipe_id=recipe_id,
                sort_order=sort_order,
            )
        )

    session.commit()
    return get_meal_plan(body.start, body.end, session)
