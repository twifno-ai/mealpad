# 西餐食谱种子数据（法/西/意/美）— Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩充 **240 道** 西餐 seed（法/西/意/美各 60），扩展 `cuisine` 枚举（移除 `western`），四条独立 `make seed-*-recipes` 命令，upsert 与中餐一致。

**Architecture:** 在 `recipe_seed.py` 新增四个 `SeedBundle`（各带 `default_cuisine` + `update_on_match`）；薄 wrapper + CLI 复制中餐模式；`migrate.py` 将旧 `western` 改为 `other`；16 个 JSON 生产数据。

**Tech Stack:** Python 3.11+、FastAPI/SQLModel、pytest、React/TypeScript。

**Spec:** [docs/superpowers/specs/2026-05-24-western-recipes-seed-design.md](../specs/2026-05-24-western-recipes-seed-design.md)

---

## File map

| File | Responsibility |
|---|---|
| `backend/app/schemas.py` | `CUISINE_TYPES` 枚举 |
| `backend/app/migrate.py` | `western`→`other`；可选 backfill 四国 seed 名 |
| `backend/app/services/recipe_seed.py` | 四个新 `SeedBundle` |
| `backend/app/services/french_recipes_seed.py` 等 ×4 | 薄包装 |
| `backend/scripts/import_*_recipes.py` ×4 | CLI |
| `backend/data/seeds/{french,spanish,italian,american}_recipes_*.json` ×16 | 240 条生产数据 |
| `backend/tests/test_recipe_cuisine.py` | 枚举 + migration 测试更新 |
| `backend/tests/test_import_western_recipes.py` | 四国导入测试 |
| `backend/tests/fixtures/seeds/french_recipes_meat.json` | fixture（2 条） |
| `frontend/src/api.ts` | `CuisineType` / `CUISINE_TYPES` |
| `frontend/src/locale/zh.ts` | `cuisineLabel` |
| `Makefile` | 四条 seed 命令 |
| `README.md` | 文档 |

---

### Task 1: 扩展 `cuisine` 枚举 + migration

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/migrate.py`
- Modify: `backend/tests/test_recipe_cuisine.py`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/locale/zh.ts`

- [ ] **Step 1: 写失败测试 — `italian` 合法、`western` 非法**

在 `test_recipe_cuisine.py` 替换 `test_invalid_cuisine_returns_422`：

```python
def test_invalid_cuisine_returns_422(client):
    response = client.post(
        "/api/recipes",
        json={
            "name": "X",
            "type": "soup",
            "cuisine": "western",
            "description": "",
            "ingredients": ["水"],
        },
    )
    assert response.status_code == 422


def test_italian_cuisine_is_valid(client):
    response = client.post(
        "/api/recipes",
        json={
            "name": "番茄意面",
            "type": "other",
            "cuisine": "italian",
            "description": "",
            "ingredients": ["意面 200g"],
        },
    )
    assert response.status_code == 201
    assert response.json()["cuisine"] == "italian"
```

将 `test_migration_does_not_overwrite_user_cuisine` 中 `cuisine="western"` 改为 `cuisine="korean"`（避免与即将加入的 `western→other` migration 冲突）：

```python
def test_migration_does_not_overwrite_user_cuisine(session: Session):
    session.add(
        Recipe(
            name="番茄炒蛋",
            type="meat",
            description="",
            ingredients=["鸡蛋"],
            cuisine="korean",
        )
    )
    session.commit()
    migrate_db()
    recipe = session.exec(select(Recipe).where(Recipe.name == "番茄炒蛋")).one()
    assert recipe.cuisine == "korean"
```

新增 migration 测试：

