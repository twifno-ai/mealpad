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
