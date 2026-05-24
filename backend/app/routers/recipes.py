from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, select

from ..db import get_session
from ..models import Recipe, RecipeImage
from ..schemas import CUISINE_TYPES, RECIPE_TYPES, RecipeCreate, RecipeRead, RecipeUpdate
from ..services.recipe_images import cover_url_for_recipe
from ..services.uploads import UploadError, delete_stored_file, save_image

router = APIRouter()


def _normalize_cuisine(cuisine: str | None) -> str | None:
    if cuisine is None or cuisine == "":
        return None
    if cuisine not in CUISINE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid recipe cuisine")
    return cuisine


def _recipe_read(session: Session, recipe: Recipe) -> RecipeRead:
    return RecipeRead(
        id=recipe.id,
        name=recipe.name,
        description=recipe.description,
        type=recipe.type,
        cuisine=recipe.cuisine,
        ingredients=recipe.ingredients,
        created_at=recipe.created_at,
        cover_url=cover_url_for_recipe(session, recipe.id),
    )


@router.get("", response_model=list[RecipeRead])
def list_recipes(
    session: Session = Depends(get_session),
    type: str | None = Query(default=None),
    cuisine: str | None = Query(default=None),
):
    statement = select(Recipe)
    if type is not None:
        if type not in RECIPE_TYPES:
            raise HTTPException(status_code=422, detail="Invalid recipe type")
        statement = statement.where(Recipe.type == type)
    if cuisine is not None:
        if cuisine == "":
            statement = statement.where(Recipe.cuisine.is_(None))
        else:
            if cuisine not in CUISINE_TYPES:
                raise HTTPException(status_code=422, detail="Invalid recipe cuisine")
            statement = statement.where(Recipe.cuisine == cuisine)
    recipes = session.exec(statement).all()
    return [_recipe_read(session, recipe) for recipe in recipes]


@router.post("", response_model=RecipeRead, status_code=201)
def create_recipe(body: RecipeCreate, session: Session = Depends(get_session)):
    if body.type not in RECIPE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid recipe type")
    cuisine = _normalize_cuisine(body.cuisine)
    recipe = Recipe.model_validate({**body.model_dump(), "cuisine": cuisine})
    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    return _recipe_read(session, recipe)


@router.get("/{recipe_id}", response_model=RecipeRead)
def get_recipe(recipe_id: int, session: Session = Depends(get_session)):
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return _recipe_read(session, recipe)


@router.put("/{recipe_id}", response_model=RecipeRead)
def update_recipe(
    recipe_id: int,
    body: RecipeUpdate,
    session: Session = Depends(get_session),
):
    if body.type not in RECIPE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid recipe type")
    cuisine = _normalize_cuisine(body.cuisine)
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    created_at = recipe.created_at
    recipe.sqlmodel_update({**body.model_dump(), "cuisine": cuisine})
    recipe.created_at = created_at
    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    return _recipe_read(session, recipe)


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int, session: Session = Depends(get_session)):
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    session.delete(recipe)
    session.commit()


@router.post("/{recipe_id}/cover", status_code=201)
def upload_cover(
    recipe_id: int,
    photo: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    old = session.exec(
        select(RecipeImage).where(
            RecipeImage.recipe_id == recipe_id,
            RecipeImage.is_cover.is_(True),
        )
    ).first()
    try:
        path = save_image(photo, subdir=f"recipes/{recipe_id}")
    except UploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if path is None:
        raise HTTPException(status_code=400, detail="未提供图片")
    if old is not None:
        delete_stored_file(old.file_path)
        session.delete(old)
    session.add(RecipeImage(recipe_id=recipe_id, file_path=path, is_cover=True))
    session.commit()
    return {"cover_url": f"/uploads/{path}"}


@router.delete("/{recipe_id}/cover", status_code=204)
def delete_cover(recipe_id: int, session: Session = Depends(get_session)):
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    cover = session.exec(
        select(RecipeImage).where(
            RecipeImage.recipe_id == recipe_id,
            RecipeImage.is_cover.is_(True),
        )
    ).first()
    if cover is None:
        return
    delete_stored_file(cover.file_path)
    session.delete(cover)
    session.commit()
