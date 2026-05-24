# 经典中餐食谱种子数据 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 向食谱库追加 **240 道** 全国家常经典中餐（meat 100 / veg 60 / soup 40 / other 40），通过一次性导入脚本写入 SQLite，**按菜名去重**，可安全重复执行。

**Architecture:** 4 个 JSON seed 文件放在 `backend/data/seeds/`；可测试的导入逻辑在 `backend/app/services/classic_recipes_seed.py`；`backend/scripts/import_classic_recipes.py` 为薄 CLI；`make seed-recipes` 触发。不修改 server lifespan。

**Tech Stack:** Python 3.11+、SQLModel、SQLite、pytest。

**Spec:** [docs/superpowers/specs/2026-05-23-classic-recipes-seed-design.md](../specs/2026-05-23-classic-recipes-seed-design.md)

---

## File map

| File | Responsibility |
|---|---|
| `backend/app/services/classic_recipes_seed.py` | 加载 JSON、校验、按名去重、批量 INSERT |
| `backend/scripts/import_classic_recipes.py` | CLI 入口，打印 imported/skipped |
| `backend/data/seeds/classic_recipes_meat.json` | 100 道荤菜 |
| `backend/data/seeds/classic_recipes_veg.json` | 60 道素菜 |
| `backend/data/seeds/classic_recipes_soup.json` | 40 道汤 |
| `backend/data/seeds/classic_recipes_other.json` | 40 道 other |
| `backend/tests/test_import_classic_recipes.py` | JSON 结构 + 导入 + 去重 + 幂等 |
| `backend/tests/fixtures/seeds/` | 测试用小 JSON（批内重复、非法 type） |
| `Makefile` | `seed-recipes` 目标 |
| `README.md` | 一行使用说明 |

---

### Task 1: 导入服务与失败测试

**Files:**
- Create: `backend/app/services/classic_recipes_seed.py`
- Create: `backend/tests/fixtures/seeds/classic_recipes_meat.json`（2 条测试用）
- Create: `backend/tests/test_import_classic_recipes.py`
- Test: `backend/tests/test_import_classic_recipes.py`

- [ ] **Step 1: 写失败测试 — 空库导入 fixture**

```python
# backend/tests/test_import_classic_recipes.py
from pathlib import Path

import pytest
from sqlmodel import Session, select

from app.models import Recipe
from app.services.classic_recipes_seed import import_classic_recipes

FIXTURES = Path(__file__).parent / "fixtures" / "seeds"


def test_import_from_fixture_dir(session: Session):
    result = import_classic_recipes(session, seeds_path=FIXTURES)
    assert result.imported == 2
    assert result.skipped == 0
    recipes = session.exec(select(Recipe)).all()
    assert len(recipes) == 2
    assert recipes[0].name == "测试红烧肉"
```

```json
// backend/tests/fixtures/seeds/classic_recipes_meat.json
[
  {
    "name": "测试红烧肉",
    "type": "meat",
    "description": "测试用",
    "ingredients": ["五花肉 500g", "冰糖 适量", "生抽 2 勺"]
  },
  {
    "name": "测试鱼香肉丝",
    "type": "meat",
    "description": "测试用",
    "ingredients": ["猪里脊 300g", "木耳 适量", "胡萝卜 半根"]
  }
]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest tests/test_import_classic_recipes.py::test_import_from_fixture_dir -v`

Expected: FAIL — `ModuleNotFoundError` 或 `import_classic_recipes` 未定义

- [ ] **Step 3: 实现 `classic_recipes_seed.py`**

