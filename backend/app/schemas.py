from datetime import date as Date
from datetime import datetime

from pydantic import BaseModel, Field

RECIPE_TYPES = {"soup", "meat", "veg", "other"}

CUISINE_TYPES = {"chinese", "japanese", "korean", "thai", "western", "other"}

SHOPPING_CATEGORIES = [
    "produce",
    "meat",
    "dairy",
    "bakery",
    "frozen",
    "pantry",
    "other",
]


class RecipeBase(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    type: str
    cuisine: str | None = None
    ingredients: list[str]


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(RecipeBase):
    pass


class RecipeRead(RecipeBase):
    id: int
    created_at: datetime
    cover_url: str | None = None


class RecipeSummary(BaseModel):
    id: int
    name: str
    type: str
    cuisine: str | None = None
    cover_url: str | None = None


class MealPlanEntryRead(BaseModel):
    id: int
    date: Date
    slot: str
    recipe_id: int
    sort_order: int
    recipe: RecipeSummary
    created_at: datetime


class EntryUpsert(BaseModel):
    recipe_id: int


class DateRange(BaseModel):
    start: Date
    end: Date


class ShoppingListItemRead(BaseModel):
    id: int
    text: str
    category: str
    checked: bool


class ShoppingListRead(BaseModel):
    id: int
    start_date: Date
    end_date: Date
    generated_at: datetime
    items_by_category: dict[str, list[ShoppingListItemRead]]


class ItemUpdate(BaseModel):
    checked: bool


class CookedDishLogRead(BaseModel):
    id: int
    date: Date
    slot: str
    recipe_id: int | None
    recipe_name: str
    kind: str
    meal_plan_entry_id: int | None
    photo_url: str | None
    logged_at: datetime
