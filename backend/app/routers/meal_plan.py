from datetime import date as Date
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import MealPlanEntry, Recipe
from ..schemas import DateRange, EntryUpsert, MealPlanEntryRead, RecipeSummary

router = APIRouter()

VALID_SLOTS = {"lunch", "dinner"}


def _entry_read(entry: MealPlanEntry, recipe: Recipe) -> MealPlanEntryRead:
    return MealPlanEntryRead(
        id=entry.id,
        date=entry.date,
        slot=entry.slot,
        recipe_id=entry.recipe_id,
        recipe=RecipeSummary(id=recipe.id, name=recipe.name, type=recipe.type),
        created_at=entry.created_at,
    )


@router.get("/", response_model=list[MealPlanEntryRead])
def get_meal_plan(
    start: Date,
    end: Date,
    session: Session = Depends(get_session),
):
    entries = session.exec(
        select(MealPlanEntry)
        .where(MealPlanEntry.date >= start)
        .where(MealPlanEntry.date <= end)
        .order_by(MealPlanEntry.date, MealPlanEntry.slot)
    ).all()
    result = []
    for entry in entries:
        recipe = session.get(Recipe, entry.recipe_id)
        if recipe is not None:
            result.append(_entry_read(entry, recipe))
    return result


@router.put("/{entry_date}/{slot}", response_model=MealPlanEntryRead)
def upsert_entry(
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

    existing = session.exec(
        select(MealPlanEntry)
        .where(MealPlanEntry.date == entry_date)
        .where(MealPlanEntry.slot == slot)
    ).first()

    if existing:
        existing.recipe_id = body.recipe_id
        entry = existing
    else:
        entry = MealPlanEntry(date=entry_date, slot=slot, recipe_id=body.recipe_id)
        session.add(entry)

    session.commit()
    session.refresh(entry)
    return _entry_read(entry, recipe)


@router.delete("/{entry_date}/{slot}", status_code=204)
def delete_entry(
    entry_date: Date,
    slot: str,
    session: Session = Depends(get_session),
):
    if slot not in VALID_SLOTS:
        raise HTTPException(status_code=422, detail="Invalid slot")
    existing = session.exec(
        select(MealPlanEntry)
        .where(MealPlanEntry.date == entry_date)
        .where(MealPlanEntry.slot == slot)
    ).first()
    if existing:
        session.delete(existing)
        session.commit()


def _iter_slots(start: Date, end: Date) -> list[tuple[Date, str]]:
    slots: list[tuple[Date, str]] = []
    current = start
    while current <= end:
        for slot in ("lunch", "dinner"):
            slots.append((current, slot))
        current += timedelta(days=1)
    return slots


@router.post("/generate", response_model=list[MealPlanEntryRead])
def generate_meal_plan(body: DateRange, session: Session = Depends(get_session)):
    from ..services.ai import generate_plan

    all_slots = set(_iter_slots(body.start, body.end))
    existing = session.exec(
        select(MealPlanEntry)
        .where(MealPlanEntry.date >= body.start)
        .where(MealPlanEntry.date <= body.end)
    ).all()
    filled = {(e.date, e.slot) for e in existing}
    empty_slots = sorted(all_slots - filled)

    if not empty_slots:
        return get_meal_plan(body.start, body.end, session)

    recipes = session.exec(select(Recipe)).all()
    recipe_dicts = [{"id": r.id, "name": r.name, "type": r.type} for r in recipes]
    valid_ids = {r.id for r in recipes}

    assignments = generate_plan(empty_slots, recipe_dicts)
    for assignment in assignments:
        try:
            assign_date = Date.fromisoformat(assignment["date"])
        except (KeyError, ValueError, TypeError):
            continue
        slot = assignment.get("slot")
        recipe_id = assignment.get("recipe_id")
        if slot not in VALID_SLOTS:
            continue
        if (assign_date, slot) not in empty_slots:
            continue
        if assign_date < body.start or assign_date > body.end:
            continue
        if recipe_id not in valid_ids:
            continue
        session.add(MealPlanEntry(date=assign_date, slot=slot, recipe_id=recipe_id))

    session.commit()
    return get_meal_plan(body.start, body.end, session)