```python
# backend/app/services/classic_recipes_seed.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlmodel import Session, select

from app.models import Recipe
from app.schemas import RECIPE_TYPES

SEED_FILES = (
    "classic_recipes_meat.json",
    "classic_recipes_veg.json",
    "classic_recipes_soup.json",
    "classic_recipes_other.json",
)

EXPECTED_COUNTS: dict[str, int] = {
    "meat": 100,
    "veg": 60,
    "soup": 40,
    "other": 40,
}

FILE_TYPE: dict[str, str] = {
    "classic_recipes_meat.json": "meat",
    "classic_recipes_veg.json": "veg",
    "classic_recipes_soup.json": "soup",
    "classic_recipes_other.json": "other",
}


@dataclass
class ImportResult:
    imported: int = 0
    skipped: int = 0
    by_type: dict[str, int] = field(default_factory=lambda: {t: 0 for t in RECIPE_TYPES})


class SeedValidationError(ValueError):
    pass


def default_seeds_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "seeds"


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


def load_seed_file(path: Path) -> list[dict]:
    expected_type = FILE_TYPE.get(path.name)
    if expected_type is None:
        raise SeedValidationError(f"未知 seed 文件: {path.name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SeedValidationError(f"{path.name}: 根节点必须是数组")
    for record in data:
        _validate_record(record, expected_type, path.name)
    return data


def import_classic_recipes(session: Session, seeds_path: Path | None = None) -> ImportResult:
    seeds_path = seeds_path or default_seeds_dir()
    seen_names = set(session.exec(select(Recipe.name)).all())
    result = ImportResult()

    for filename in SEED_FILES:
        path = seeds_path / filename
        if not path.is_file():
            continue
        for record in load_seed_file(path):
            name = record["name"]
            if name in seen_names:
                result.skipped += 1
                continue
            recipe = Recipe(
                name=name,
                type=record["type"],
                description=record["description"],
                ingredients=record["ingredients"],
            )
            session.add(recipe)
            seen_names.add(name)
            result.imported += 1
            result.by_type[record["type"]] += 1

    session.commit()
    return result


def validate_production_seeds(seeds_path: Path | None = None) -> dict[str, int]:
    """校验生产 seed 文件条数与 type；供 pytest 使用。"""
    seeds_path = seeds_path or default_seeds_dir()
    counts: dict[str, int] = {t: 0 for t in RECIPE_TYPES}
    names: set[str] = set()
    for filename in SEED_FILES:
        path = seeds_path / filename
        if not path.is_file():
            raise SeedValidationError(f"缺少 seed 文件: {path}")
        records = load_seed_file(path)
        expected = FILE_TYPE[filename]
        counts[expected] += len(records)
        for record in records:
            if record["name"] in names:
                raise SeedValidationError(f"seed 内重复菜名: {record['name']}")
            names.add(record["name"])
    for rtype, expected in EXPECTED_COUNTS.items():
        if counts[rtype] != expected:
            raise SeedValidationError(f"{rtype} 应为 {expected} 条，实际 {counts[rtype]}")
    if len(names) != sum(EXPECTED_COUNTS.values()):
        raise SeedValidationError(f"合计应为 240 条，实际 {len(names)}")
    return counts
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest tests/test_import_classic_recipes.py::test_import_from_fixture_dir -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/classic_recipes_seed.py \
  backend/tests/test_import_classic_recipes.py \
  backend/tests/fixtures/seeds/classic_recipes_meat.json
git commit -m "feat: add classic recipes seed import service"
```

---

### Task 2: 去重、幂等与校验失败测试

**Files:**
- Modify: `backend/tests/test_import_classic_recipes.py`
- Create: `backend/tests/fixtures/seeds/classic_recipes_veg.json`（批内重复）
- Create: `backend/tests/fixtures/seeds/classic_recipes_soup.json`（空数组占位）
- Create: `backend/tests/fixtures/seeds/classic_recipes_other.json`（空数组占位）

- [ ] **Step 1: 写 DB 去重测试**

```python
def test_skips_existing_db_name(session: Session):
    session.add(
        Recipe(
            name="测试红烧肉",
            type="meat",
            description="已有",
            ingredients=["旧食材"],
        )
    )
    session.commit()
    result = import_classic_recipes(session, seeds_path=FIXTURES)
    assert result.imported == 1
    assert result.skipped == 1
    kept = session.exec(select(Recipe).where(Recipe.name == "测试红烧肉")).one()
    assert kept.description == "已有"
    assert kept.ingredients == ["旧食材"]
```

- [ ] **Step 2: 写批内重复 fixture 与测试**

```json
// backend/tests/fixtures/seeds/classic_recipes_veg.json
[
  {
    "name": "重复菜",
    "type": "veg",
    "description": "第一条",
    "ingredients": ["白菜 适量"]
  },
  {
    "name": "重复菜",
    "type": "veg",
    "description": "第二条应被跳过",
    "ingredients": ["白菜 适量"]
  }
]
```

```python
def test_skips_duplicate_within_batch(session: Session, tmp_path: Path):
  # 单独小目录，仅 meat 空 + veg 重复
  seeds = tmp_path / "seeds"
  seeds.mkdir()
  (seeds / "classic_recipes_meat.json").write_text("[]", encoding="utf-8")
  (seeds / "classic_recipes_soup.json").write_text("[]", encoding="utf-8")
  (seeds / "classic_recipes_other.json").write_text("[]", encoding="utf-8")
  (seeds / "classic_recipes_veg.json").write_text(
      (FIXTURES / "classic_recipes_veg.json").read_text(encoding="utf-8"),
      encoding="utf-8",
  )
  result = import_classic_recipes(session, seeds_path=seeds)
  assert result.imported == 1
  assert result.skipped == 1
  assert len(session.exec(select(Recipe).where(Recipe.name == "重复菜")).all()) == 1
```