```python
def test_migration_converts_western_to_other(session: Session):
    session.add(
        Recipe(
            name="旧西餐",
            type="meat",
            description="",
            ingredients=["牛肉"],
            cuisine="western",
        )
    )
    session.commit()
    migrate_db()
    recipe = session.exec(select(Recipe).where(Recipe.name == "旧西餐")).one()
    assert recipe.cuisine == "other"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest tests/test_recipe_cuisine.py::test_italian_cuisine_is_valid tests/test_recipe_cuisine.py::test_invalid_cuisine_returns_422 tests/test_recipe_cuisine.py::test_migration_converts_western_to_other -v`

Expected: FAIL — `italian` 仍 422；`western` 仍 201；migration 未改 `western`

- [ ] **Step 3: 更新 `schemas.py`**

```python
CUISINE_TYPES = {
    "chinese",
    "japanese",
    "korean",
    "thai",
    "french",
    "spanish",
    "italian",
    "american",
    "other",
}
```

- [ ] **Step 4: 更新 `migrate.py`**

在 `_backfill_recipe_cuisine` 之后、`migrate_db` 的 cuisine 块内增加：

```python
def _migrate_western_to_other(conn) -> None:
    conn.execute(text("UPDATE recipe SET cuisine = 'other' WHERE cuisine = 'western'"))
```

在 `migrate_db()` 中 `_backfill_recipe_cuisine(conn)` 之后调用 `_migrate_western_to_other(conn)`。

- [ ] **Step 5: 更新前端**

`frontend/src/api.ts`：

```typescript
export type CuisineType =
  | "chinese"
  | "japanese"
  | "korean"
  | "thai"
  | "french"
  | "spanish"
  | "italian"
  | "american"
  | "other";

export const CUISINE_TYPES: CuisineType[] = [
  "chinese",
  "japanese",
  "korean",
  "thai",
  "french",
  "spanish",
  "italian",
  "american",
  "other",
];
```

`frontend/src/locale/zh.ts` 的 `CUISINE_LABELS`：

```typescript
const CUISINE_LABELS: Record<string, string> = {
  chinese: "中餐",
  japanese: "日餐",
  korean: "韩餐",
  thai: "泰餐",
  french: "法餐",
  spanish: "西班牙餐",
  italian: "意餐",
  american: "美式",
  other: "其他",
};
```

- [ ] **Step 6: 运行测试**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest tests/test_recipe_cuisine.py -v`

Expected: 全部 PASS

Run: `cd frontend && npm run build`

Expected: 构建成功

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas.py backend/app/migrate.py backend/tests/test_recipe_cuisine.py frontend/src/api.ts frontend/src/locale/zh.ts
git commit -m "feat: extend cuisine enum with french/spanish/italian/american"
```

---

### Task 2: 四个 SeedBundle + wrapper + CLI + Makefile

**Files:**
- Modify: `backend/app/services/recipe_seed.py`
- Create: `backend/app/services/french_recipes_seed.py`
- Create: `backend/app/services/spanish_recipes_seed.py`
- Create: `backend/app/services/italian_recipes_seed.py`
- Create: `backend/app/services/american_recipes_seed.py`
- Create: `backend/scripts/import_french_recipes.py`
- Create: `backend/scripts/import_spanish_recipes.py`
- Create: `backend/scripts/import_italian_recipes.py`
- Create: `backend/scripts/import_american_recipes.py`
- Modify: `Makefile`

- [ ] **Step 1: 写失败测试 — bundle 定义**

创建 `backend/tests/test_import_western_recipes.py` 开头：

```python
from app.services.recipe_seed import (
    AMERICAN_BUNDLE,
    FRENCH_BUNDLE,
    ITALIAN_BUNDLE,
    SPANISH_BUNDLE,
)

WESTERN_COUNTS = {"meat": 25, "veg": 15, "soup": 10, "other": 10}


def test_western_bundle_counts():
    for bundle in (FRENCH_BUNDLE, SPANISH_BUNDLE, ITALIAN_BUNDLE, AMERICAN_BUNDLE):
        assert bundle.expected_counts == WESTERN_COUNTS
        assert bundle.update_on_match == frozenset({"description", "ingredients", "cuisine"})
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest tests/test_import_western_recipes.py::test_western_bundle_counts -v`

