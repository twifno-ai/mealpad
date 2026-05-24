#!/usr/bin/env python3
"""导入西班牙餐 seed JSON。同名则更新 description、ingredients、cuisine，否则插入。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session

from app.db import engine, init_db
from app.services.spanish_recipes_seed import ImportResult, import_spanish_recipes


def main() -> int:
    init_db()
    with Session(engine) as session:
        result: ImportResult = import_spanish_recipes(session)
    print(
        f"已导入 {result.imported} 条，更新 {result.updated} 条，跳过 {result.skipped} 条"
    )
    if result.imported:
        parts = ", ".join(
            f"{t} {result.by_type[t]}"
            for t in sorted(result.by_type)
            if result.by_type[t]
        )
        print(f"  新增分类: {parts}")
    if result.updated:
        parts = ", ".join(
            f"{t} {result.updated_by_type[t]}"
            for t in sorted(result.updated_by_type)
            if result.updated_by_type[t]
        )
        print(f"  更新分类: {parts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
