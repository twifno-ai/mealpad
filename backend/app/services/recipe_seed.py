from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlmodel import Session, select

from app.models import Recipe
from app.schemas import RECIPE_TYPES

@dataclass(frozen=True)
class SeedBundle:
    name: str
    seed_files: tuple[str, ...]
    file_type: dict[str, str]
    expected_counts: dict[str, int]
    update_on_match: frozenset[str] = frozenset()
    default_cuisine: str | None = None


CLASSIC_BUNDLE = SeedBundle(
    name="classic",
    seed_files=(
        "classic_recipes_meat.json",
        "classic_recipes_veg.json",
        "classic_recipes_soup.json",
        "classic_recipes_other.json",
    ),
    file_type={
        "classic_recipes_meat.json": "meat",
        "classic_recipes_veg.json": "veg",
        "classic_recipes_soup.json": "soup",
        "classic_recipes_other.json": "other",
    },
    expected_counts={"meat": 100, "veg": 60, "soup": 40, "other": 40},
    update_on_match=frozenset({"description", "ingredients", "cuisine"}),
    default_cuisine="chinese",
)

JAPANESE_BUNDLE = SeedBundle(
    name="japanese",
    seed_files=(
        "japanese_recipes_meat.json",
        "japanese_recipes_veg.json",
        "japanese_recipes_soup.json",
        "japanese_recipes_other.json",
    ),
    file_type={
        "japanese_recipes_meat.json": "meat",
        "japanese_recipes_veg.json": "veg",
        "japanese_recipes_soup.json": "soup",
        "japanese_recipes_other.json": "other",
    },
    expected_counts={"meat": 50, "veg": 30, "soup": 20, "other": 20},
    default_cuisine="japanese",
)


@dataclass
class ImportResult:
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    by_type: dict[str, int] = field(default_factory=lambda: {t: 0 for t in RECIPE_TYPES})
    updated_by_type: dict[str, int] = field(default_factory=lambda: {t: 0 for t in RECIPE_TYPES})


class SeedValidationError(ValueError):
    pass


def default_seeds_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "seeds"


def _validate_record(record: dict, expected_type: str, source: str) -> None:
    if not isinstance(record, dict):
        raise SeedValidationError(f"{source}: 每条记录必须是对象")
    name = record.get("name")
    if not name or not isinstance(name, str):
        raise SeedValidationError(f"{source}: name 必填且为非空字符串")
    rtype = record.get("type")
    if rtype not in RECIPE_TYPES:
        raise SeedValidationError(f"{source}: 非法 type {rtype!r}")
    if rtype != expected_type:
        raise SeedValidationError(f"{source}: type {rtype!r} 与文件期望 {expected_type!r} 不一致")
    if "description" not in record or not isinstance(record["description"], str):
        raise SeedValidationError(f"{source}: description 必须为字符串")
    ingredients = record.get("ingredients")
    if not isinstance(ingredients, list) or not ingredients:
        raise SeedValidationError(f"{source}: ingredients 必须为非空数组")
    if not all(isinstance(i, str) and i.strip() for i in ingredients):
        raise SeedValidationError(f"{source}: ingredients 每项必须为非空字符串")


def load_seed_file(path: Path, bundle: SeedBundle) -> list[dict]:
    expected_type = bundle.file_type.get(path.name)
    if expected_type is None:
        raise SeedValidationError(f"未知 seed 文件: {path.name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SeedValidationError(f"{path.name}: 根节点必须是数组")
    for record in data:
        _validate_record(record, expected_type, path.name)
    return data


def _seed_field_value(bundle: SeedBundle, field_name: str, record: dict):
    if field_name == "cuisine":
        return bundle.default_cuisine
    return record[field_name]


def import_recipe_seeds(
    session: Session,
    bundle: SeedBundle,
    seeds_path: Path | None = None,
) -> ImportResult:
    seeds_path = seeds_path or default_seeds_dir()
    existing = {
        recipe.name: recipe
        for recipe in session.exec(select(Recipe)).all()
    }
    result = ImportResult()

    for filename in bundle.seed_files:
        path = seeds_path / filename
        if not path.is_file():
            continue
        for record in load_seed_file(path, bundle):
            name = record["name"]
            if name in existing:
                if not bundle.update_on_match:
                    result.skipped += 1
                    continue
                recipe = existing[name]
                for field_name in bundle.update_on_match:
                    setattr(recipe, field_name, _seed_field_value(bundle, field_name, record))
                session.add(recipe)
                result.updated += 1
                result.updated_by_type[record["type"]] += 1
                continue
            recipe = Recipe(
                name=name,
                type=record["type"],
                description=record["description"],
                ingredients=record["ingredients"],
                cuisine=bundle.default_cuisine,
            )
            session.add(recipe)
            existing[name] = recipe
            result.imported += 1
            result.by_type[record["type"]] += 1

    session.commit()
    return result


def validate_production_seeds(
    bundle: SeedBundle,
    seeds_path: Path | None = None,
) -> dict[str, int]:
    """校验生产 seed 文件条数与 type；供 pytest 使用。"""
    seeds_path = seeds_path or default_seeds_dir()
    counts: dict[str, int] = {t: 0 for t in RECIPE_TYPES}
    names: set[str] = set()
    for filename in bundle.seed_files:
        path = seeds_path / filename
        if not path.is_file():
            raise SeedValidationError(f"缺少 seed 文件: {path}")
        records = load_seed_file(path, bundle)
        expected = bundle.file_type[filename]
        counts[expected] += len(records)
        for record in records:
            if record["name"] in names:
                raise SeedValidationError(f"seed 内重复菜名: {record['name']}")
            names.add(record["name"])
    for rtype, expected in bundle.expected_counts.items():
        if counts[rtype] != expected:
            raise SeedValidationError(f"{rtype} 应为 {expected} 条，实际 {counts[rtype]}")
    total = sum(bundle.expected_counts.values())
    if len(names) != total:
        raise SeedValidationError(f"合计应为 {total} 条，实际 {len(names)}")
    return counts
