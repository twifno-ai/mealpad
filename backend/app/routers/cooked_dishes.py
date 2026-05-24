from datetime import date as Date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlmodel import Session, select

from ..db import get_session
from ..models import CookedDishLog, MealPlanEntry, Recipe
from ..schemas import CookedDishLogRead
from ..services.uploads import UploadError, delete_stored_file, save_image

router = APIRouter()

VALID_SLOTS = {"lunch", "dinner"}


def _to_read(log: CookedDishLog) -> CookedDishLogRead:
    return CookedDishLogRead(
        id=log.id,
        date=log.date,
        slot=log.slot,
        recipe_id=log.recipe_id,
        recipe_name=log.recipe_name,
        kind=log.kind,
        meal_plan_entry_id=log.meal_plan_entry_id,
        photo_url=f"/uploads/{log.photo_path}" if log.photo_path else None,
        logged_at=log.logged_at,
    )


@router.get("", response_model=list[CookedDishLogRead])
def list_cooked(
    start: Date = Query(...),
    end: Date = Query(...),
    session: Session = Depends(get_session),
):
    rows = session.exec(
        select(CookedDishLog)
        .where(CookedDishLog.date >= start, CookedDishLog.date <= end)
        .order_by(CookedDishLog.date, CookedDishLog.slot, CookedDishLog.logged_at)
    ).all()
    return [_to_read(row) for row in rows]


@router.post("/planned/{entry_id}", response_model=CookedDishLogRead, status_code=201)
def mark_planned(
    entry_id: int,
    photo: UploadFile | None = File(default=None),
    session: Session = Depends(get_session),
):
    entry = session.get(MealPlanEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="未找到计划条目")
    existing = session.exec(
        select(CookedDishLog).where(CookedDishLog.meal_plan_entry_id == entry_id)
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="该道菜已标记为已做")
    recipe = session.get(Recipe, entry.recipe_id)
    if recipe is None:
        raise HTTPException(status_code=422, detail="食谱不存在")
    try:
        photo_path = save_image(photo, subdir="cooked")
    except UploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log = CookedDishLog(
        date=entry.date,
        slot=entry.slot,
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        kind="planned",
        meal_plan_entry_id=entry.id,
        photo_path=photo_path,
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return _to_read(log)


@router.post("/extra", response_model=CookedDishLogRead, status_code=201)
def add_extra(
    date: Date = Form(...),
    slot: str = Form(...),
    recipe_id: int = Form(...),
    photo: UploadFile | None = File(default=None),
    session: Session = Depends(get_session),
):
    if slot not in VALID_SLOTS:
        raise HTTPException(status_code=422, detail="无效的餐次")
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="食谱不存在")
    duplicate = session.exec(
        select(CookedDishLog).where(
            CookedDishLog.date == date,
            CookedDishLog.slot == slot,
            CookedDishLog.recipe_id == recipe_id,
            CookedDishLog.kind == "extra",
        )
    ).first()
    if duplicate is not None:
        raise HTTPException(status_code=422, detail="该餐已包含此食谱的实际记录")
    try:
        photo_path = save_image(photo, subdir="cooked")
    except UploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log = CookedDishLog(
        date=date,
        slot=slot,
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        kind="extra",
        photo_path=photo_path,
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return _to_read(log)


@router.put("/{log_id}/photo", response_model=CookedDishLogRead)
def replace_photo(
    log_id: int,
    photo: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    log = session.get(CookedDishLog, log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="未找到记录")
    try:
        photo_path = save_image(photo, subdir="cooked")
    except UploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    delete_stored_file(log.photo_path)
    log.photo_path = photo_path
    session.add(log)
    session.commit()
    session.refresh(log)
    return _to_read(log)


@router.delete("/{log_id}/photo", response_model=CookedDishLogRead)
def remove_photo(log_id: int, session: Session = Depends(get_session)):
    log = session.get(CookedDishLog, log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="未找到记录")
    delete_stored_file(log.photo_path)
    log.photo_path = None
    session.add(log)
    session.commit()
    session.refresh(log)
    return _to_read(log)


@router.delete("/{log_id}", status_code=204)
def delete_log(log_id: int, session: Session = Depends(get_session)):
    log = session.get(CookedDishLog, log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="未找到记录")
    delete_stored_file(log.photo_path)
    session.delete(log)
    session.commit()
