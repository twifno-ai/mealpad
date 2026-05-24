from datetime import date as Date
from datetime import datetime

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel, UniqueConstraint


class Recipe(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str = ""
    type: str = Field(index=True)
    ingredients: list[str] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MealPlanEntry(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("date", "slot", "recipe_id"),)

    id: int | None = Field(default=None, primary_key=True)
    date: Date = Field(index=True)
    slot: str
    recipe_id: int = Field(foreign_key="recipe.id", ondelete="CASCADE")
    sort_order: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ShoppingList(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("start_date", "end_date"),)

    id: int | None = Field(default=None, primary_key=True)
    start_date: Date = Field(index=True)
    end_date: Date
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ShoppingListItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    shopping_list_id: int = Field(foreign_key="shoppinglist.id", index=True, ondelete="CASCADE")
    text: str
    category: str = ""
    checked: bool = False


class CookedDishLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    date: Date = Field(index=True)
    slot: str
    recipe_id: int | None = Field(default=None, foreign_key="recipe.id", ondelete="SET NULL")
    recipe_name: str
    kind: str
    meal_plan_entry_id: int | None = Field(
        default=None,
        foreign_key="mealplanentry.id",
        ondelete="SET NULL",
        unique=True,
    )
    photo_path: str | None = None
    logged_at: datetime = Field(default_factory=datetime.utcnow)


class RecipeImage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    recipe_id: int = Field(foreign_key="recipe.id", ondelete="CASCADE", index=True)
    file_path: str
    sort_order: int = 0
    is_cover: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
