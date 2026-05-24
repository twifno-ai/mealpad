import re
from pathlib import Path

from sqlmodel import Session, select

from app.models import Recipe
from app.services.french_recipes_seed import import_french_recipes, validate_production_seeds as validate_french
from app.services.italian_recipes_seed import validate_production_seeds as validate_italian
from app.services.recipe_seed import (
    AMERICAN_BUNDLE,
    FRENCH_BUNDLE,
    ITALIAN_BUNDLE,
    SPANISH_BUNDLE,
    default_seeds_dir,
    load_seed_file,
)
from app.services.spanish_recipes_seed import validate_production_seeds as validate_spanish
from app.services.american_recipes_seed import validate_production_seeds as validate_american

FIXTURES = Path(__file__).parent / "fixtures" / "seeds"
STEP_LINE = re.compile(r"^\d+\. ")
L3_NAME = re.compile(r"^.+（.+）$")
WESTERN_COUNTS = {"meat": 25, "veg": 15, "soup": 10, "other": 10}


def test_western_bundle_counts():
    for bundle in (FRENCH_BUNDLE, SPANISH_BUNDLE, ITALIAN_BUNDLE, AMERICAN_BUNDLE):
        assert bundle.expected_counts == WESTERN_COUNTS
        assert bundle.update_on_match == frozenset({"description", "ingredients", "cuisine"})


def test_import_french_from_fixture(session: Session):
    result = import_french_recipes(session, seeds_path=FIXTURES)
    assert result.imported == 2
    assert result.updated == 0
    recipes = session.exec(select(Recipe)).all()
    assert all(r.cuisine == "french" for r in recipes)


def test_french_upserts_existing_db_name(session: Session):
    session.add(
        Recipe(
            name="测试油封鸭（Confit de canard）",
            type="meat",
            description="旧",
            ingredients=["旧"],
            cuisine="other",
        )
    )
    session.commit()
    result = import_french_recipes(session, seeds_path=FIXTURES)
    assert result.imported == 1
    assert result.updated == 1
    kept = session.exec(
        select(Recipe).where(Recipe.name == "测试油封鸭（Confit de canard）")
    ).one()
    assert kept.cuisine == "french"
    assert kept.description.startswith("1. ")


def _assert_l3_and_steps(bundle):
    for filename in bundle.seed_files:
        for record in load_seed_file(default_seeds_dir() / filename, bundle):
            assert L3_NAME.match(record["name"]), record["name"]
            steps = [ln for ln in record["description"].splitlines() if STEP_LINE.match(ln)]
            assert 3 <= len(steps) <= 6, record["name"]


def test_french_production_seed_files_structure():
    assert validate_french(default_seeds_dir()) == WESTERN_COUNTS


def test_french_production_l3_names_and_steps():
    validate_french()
    _assert_l3_and_steps(FRENCH_BUNDLE)


def test_spanish_production_seed_files_structure():
    assert validate_spanish(default_seeds_dir()) == WESTERN_COUNTS


def test_spanish_production_l3_names_and_steps():
    validate_spanish()
    _assert_l3_and_steps(SPANISH_BUNDLE)


def test_italian_production_seed_files_structure():
    assert validate_italian(default_seeds_dir()) == WESTERN_COUNTS


def test_italian_production_l3_names_and_steps():
    validate_italian()
    _assert_l3_and_steps(ITALIAN_BUNDLE)


def test_american_production_seed_files_structure():
    assert validate_american(default_seeds_dir()) == WESTERN_COUNTS


def test_american_production_l3_names_and_steps():
    validate_american()
    _assert_l3_and_steps(AMERICAN_BUNDLE)