Expected: FAIL — `FRENCH_BUNDLE` 未定义

- [ ] **Step 3: 在 `recipe_seed.py` 追加四个 bundle**

```python
_WESTERN_COUNTS = {"meat": 25, "veg": 15, "soup": 10, "other": 10}
_WESTERN_UPDATE = frozenset({"description", "ingredients", "cuisine"})

FRENCH_BUNDLE = SeedBundle(
    name="french",
    seed_files=(
        "french_recipes_meat.json",
        "french_recipes_veg.json",
        "french_recipes_soup.json",
        "french_recipes_other.json",
    ),
    file_type={
        "french_recipes_meat.json": "meat",
        "french_recipes_veg.json": "veg",
        "french_recipes_soup.json": "soup",
        "french_recipes_other.json": "other",
    },
    expected_counts=_WESTERN_COUNTS,
    update_on_match=_WESTERN_UPDATE,
    default_cuisine="french",
)

SPANISH_BUNDLE = SeedBundle(
    name="spanish",
    seed_files=(
        "spanish_recipes_meat.json",
        "spanish_recipes_veg.json",
        "spanish_recipes_soup.json",
        "spanish_recipes_other.json",
    ),
    file_type={
        "spanish_recipes_meat.json": "meat",
        "spanish_recipes_veg.json": "veg",
        "spanish_recipes_soup.json": "soup",
        "spanish_recipes_other.json": "other",
    },
    expected_counts=_WESTERN_COUNTS,
    update_on_match=_WESTERN_UPDATE,
    default_cuisine="spanish",
)

ITALIAN_BUNDLE = SeedBundle(
    name="italian",
    seed_files=(
        "italian_recipes_meat.json",
        "italian_recipes_veg.json",
        "italian_recipes_soup.json",
        "italian_recipes_other.json",
    ),
    file_type={
        "italian_recipes_meat.json": "meat",
        "italian_recipes_veg.json": "veg",
        "italian_recipes_soup.json": "soup",
        "italian_recipes_other.json": "other",
    },
    expected_counts=_WESTERN_COUNTS,
    update_on_match=_WESTERN_UPDATE,
    default_cuisine="italian",
)

AMERICAN_BUNDLE = SeedBundle(
    name="american",
    seed_files=(
        "american_recipes_meat.json",
        "american_recipes_veg.json",
        "american_recipes_soup.json",
        "american_recipes_other.json",
    ),
    file_type={
        "american_recipes_meat.json": "meat",
        "american_recipes_veg.json": "veg",
        "american_recipes_soup.json": "soup",
        "american_recipes_other.json": "other",
    },
    expected_counts=_WESTERN_COUNTS,
    update_on_match=_WESTERN_UPDATE,
    default_cuisine="american",
)
```

- [ ] **Step 4: 四个薄 wrapper（结构相同，以法餐为例）**

`backend/app/services/french_recipes_seed.py`：

```python
from .recipe_seed import FRENCH_BUNDLE, ImportResult, import_recipe_seeds, validate_production_seeds as _validate


def import_french_recipes(session, seeds_path=None) -> ImportResult:
    return import_recipe_seeds(session, FRENCH_BUNDLE, seeds_path)


def validate_production_seeds(seeds_path=None):
    return _validate(FRENCH_BUNDLE, seeds_path)
```

`spanish_recipes_seed.py` / `italian_recipes_seed.py` / `american_recipes_seed.py` 同理，替换 bundle 名与 import 函数名。

- [ ] **Step 5: 四个 CLI（复制 `import_classic_recipes.py`，改 import 函数）**

`import_french_recipes.py` docstring：`"""导入法餐 seed JSON。同名则更新 description、ingredients、cuisine，否则插入。"""`

- [ ] **Step 6: Makefile**

