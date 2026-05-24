"""French recipe seeds — thin wrapper around recipe_seed."""

from __future__ import annotations

from pathlib import Path

from sqlmodel import Session

from .recipe_seed import (
    FRENCH_BUNDLE,
    ImportResult,
    default_seeds_dir,
    import_recipe_seeds,
    load_seed_file as _load_seed_file,
    validate_production_seeds as _validate_production_seeds,
)

SEED_FILES = FRENCH_BUNDLE.seed_files
EXPECTED_COUNTS = FRENCH_BUNDLE.expected_counts
FILE_TYPE = FRENCH_BUNDLE.file_type


def load_seed_file(path: Path) -> list[dict]:
    return _load_seed_file(path, FRENCH_BUNDLE)


def import_french_recipes(session: Session, seeds_path: Path | None = None) -> ImportResult:
    return import_recipe_seeds(session, FRENCH_BUNDLE, seeds_path)


def validate_production_seeds(seeds_path: Path | None = None) -> dict[str, int]:
    return _validate_production_seeds(FRENCH_BUNDLE, seeds_path)


__all__ = [
    "FRENCH_BUNDLE",
    "EXPECTED_COUNTS",
    "FILE_TYPE",
    "ImportResult",
    "SEED_FILES",
    "default_seeds_dir",
    "import_french_recipes",
    "load_seed_file",
    "validate_production_seeds",
]
