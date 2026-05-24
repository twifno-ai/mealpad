#!/usr/bin/env python3
"""一次性导入日餐 seed JSON。按菜名去重，可重复执行。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session

from app.db import engine, init_db
from app.services.japanese_recipes_seed import ImportResult, import_japanese_recipes


def main() -> int:
    init_db()
    with Session(engine) as session:
        result: ImportResult = import_japanese_recipes(session)
    print(f"已导入 {result.imported} 条，跳过 {result.skipped} 条（同名已存在）")
    if result.imported:
        parts = ", ".join(
            f"{t} {result.by_type[t]}"
            for t in sorted(result.by_type)
            if result.by_type[t]
        )
        print(f"  新增分类: {parts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
