import re
from pathlib import Path

import pytest
from sqlmodel import Session, select

from app.models import Recipe
from app.services.japanese_recipes_seed import (
    JAPANESE_BUNDLE,
    default_seeds_dir,
    import_japanese_recipes,
    load_seed_file,
    validate_production_seeds,
)
from app.services.recipe_seed import SeedValidationError

FIXTURES = Path(__file__).parent / "fixtures" / "seeds"
STEP_LINE = re.compile(r"^\d+\. ")


def test_japanese_bundle_counts():
    assert JAPANESE_BUNDLE.expected_counts == {"meat": 50, "veg": 30, "soup": 20, "other": 20}
    assert JAPANESE_BUNDLE.default_cuisine == "japanese"


def test_import_from_fixture_dir(session: Session):
    result = import_japanese_recipes(session, seeds_path=FIXTURES)
    assert result.imported == 2
    assert result.skipped == 0
    recipes = session.exec(select(Recipe)).all()
    assert len(recipes) == 2
    assert recipes[0].name == "测试照烧（テスト照り焼き）"
    assert all(r.cuisine == "japanese" for r in recipes)


def test_skips_existing_db_name(session: Session):
    session.add(
        Recipe(
            name="测试照烧（テスト照り焼き）",
            type="meat",
            description="已有",
            ingredients=["旧食材"],
        )
    )
    session.commit()
    result = import_japanese_recipes(session, seeds_path=FIXTURES)
    assert result.imported == 1
    assert result.skipped == 1
    kept = session.exec(select(Recipe).where(Recipe.name == "测试照烧（テスト照り焼き）")).one()
    assert kept.description == "已有"


def test_skips_duplicate_within_batch(session: Session, tmp_path: Path):
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    (seeds / "japanese_recipes_veg.json").write_text("[]", encoding="utf-8")
    (seeds / "japanese_recipes_soup.json").write_text("[]", encoding="utf-8")
    (seeds / "japanese_recipes_other.json").write_text("[]", encoding="utf-8")
    (seeds / "japanese_recipes_meat.json").write_text(
        """[
  {"name": "重复日餐", "type": "meat", "description": "1. a\\n2. b\\n3. c", "ingredients": ["x"]},
  {"name": "重复日餐", "type": "meat", "description": "1. a\\n2. b\\n3. c", "ingredients": ["x"]}
]""",
        encoding="utf-8",
    )
    result = import_japanese_recipes(session, seeds_path=seeds)
    assert result.imported == 1
    assert result.skipped == 1


def test_idempotent_second_run(session: Session):
    first = import_japanese_recipes(session, seeds_path=FIXTURES)
    second = import_japanese_recipes(session, seeds_path=FIXTURES)
    assert first.imported == 2
    assert second.imported == 0
    assert second.skipped == 2


def test_invalid_type_raises(session: Session, tmp_path: Path):
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    bad = seeds / "japanese_recipes_meat.json"
    bad.write_text(
        '[{"name":"坏（バド）","type":"veg","description":"1. a\\n2. b\\n3. c","ingredients":["x"]}]',
        encoding="utf-8",
    )
    with pytest.raises(SeedValidationError, match="不一致"):
        import_japanese_recipes(session, seeds_path=seeds)


def test_production_seed_files_structure():
    counts = validate_production_seeds(default_seeds_dir())
    assert counts == {"meat": 50, "veg": 30, "soup": 20, "other": 20}


def test_production_import_on_empty_db(session: Session):
    result = import_japanese_recipes(session, seeds_path=default_seeds_dir())
    assert result.imported == 120
    assert result.skipped == 0
    assert sum(result.by_type.values()) == 120


def test_production_descriptions_have_steps():
    validate_production_seeds()
    for filename in JAPANESE_BUNDLE.seed_files:
        for record in load_seed_file(default_seeds_dir() / filename):
            steps = [ln for ln in record["description"].splitlines() if STEP_LINE.match(ln)]
            assert len(steps) >= 3, record["name"]
            assert "（" in record["name"] and "）" in record["name"]