```makefile
.PHONY: ... seed-french-recipes seed-spanish-recipes seed-italian-recipes seed-american-recipes

seed-french-recipes: setup-backend
	cd backend && .venv/bin/python scripts/import_french_recipes.py

seed-spanish-recipes: setup-backend
	cd backend && .venv/bin/python scripts/import_spanish_recipes.py

seed-italian-recipes: setup-backend
	cd backend && .venv/bin/python scripts/import_italian_recipes.py

seed-american-recipes: setup-backend
	cd backend && .venv/bin/python scripts/import_american_recipes.py
```

- [ ] **Step 7: 创建空 JSON 占位**

16 个文件各写 `[]`，验证 CLI：

Run: `make seed-french-recipes`

Expected: `已导入 0 条，更新 0 条，跳过 0 条`

- [ ] **Step 8: 运行 bundle 测试**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest tests/test_import_western_recipes.py::test_western_bundle_counts -v`

Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/recipe_seed.py backend/app/services/*_recipes_seed.py backend/scripts/import_*_recipes.py backend/data/seeds/french_recipes_*.json backend/data/seeds/spanish_recipes_*.json backend/data/seeds/italian_recipes_*.json backend/data/seeds/american_recipes_*.json Makefile backend/tests/test_import_western_recipes.py
git commit -m "feat: add western recipe seed bundles and import commands"
```

---

### Task 3: 导入测试（fixture + upsert + 生产校验）

**Files:**
- Modify: `backend/tests/test_import_western_recipes.py`
- Create: `backend/tests/fixtures/seeds/french_recipes_meat.json`
- Create: `backend/tests/fixtures/seeds/french_recipes_veg.json`（空 `[]`）
- Create: `backend/tests/fixtures/seeds/french_recipes_soup.json`（空）
- Create: `backend/tests/fixtures/seeds/french_recipes_other.json`（空）

- [ ] **Step 1: fixture 两条法餐**

`french_recipes_meat.json`：

```json
[
  {
    "name": "测试油封鸭（Confit de canard）",
    "type": "meat",
    "description": "1. 鸭腿抹盐腌 2 小时。\n2. 鸭油小火浸鸭腿 2 小时至软烂。\n3. 烤箱 200°C 烤皮 10 分钟至酥脆。",
    "ingredients": ["鸭腿 2只", "鸭油 500ml", "盐 适量", "百里香 2枝"]
  },
  {
    "name": "测试红酒炖牛肉（Bœuf bourguignon）",
    "type": "meat",
    "description": "1. 牛肉块拍粉，煎至表面焦黄。\n2. 加入洋葱、胡萝卜、红酒与牛肉高汤。\n3. 小火炖 2 小时至软烂。",
    "ingredients": ["牛腩 500g", "红酒 200ml", "洋葱 1个", "胡萝卜 2根", "牛肉高汤 300ml"]
  }
]
```

其余三个 french fixture 文件写 `[]`（bundle 会 skip 缺失文件 — 注意 `import_recipe_seeds` 对缺失文件是 `continue`，但 `validate_production_seeds` 会报错；fixture 测试只用 import，不用 validate）。

- [ ] **Step 2: 追加测试**

```python
import re
from pathlib import Path

import pytest
from sqlmodel import Session, select

from app.models import Recipe
from app.services.french_recipes_seed import import_french_recipes
from app.services.recipe_seed import FRENCH_BUNDLE, SeedValidationError, load_seed_file

FIXTURES = Path(__file__).parent / "fixtures" / "seeds"
STEP_LINE = re.compile(r"^\d+\. ")
L3_NAME = re.compile(r"^.+（.+）$")


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
```

- [ ] **Step 3: 运行测试**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest tests/test_import_western_recipes.py -v`

Expected: 全部 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_import_western_recipes.py backend/tests/fixtures/seeds/french_recipes_*.json
git commit -m "test: french recipe seed import and upsert"
```

---

### Task 4: 生产 JSON — 法餐 60 道