- [ ] **Step 3: 写幂等测试**

```python
def test_idempotent_second_run(session: Session):
    first = import_classic_recipes(session, seeds_path=FIXTURES)
    second = import_classic_recipes(session, seeds_path=FIXTURES)
    assert first.imported == 2
    assert second.imported == 0
    assert second.skipped == 2
```

- [ ] **Step 4: 写非法 type 测试**

```python
def test_invalid_type_raises(session: Session, tmp_path: Path):
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    bad = seeds / "classic_recipes_meat.json"
    bad.write_text(
        '[{"name":"坏数据","type":"veg","description":"","ingredients":["x"]}]',
        encoding="utf-8",
    )
    with pytest.raises(SeedValidationError, match="不一致"):
        import_classic_recipes(session, seeds_path=seeds)
```

在文件顶部增加：`from app.services.classic_recipes_seed import SeedValidationError`

- [ ] **Step 5: 创建空 soup/other fixture**

```json
[]
```

分别写入 `classic_recipes_soup.json` 与 `classic_recipes_other.json`（测试 fixture 目录）。

- [ ] **Step 6: 运行全部 import 测试**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest tests/test_import_classic_recipes.py -v`

Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add backend/tests/test_import_classic_recipes.py backend/tests/fixtures/seeds/
git commit -m "test: classic recipes import dedup and validation"
```

---

### Task 3: CLI 脚本与 Makefile

**Files:**
- Create: `backend/scripts/import_classic_recipes.py`
- Modify: `Makefile`

- [ ] **Step 1: 写 CLI 脚本**

```python
#!/usr/bin/env python3
"""一次性导入经典中餐 seed JSON。按菜名去重，可重复执行。"""
from __future__ import annotations

import sys
from pathlib import Path

# 允许从 backend/ 目录运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session

from app.db import engine, init_db
from app.services.classic_recipes_seed import ImportResult, import_classic_recipes


def main() -> int:
    init_db()
    with Session(engine) as session:
        result: ImportResult = import_classic_recipes(session)
    print(
        f"已导入 {result.imported} 条，跳过 {result.skipped} 条（同名已存在）"
    )
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
```

- [ ] **Step 2: 添加 Makefile 目标**

```makefile
.PHONY: seed-recipes

seed-recipes: setup-backend
	cd backend && .venv/bin/python scripts/import_classic_recipes.py
```

- [ ] **Step 3: 手动验证 CLI（seed 尚未齐全时应能跑通 fixture 或 0 条）**

Run: `make seed-recipes`

Expected: 无 traceback；输出 imported/skipped 行

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/import_classic_recipes.py Makefile
git commit -m "feat: add make seed-recipes import CLI"
```

---

### Task 4: 生产 seed — `classic_recipes_meat.json`（100 道）

**Files:**
- Create: `backend/data/seeds/classic_recipes_meat.json`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p backend/data/seeds
```

- [ ] **Step 2: 编写 100 条完整 JSON**

