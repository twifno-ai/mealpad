from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import Recipe
from ..schemas import RECIPE_TYPES, RecipeCreate, RecipeRead, RecipeUpdate

router = APIRouter()


@router.get("", response_model=list[RecipeRead])
def list_recipes(
    session: Session = Depends(get_session),
    type: str | None = Query(default=None),
):
    statement = select(Recipe)
    if type is not None:
        statement = statement.where(Recipe.type == type)
    return session.exec(statement).all()


@router.post("", response_model=RecipeRead, status_code=201)
def create_recipe(body: RecipeCreate, session: Session = Depends(get_session)):
    if body.type not in RECIPE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid recipe type")
    recipe = Recipe.model_validate(body)
    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    return recipe


@router.get("/{recipe_id}", response_model=RecipeRead)
def get_recipe(recipe_id: int, session: Session = Depends(get_session)):
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.put("/{recipe_id}", response_model=RecipeRead)
def update_recipe(
    recipe_id: int,
    body: RecipeUpdate,
    session: Session = Depends(get_session),
):
    if body.type not in RECIPE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid recipe type")
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    created_at = recipe.created_at
    recipe.sqlmodel_update(body)
    recipe.created_at = created_at
    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    return recipe


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int, session: Session = Depends(get_session)):
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    session.delete(recipe)
    session.commit()
