import re
from pathlib import Path

import pytest
from sqlmodel import Session, select

from app.models import Recipe
from app.services.classic_recipes_seed import (
    CLASSIC_BUNDLE,
    SeedValidationError,
    default_seeds_dir,
    import_classic_recipes,
    load_seed_file,
    validate_production_seeds,
)

FIXTURES = Path(__file__).parent / "fixtures" / "seeds"
STEP_LINE = re.compile(r"^\d+\. ")


def test_classic_bundle_counts():
    assert CLASSIC_BUNDLE.expected_counts == {"meat": 100, "veg": 60, "soup": 40, "other": 40}
    assert CLASSIC_BUNDLE.update_on_match == frozenset({"description", "ingredients", "cuisine"})
    assert CLASSIC_BUNDLE.default_cuisine == "chinese"


def test_import_from_fixture_dir(session: Session):
    result = import_classic_recipes(session, seeds_path=FIXTURES)
    assert result.imported == 2
    assert result.updated == 0
    assert result.skipped == 0
    recipes = session.exec(select(Recipe)).all()
    assert len(recipes) == 2
    assert recipes[0].name == "测试红烧肉"
    assert all(r.cuisine == "chinese" for r in recipes)


def test_upserts_existing_db_name(session: Session):
    session.add(
        Recipe(
            name="测试红烧肉",
            type="meat",
            description="已有",
            ingredients=["旧食材"],
            cuisine="western",
        )
    )
    session.commit()
    result = import_classic_recipes(session, seeds_path=FIXTURES)
    assert result.imported == 1
    assert result.updated == 1
    assert result.skipped == 0
    kept = session.exec(select(Recipe).where(Recipe.name == "测试红烧肉")).one()
    assert kept.description.startswith("1. ")
    assert kept.ingredients != ["旧食材"]
    assert kept.type == "meat"
    assert kept.cuisine == "chinese"


def test_duplicate_name_in_batch_upserts(session: Session, tmp_path: Path):
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    (seeds / "classic_recipes_meat.json").write_text("[]", encoding="utf-8")
    (seeds / "classic_recipes_soup.json").write_text("[]", encoding="utf-8")
    (seeds / "classic_recipes_other.json").write_text("[]", encoding="utf-8")
    (seeds / "classic_recipes_veg.json").write_text(
        """[
  {"name": "重复菜", "type": "veg", "description": "1. 第一条\\n2. 第二条\\n3. 第三条", "ingredients": ["白菜 适量"]},
  {"name": "重复菜", "type": "veg", "description": "1. 更新一\\n2. 更新二\\n3. 更新三", "ingredients": ["白菜 1颗"]}
]""",
        encoding="utf-8",
    )
    result = import_classic_recipes(session, seeds_path=seeds)
    assert result.imported == 1
    assert result.updated == 1
    kept = session.exec(select(Recipe).where(Recipe.name == "重复菜")).one()
    assert "更新一" in kept.description
    assert kept.ingredients == ["白菜 1颗"]


def test_second_run_updates_existing(session: Session):
    first = import_classic_recipes(session, seeds_path=FIXTURES)
    second = import_classic_recipes(session, seeds_path=FIXTURES)
    assert first.imported == 2
    assert second.imported == 0
    assert second.updated == 2
    assert second.skipped == 0


def test_invalid_type_raises(session: Session, tmp_path: Path):
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    bad = seeds / "classic_recipes_meat.json"
    bad.write_text(
        '[{"name":"坏数据","type":"veg","description":"1. a\\n2. b\\n3. c","ingredients":["x"]}]',
        encoding="utf-8",
    )
    with pytest.raises(SeedValidationError, match="不一致"):
        import_classic_recipes(session, seeds_path=seeds)


def test_production_seed_files_structure():
    counts = validate_production_seeds(default_seeds_dir())
    assert counts == {"meat": 100, "veg": 60, "soup": 40, "other": 40}


def test_production_descriptions_have_steps():
    validate_production_seeds()
    for filename in CLASSIC_BUNDLE.seed_files:
        for record in load_seed_file(default_seeds_dir() / filename):
            steps = [ln for ln in record["description"].splitlines() if STEP_LINE.match(ln)]
            assert len(steps) >= 3, record["name"]


def test_production_import_on_empty_db(session: Session):
    result = import_classic_recipes(session, seeds_path=default_seeds_dir())
    assert result.imported == 240
    assert result.updated == 0
    assert result.skipped == 0
    assert sum(result.by_type.values()) == 240
