"""SQLite migrations for existing mealpad.db files."""

import json
from pathlib import Path

from sqlalchemy import inspect, text

from . import models
from .db import engine

_SEEDS_DIR = Path(__file__).resolve().parent.parent / "data" / "seeds"


def _seed_names(pattern: str) -> set[str]:
    names: set[str] = set()
    for path in sorted(_SEEDS_DIR.glob(pattern)):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            for record in data:
                if isinstance(record, dict) and record.get("name"):
                    names.add(record["name"])
    return names


def _migrate_western_to_other(conn) -> None:
    conn.execute(text("UPDATE recipe SET cuisine = 'other' WHERE cuisine = 'western'"))


def _backfill_recipe_cuisine(conn) -> None:
    chinese = _seed_names("classic_recipes_*.json")
    japanese = _seed_names("japanese_recipes_*.json")
    for name in chinese:
        conn.execute(
            text("UPDATE recipe SET cuisine = 'chinese' WHERE name = :name AND cuisine IS NULL"),
            {"name": name},
        )
    for name in japanese:
        conn.execute(
            text("UPDATE recipe SET cuisine = 'japanese' WHERE name = :name AND cuisine IS NULL"),
            {"name": name},
        )


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
    if inspector.has_table("recipe"):
        columns = {col["name"] for col in inspector.get_columns("recipe")}
        if "cuisine" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE recipe ADD COLUMN cuisine TEXT"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_recipe_cuisine ON recipe (cuisine)"))
        with engine.begin() as conn:
            _backfill_recipe_cuisine(conn)
            _migrate_western_to_other(conn)

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