按 [附录 A](#附录-a-meat-100) 菜名逐条编写。每条格式：

```json
{
  "name": "番茄炒蛋",
  "type": "meat",
  "description": "家常下饭菜，酸甜适口。",
  "ingredients": ["鸡蛋 3 个", "番茄 2 个", "盐 适量", "糖 少许", "葱花 少许"]
}
```

要求：
- `name` 与附录 A 完全一致，100 条互不重复
- 每道 4–10 条中文食材
- 南北家常混合，避免重复「换名同菜」

- [ ] **Step 3: 本地校验条数**

Run:

```bash
cd backend && .venv/bin/python -c "
from app.services.classic_recipes_seed import load_seed_file, default_seeds_dir
p = default_seeds_dir() / 'classic_recipes_meat.json'
print(len(load_seed_file(p)))
"
```

Expected: `100`

- [ ] **Step 4: Commit**

```bash
git add backend/data/seeds/classic_recipes_meat.json
git commit -m "data: add 100 classic meat recipe seeds"
```

---

### Task 5: 生产 seed — `classic_recipes_veg.json`（60 道）

**Files:**
- Create: `backend/data/seeds/classic_recipes_veg.json`

- [ ] **Step 1: 按 [附录 B](#附录-b-veg-60) 编写 60 条 JSON**

- [ ] **Step 2: 校验**

Expected: `load_seed_file` 返回 60 条；与附录 A 菜名无交叉重复

- [ ] **Step 3: Commit**

```bash
git add backend/data/seeds/classic_recipes_veg.json
git commit -m "data: add 60 classic veg recipe seeds"
```

---

### Task 6: 生产 seed — soup（40）+ other（40）

**Files:**
- Create: `backend/data/seeds/classic_recipes_soup.json`
- Create: `backend/data/seeds/classic_recipes_other.json`

- [ ] **Step 1: 按 [附录 C](#附录-c-soup-40) 编写 40 条汤品 JSON**

- [ ] **Step 2: 按 [附录 D](#附录-d-other-40) 编写 40 条 other JSON**

`other` 以主食、小吃、简餐为主（炒饭、面食、粥、点心），不含纯饮料。

- [ ] **Step 3: 全库名称交叉检查**

Run:

```bash
cd backend && .venv/bin/python -c "
from app.services.classic_recipes_seed import validate_production_seeds
print(validate_production_seeds())
"
```

Expected: `{'meat': 100, 'veg': 60, 'soup': 40, 'other': 40}`，无 SeedValidationError

- [ ] **Step 4: Commit**

```bash
git add backend/data/seeds/classic_recipes_soup.json backend/data/seeds/classic_recipes_other.json
git commit -m "data: add classic soup and other recipe seeds"
```

---

### Task 7: 生产 JSON 结构测试与全量 pytest

**Files:**
- Modify: `backend/tests/test_import_classic_recipes.py`

- [ ] **Step 1: 添加生产 seed 结构测试**

```python
from app.services.classic_recipes_seed import (
    default_seeds_dir,
    validate_production_seeds,
)


def test_production_seed_files_structure():
    counts = validate_production_seeds(default_seeds_dir())
    assert counts == {"meat": 100, "veg": 60, "soup": 40, "other": 40}


def test_production_import_on_empty_db(session: Session):
    result = import_classic_recipes(session, seeds_path=default_seeds_dir())
    assert result.imported == 240
    assert result.skipped == 0
    assert sum(result.by_type.values()) == 240
```

- [ ] **Step 2: 运行全量后端测试**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest -v`

Expected: 全部 PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_import_classic_recipes.py
git commit -m "test: validate production classic recipe seeds"
```

---

### Task 8: 文档与验收

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-23-classic-recipes-seed-design.md`

- [ ] **Step 1: README 增加 seed 说明**

在 Setup 或 Recipes 相关段落后添加：

```markdown
### Seed classic recipes (optional)

To bulk-add ~240 home-style Chinese recipes to your library:

```bash
make seed-recipes
```

Recipes with the same name are skipped, so this command is safe to run more than once.
```

- [ ] **Step 2: 更新 spec 状态**

将 spec 顶部 `状态：待实现` 改为 `状态：已完成`，`实现计划` 链接指向本文件。

- [ ] **Step 3: 手动验收**

```bash
make seed-recipes          # 第一次：应 imported≈240
make seed-recipes          # 第二次：应 imported=0, skipped≈240
make dev-backend           # 食谱页可见新条目
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/superpowers/specs/2026-05-23-classic-recipes-seed-design.md
git commit -m "docs: document classic recipe seed import"
```

---

## 附录 A: meat（100）

| # | 菜名 | # | 菜名 | # | 菜名 | # | 菜名 |
|---|------|---|------|---|------|---|------|
| 1 | 番茄炒蛋 | 26 | 京酱肉丝 | 51 | 姜葱炒蟹 | 76 | 雪菜肉丝 |
| 2 | 红烧肉 | 27 | 木须肉 | 52 | 蛤蜊蒸蛋 | 77 | 榨菜肉丝 |
| 3 | 鱼香肉丝 | 28 | 熘肝尖 | 53 | 香菇滑鸡 | 78 | 鱼香茄子 |
| 4 | 宫保鸡丁 | 29 | 葱爆羊肉 | 54 | 栗子鸡 | 79 | 肉末茄子 |
| 5 | 可乐鸡翅 | 30 | 孜然羊肉 | 55 | 咖喱鸡 | 80 | 干锅花菜 |
| 6 | 糖醋里脊 | 31 | 红烧狮子头 | 56 | 照烧鸡腿 | 81 | 干锅土豆片 |
| 7 | 回锅肉 | 32 | 四喜丸子 | 57 | 盐焗鸡 | 82 | 干锅虾 |
| 8 | 麻婆豆腐 | 33 | 糖醋排骨 | 58 | 棒棒鸡 | 83 | 香辣虾 |
| 9 | 青椒肉丝 | 34 | 蒜苔炒肉 | 59 | 大盘鸡 | 84 | 家常麻辣香锅 |
| 10 | 土豆烧牛肉 | 35 | 芹菜炒肉丝 | 60 | 红烧牛腩 | 85 | 家常毛血旺 |
| 11 | 可乐排骨 | 36 | 木耳炒肉 | 61 | 番茄牛腩 | 86 | 水煮肉片 |
| 12 | 蒜香排骨 | 37 | 茭白炒肉丝 | 62 | 土豆炖牛腩 | 87 | 水煮鱼 |
| 13 | 粉蒸肉 | 38 | 苦瓜炒肉 | 63 | 黑椒牛柳 | 88 | 酸菜鱼 |
| 14 | 东坡肉 | 39 | 豆角炒肉 | 64 | 蚝油牛肉 | 89 | 剁椒蒸排骨 |
| 15 | 梅菜扣肉 | 40 | 西葫芦炒肉 | 65 | 小炒黄牛肉 | 90 | 粉蒸排骨 |
| 16 | 白切鸡 | 41 | 杭椒炒肉 | 66 | 孜然牛肉 | 91 | 酱爆鸡丁 |
| 17 | 口水鸡 | 42 | 农家小炒肉 | 67 | 牙签牛肉 | 92 | 滑蛋虾仁 |
| 18 | 黄焖鸡 | 43 | 剁椒鱼头 | 68 | 红烧猪手 | 93 | 虾仁炒蛋 |
| 19 | 三杯鸡 | 44 | 红烧鲤鱼 | 69 | 酱猪蹄 | 94 | 西兰花炒虾仁 |
| 20 | 啤酒鸭 | 45 | 糖醋鱼 | 70 | 蒜泥白肉 | 95 | 腰果虾仁 |
| 21 | 啤酒鱼 | 46 | 干烧黄花鱼 | 71 | 红烧肉炖蛋 | 96 | 酿豆腐 |
| 22 | 红烧带鱼 | 47 | 香煎带鱼 | 72 | 酿茄子 | 97 | 狮子头炖白菜 |
| 23 | 清蒸鲈鱼 | 48 | 酱爆鱿鱼 | 73 | 干煸牛肉丝 | 98 | 尖椒炒大肠 |
| 24 | 干煸豆角 | 49 | 白灼虾 | 74 | 溜肉段 | 99 | 锅包肉 |
| 25 | 蚂蚁上树 | 50 | 油焖大虾 | 75 | 软炸里脊 | 100 | 红烧蹄髈 |

## 附录 B: veg（60）

| # | 菜名 | # | 菜名 | # | 菜名 |
|---|------|---|------|---|------|
| 1 | 地三鲜 | 21 | 清炒生菜 | 41 | 清炒丝瓜 |
| 2 | 蒜蓉西兰花 | 22 | 蚝油生菜 | 42 | 蒜蓉粉丝蒸丝瓜 |
| 3 | 清炒时蔬 | 23 | 清炒小白菜 | 43 | 清炒黄瓜 |
| 4 | 干煸四季豆 | 24 | 香菇青菜 | 44 | 拍黄瓜 |
| 5 | 虎皮青椒 | 25 | 油菜炒蘑菇 | 45 | 凉拌黄瓜 |
| 6 | 香干炒芹菜 | 26 | 清炒空心菜 | 46 | 老虎菜 |
| 7 | 家常豆腐 | 27 | 腐乳空心菜 | 47 | 凉拌木耳 |
| 8 | 鱼香豆腐 | 28 | 清炒豆苗 | 48 | 凉拌海带丝 |
| 9 | 红烧豆腐 | 29 | 清炒荷兰豆 | 49 | 干煸菜花 |
| 10 | 蚝油豆腐 | 30 | 荷塘小炒 | 50 | 清炒花菜 |
| 11 | 素炒三丝 | 31 | 清炒藕片 | 51 | 素炒蘑菇 |
| 12 | 醋溜白菜 | 32 | 醋溜土豆丝 | 52 | 干香菇炒油菜 |
| 13 | 上汤娃娃菜 | 33 | 干煸土豆条 | 53 | 素烧茄子 |
| 14 | 干锅包菜 | 34 | 清炒山药 | 54 | 鱼香茄条 |
| 15 | 手撕包菜 | 35 | 木耳山药 | 55 | 家常炖茄子 |
| 16 | 清炒菠菜 | 36 | 清炒芦笋 | 56 | 清炒豆芽 |
| 17 | 蒜蓉菠菜 | 37 | 清炒莴笋 | 57 | 醋溜豆芽 |
| 18 | 凉拌菠菜 | 38 | 鱼香莴笋 | 58 | 素炒合菜 |
| 19 | 清炒油麦菜 | 39 | 清炒西葫芦 | 59 | 素炒什锦 |
| 20 | 清炒豌豆苗 | 40 | 清炒冬瓜 | 60 | 罗汉斋 |

## 附录 C: soup（40）

| # | 菜名 | # | 菜名 | # | 菜名 | # | 菜名 |
|---|------|---|------|---|------|---|------|
| 1 | 番茄蛋花汤 | 11 | 菌菇汤 | 21 | 财鱼豆腐汤 | 31 | 罗宋汤 |
| 2 | 紫菜蛋花汤 | 12 | 酸辣汤 | 22 | 虫草花鸡汤 | 32 | 上汤时蔬 |
| 3 | 冬瓜排骨汤 | 13 | 西湖牛肉羹 | 23 | 淮山老鸡汤 | 33 | 海带排骨汤 |
| 4 | 玉米排骨汤 | 14 | 鲫鱼豆腐汤 | 24 | 花旗参乌鸡汤 | 34 | 墨鱼猪蹄汤 |
| 5 | 萝卜排骨汤 | 15 | 鱼头豆腐汤 | 25 | 木瓜炖银耳 | 35 | 节瓜咸蛋汤 |
| 6 | 莲藕排骨汤 | 16 | 丝瓜蛋汤 | 26 | 银耳莲子汤 | 36 | 西洋菜猪骨汤 |
| 7 | 黄豆猪蹄汤 | 17 | 菠菜蛋汤 | 27 | 排骨山药汤 | 37 | 粉葛猪骨汤 |
| 8 | 老鸭汤 | 18 | 小白菜豆腐汤 | 28 | 牛尾汤 | 38 | 花旗参瘦肉汤 |
| 9 | 老母鸡汤 | 19 | 疙瘩汤 | 29 | 羊肉汤 | 39 | 竹荪炖鸡汤 |
| 10 | 三鲜汤 | 20 | 西红柿疙瘩汤 | 30 | 羊杂汤 | 40 | 咸鸭蛋芥菜汤 |

## 附录 D: other（40）

| # | 菜名 | # | 菜名 | # | 菜名 | # | 菜名 |
|---|------|---|------|---|------|---|------|
| 1 | 蛋炒饭 | 11 | 刀削面 | 21 | 花卷 | 31 | 烙饼 |
| 2 | 扬州炒饭 | 12 | 牛肉面 | 22 | 馒头 | 32 | 发糕 |
| 3 | 葱油拌面 | 13 | 炒河粉 | 23 | 葱油饼 | 33 | 玉米窝头 |
| 4 | 蒸水蛋 | 14 | 炒米粉 | 24 | 手抓饼 | 34 | 红薯饭 |
| 5 | 家常小笼包 | 15 | 广式肠粉 | 25 | 馅饼 | 35 | 酱油炒饭 |
| 6 | 手工饺子 | 16 | 白粥 | 26 | 咸肉粽 | 36 | 腊味煲仔饭 |
| 7 | 鲜肉馄饨 | 17 | 皮蛋瘦肉粥 | 27 | 烧卖 | 37 | 朝鲜冷面 |
| 8 | 阳春面 | 18 | 海鲜粥 | 28 | 春卷 | 38 | 石锅拌饭 |
| 9 | 炸酱面 | 19 | 小米南瓜粥 | 29 | 锅贴 | 39 | 炒饼 |
| 10 | 热干面 | 20 | 八宝粥 | 30 | 蒸饺 | 40 | 炒年糕 |

---

## 验收清单（与 spec 对齐）

- [ ] 四个 JSON 合计 240 条，配额 100/60/40/40
- [ ] 240 个菜名全局唯一
- [ ] `make seed-recipes` 追加写入且同名跳过
- [ ] 连续两次执行第二次 imported=0
- [ ] `cd backend && pytest` 全部通过
- [ ] 无 `main.py` lifespan 改动
- [ ] JSON 进 git；`mealpad.db` 仍 gitignore