**Files:**
- Modify: `backend/data/seeds/french_recipes_meat.json`（25）
- Modify: `backend/data/seeds/french_recipes_veg.json`（15）
- Modify: `backend/data/seeds/french_recipes_soup.json`（10）
- Modify: `backend/data/seeds/french_recipes_other.json`（10）

- [ ] **Step 1: 编写 60 道法餐**

规则（与 spec 一致）：
- 菜名 L3：`中文（法文）`，全角括号
- `description`：3–6 步，`\n` 分隔，`1. ` 格式，中文
- `ingredients`：4–8 项中文
- 全局不与现有中/日/其他三国 seed 重名

内容方向示例：
- **meat：** 油封鸭、红酒炖牛肉、法式煎牛排、普罗旺斯炖菜（含肉）、科ordon bleu…
- **veg：** 尼斯沙拉、 ratatouille 普罗旺斯杂菜、法式煎蛋卷（素）、烤时蔬…
- **soup：** 法式洋葱汤、海鲜浓汤、蔬菜浓汤…
- **other：** 可丽饼、法棍配黄油、 quiche 洛林蛋奶派、马卡龙（家庭简版）…

- [ ] **Step 2: 校验**

Run:

```bash
cd backend && .venv/bin/python -c "
from app.services.french_recipes_seed import validate_production_seeds
print(validate_production_seeds())
"
```

Expected: `{'meat': 25, 'veg': 15, 'soup': 10, 'other': 10}`

- [ ] **Step 3: 生产测试（先写测试再跑）**

在 `test_import_western_recipes.py` 追加：

```python
from app.services.french_recipes_seed import validate_production_seeds as validate_french
from app.services.recipe_seed import default_seeds_dir


def test_french_production_seed_files_structure():
    assert validate_french(default_seeds_dir()) == WESTERN_COUNTS


def test_french_production_l3_names_and_steps():
    validate_french()
    for filename in FRENCH_BUNDLE.seed_files:
        for record in load_seed_file(default_seeds_dir() / filename, FRENCH_BUNDLE):
            assert L3_NAME.match(record["name"]), record["name"]
            steps = [ln for ln in record["description"].splitlines() if STEP_LINE.match(ln)]
            assert 3 <= len(steps) <= 6, record["name"]
```

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest tests/test_import_western_recipes.py -k french -v`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/data/seeds/french_recipes_*.json backend/tests/test_import_western_recipes.py
git commit -m "feat: add 60 french recipe seeds"
```

---

### Task 5: 生产 JSON — 西班牙餐 60 道

**Files:**
- `backend/data/seeds/spanish_recipes_*.json` ×4

- [ ] **Step 1: 编写 60 道**

内容方向：海鲜饭、西班牙土豆蛋饼、蒜香虾、Gazpacho、塔帕斯、chorizo 炖菜…

- [ ] **Step 2: 校验 + 测试**

复制 Task 4 的 validate/L3/steps 测试，改用 `SPANISH_BUNDLE` 与 `validate_production_seeds` from `spanish_recipes_seed`。

Run: `pytest tests/test_import_western_recipes.py -k spanish -v`

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: add 60 spanish recipe seeds"
```

---

### Task 6: 生产 JSON — 意餐 60 道

**Files:**
- `backend/data/seeds/italian_recipes_*.json` ×4

- [ ] **Step 1: 编写 60 道**

内容方向：番茄意面、奶油培根面、千层面、米兰烩饭、玛格丽特披萨、意式肉酱…

- [ ] **Step 2: 校验 + 测试**（同 Task 5，换 `ITALIAN_BUNDLE`）

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: add 60 italian recipe seeds"
```

---

### Task 7: 生产 JSON — 美式 60 道

**Files:**
- `backend/data/seeds/american_recipes_*.json` ×4

- [ ] **Step 1: 编写 60 道**

内容方向：经典汉堡、烤肋排、通心粉奶酪、蛤蜊浓汤、烤鸡、布朗尼、苹果派…

