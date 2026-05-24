"""SQLite migrations for existing mealpad.db files."""

from sqlalchemy import inspect, text

from . import models
from .db import engine


def _rebuild_meal_plan_entry(conn) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE mealplanentry_new (
                id INTEGER NOT NULL PRIMARY KEY,
                date DATE NOT NULL,
                slot VARCHAR NOT NULL,
                recipe_id INTEGER NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                FOREIGN KEY(recipe_id) REFERENCES recipe (id) ON DELETE CASCADE,
                UNIQUE (date, slot, recipe_id)
            )
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO mealplanentry_new (id, date, slot, recipe_id, sort_order, created_at)
            SELECT id, date, slot, recipe_id, 0, created_at FROM mealplanentry
            """
        )
    )
    conn.execute(text("DROP TABLE mealplanentry"))
    conn.execute(text("ALTER TABLE mealplanentry_new RENAME TO mealplanentry"))
    conn.execute(text("CREATE INDEX ix_mealplanentry_date ON mealplanentry (date)"))


def migrate_db() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("mealplanentry"):
        return

    columns = {col["name"] for col in inspector.get_columns("mealplanentry")}
    if "sort_order" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE mealplanentry ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
            )

    with engine.connect() as conn:
        create_sql = conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='mealplanentry'")
        ).scalar_one_or_none()
    if not create_sql:
        return

    normalized = create_sql.replace("\n", " ")
    if "UNIQUE (date, slot, recipe_id)" not in normalized:
        with engine.begin() as conn:
            _rebuild_meal_plan_entry(conn)

    _ensure_v2_tables()


def _ensure_v2_tables() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("cookeddishlog"):
        models.CookedDishLog.__table__.create(engine)
    if not inspector.has_table("recipeimage"):
        models.RecipeImage.__table__.create(engine)