- [ ] **Step 2: 校验 + 测试**（同 Task 5，换 `AMERICAN_BUNDLE`）

- [ ] **Step 3: 全局唯一性检查**

Run:

```bash
cd backend && .venv/bin/python -c "
import json
from pathlib import Path
names = []
for p in sorted(Path('data/seeds').glob('*_recipes_*.json')):
    for r in json.loads(p.read_text()):
        names.append(r['name'])
assert len(names) == len(set(names)), 'duplicate names'
print('total', len(names), 'unique ok')
"
```

Expected: `total 600 unique ok`（240 中 + 120 日 + 240 西，若仅测西餐则改 glob 为 `french_*` 等四国）

更精确：

```bash
cd backend && .venv/bin/python -c "
import json
from pathlib import Path
patterns = ['classic_recipes_*.json','japanese_recipes_*.json','french_recipes_*.json','spanish_recipes_*.json','italian_recipes_*.json','american_recipes_*.json']
names = []
for pat in patterns:
    for p in Path('data/seeds').glob(pat):
        for r in json.loads(p.read_text()):
            names.append(r['name'])
dups = [n for n in set(names) if names.count(n) > 1]
assert not dups, dups
print(len(names), 'recipes, all unique')
"
```

Expected: `600 recipes, all unique`

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add 60 american recipe seeds"
```

---

### Task 8: 全量回归 + 文档

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-24-western-recipes-seed-design.md`（状态 → 已完成，链到本 plan）

- [ ] **Step 1: 全量测试**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest -v`

Expected: 全部 PASS（约 94+ 条）

Run: `cd frontend && npm run build && npm test`

Expected: 构建与测试通过

- [ ] **Step 2: 手动验收**

```bash
make seed-french-recipes    # 第一次 +60
make seed-french-recipes    # 第二次 updated=60
make seed-spanish-recipes
make seed-italian-recipes
make seed-american-recipes
```

- [ ] **Step 3: README 与 spec 状态**

README 增加一节「Seed Western recipes (optional)」，包含四条 make 命令说明，并注明同名 upsert 行为。

- [ ] **Step 4: Commit**

```bash
git commit -m "docs: add western recipe seed commands to README"
```

---

## 验收清单

- [ ] `CUISINE_TYPES` 含 `french` / `spanish` / `italian` / `american`，无 `western`
- [ ] 16 个 JSON 文件共 240 条，配额正确
- [ ] 四条 `make seed-*-recipes` 可导入且 upsert 正常
- [ ] 前端可筛选法/ 西/ 意/ 美
- [ ] DB 中旧 `western` 已变为 `other`
- [ ] README 文档四条命令
- [ ] 全量测试通过

## 风险

| 风险 |  缓解 |
|------|------|
| 与中餐/ 日餐/ 其他三国 seed 菜名冲突 | 全局唯一检查；L3 原文降低碰撞 |
| 16 文件维护 | 分国提交、分国命令 |
| 用户习惯「西餐」筛选 | UI 四国并列；`other` 兜底 |

---

## Spec 对照（自检）

| Spec 要求 | Plan 任务 |
|---|---|
| 扩展 `cuisine` 枚举 | Task 1 |
| 240 道 | Task 4–7 |
| Migration `western`→`other` | Task 1 |
| 4 条独立导入命令 + upsert | Task 2 |
| 16 个 JSON | Task 4–7 |
| 前端筛选 | Task 1 |
| 测试 | Task 1、3、4–7、8 |
| README | Task 8 |

---

## 执行方式

**Plan complete and saved to `docs/superpowers/plans/2026-05-24-western-recipes-seed.md`.**

**两种执行路径：**

1. **Subagent-Driven（推荐）** — 按 Task 分派 subagent，Task 间 review
2. **Inline Execution** — 当前 session 按 executing-plans 逐步执行

**请选择执行方式，或指示开始 Task 1。**
