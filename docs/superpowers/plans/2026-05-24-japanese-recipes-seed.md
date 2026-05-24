# 经典日餐食谱种子数据 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 追加 **120 道** 日餐 seed（50/30/20/20），独立 `make seed-japanese-recipes`，复用通用导入逻辑，按完整菜名去重。

**Architecture:** 将 `classic_recipes_seed.py` 重构为 `recipe_seed.py`（`SeedBundle` + `import_recipe_seeds`）；中餐 wrapper 不变；新增 `japanese_recipes_*.json` 与日餐 CLI。

**Tech Stack:** Python 3.11+、SQLModel、pytest。

**Spec:** [docs/superpowers/specs/2026-05-24-japanese-recipes-seed-design.md](../specs/2026-05-24-japanese-recipes-seed-design.md)

---

## File map

| File | Responsibility |
|---|---|
| `backend/app/services/recipe_seed.py` | 通用 SeedBundle、导入、校验 |
| `backend/app/services/classic_recipes_seed.py` | 薄包装 → CLASSIC_BUNDLE |
| `backend/app/services/japanese_recipes_seed.py` | 薄包装 → JAPANESE_BUNDLE |
| `backend/scripts/import_japanese_recipes.py` | 日餐 CLI |
| `backend/data/seeds/japanese_recipes_*.json` | 120 条生产数据 |
| `backend/tests/test_import_japanese_recipes.py` | 日餐测试 |
| `backend/tests/test_import_classic_recipes.py` | 确保重构后仍通过 |
| `Makefile` | `seed-japanese-recipes` |
| `README.md` | 文档 |

---

### Task 1: 重构为通用 `recipe_seed.py`

**Files:**
- Create: `backend/app/services/recipe_seed.py`
- Modify: `backend/app/services/classic_recipes_seed.py`

- [ ] **Step 1: 写失败测试 — wrapper 仍导出相同符号**

在 `test_import_classic_recipes.py` 顶部增加：

```python
from app.services.classic_recipes_seed import CLASSIC_BUNDLE, default_seeds_dir
from app.services.recipe_seed import SeedBundle

def test_classic_bundle_counts():
    assert CLASSIC_BUNDLE.expected_counts == {"meat": 100, "veg": 60, "soup": 40, "other": 40}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest tests/test_import_classic_recipes.py::test_classic_bundle_counts -v`

Expected: FAIL — `CLASSIC_BUNDLE` 未定义

- [ ] **Step 3: 实现 `recipe_seed.py`**

将现有 `classic_recipes_seed.py` 逻辑迁移到 `recipe_seed.py`：

```python
@dataclass(frozen=True)
class SeedBundle:
    name: str
    seed_files: tuple[str, ...]
    file_type: dict[str, str]
    expected_counts: dict[str, int]

CLASSIC_BUNDLE = SeedBundle(
    name="classic",
    seed_files=(
        "classic_recipes_meat.json",
        "classic_recipes_veg.json",
        "classic_recipes_soup.json",
        "classic_recipes_other.json",
    ),
    file_type={...},
    expected_counts={"meat": 100, "veg": 60, "soup": 40, "other": 40},
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
)

def import_recipe_seeds(session, bundle: SeedBundle, seeds_path=None) -> ImportResult: ...
def validate_production_seeds(bundle: SeedBundle, seeds_path=None) -> dict[str, int]: ...
def default_seeds_dir() -> Path: ...  # 不变
```

- [ ] **Step 4: 瘦身 `classic_recipes_seed.py`**

```python
from .recipe_seed import CLASSIC_BUNDLE, ImportResult, SeedValidationError, default_seeds_dir, import_recipe_seeds, load_seed_file, validate_production_seeds as _validate

def import_classic_recipes(session, seeds_path=None) -> ImportResult:
    return import_recipe_seeds(session, CLASSIC_BUNDLE, seeds_path)

def validate_production_seeds(seeds_path=None):
    return _validate(CLASSIC_BUNDLE, seeds_path)
```

- [ ] **Step 5: 运行全部现有 import 测试**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest tests/test_import_classic_recipes.py -v`

Expected: 全部 PASS

---

### Task 2: 日餐 wrapper、CLI、Makefile

**Files:**
- Create: `backend/app/services/japanese_recipes_seed.py`
- Create: `backend/scripts/import_japanese_recipes.py`
- Modify: `Makefile`

- [ ] **Step 1: `japanese_recipes_seed.py`**

```python
from .recipe_seed import JAPANESE_BUNDLE, ImportResult, import_recipe_seeds, validate_production_seeds as _validate

def import_japanese_recipes(session, seeds_path=None) -> ImportResult:
    return import_recipe_seeds(session, JAPANESE_BUNDLE, seeds_path)

def validate_production_seeds(seeds_path=None):
    return _validate(JAPANESE_BUNDLE, seeds_path)
```

- [ ] **Step 2: CLI 脚本**（结构同 `import_classic_recipes.py`，调用 `import_japanese_recipes`）

- [ ] **Step 3: Makefile**

```makefile
seed-japanese-recipes: setup-backend
	cd backend && .venv/bin/python scripts/import_japanese_recipes.py
```

- [ ] **Step 4: 创建空 JSON 占位并验证 CLI 可运行**

四个 `japanese_recipes_*.json` 写 `[]`，`make seed-japanese-recipes` 应输出 imported=0。

---

### Task 3: 日餐 seed JSON（120 道）

**Files:**
- Create: `backend/data/seeds/japanese_recipes_meat.json`（50）
- Create: `backend/data/seeds/japanese_recipes_veg.json`（30）
- Create: `backend/data/seeds/japanese_recipes_soup.json`（20）
- Create: `backend/data/seeds/japanese_recipes_other.json`（20）

按 spec 附录逐条编写；L3 菜名；ingredients 中文；**description 为 3–6 步编号制作步骤**（`\n` 分隔，每行 `1. ` 格式）。

示例见 spec「数据文件」节。

校验：

```bash
cd backend && .venv/bin/python -c "
from app.services.japanese_recipes_seed import validate_production_seeds
print(validate_production_seeds())
"
```

Expected: `{'meat': 50, 'veg': 30, 'soup': 20, 'other': 20}`

---

### Task 4: 日餐测试

**Files:**
- Create: `backend/tests/test_import_japanese_recipes.py`
- Create: `backend/tests/fixtures/seeds/japanese_recipes_meat.json`（2 条测试用）

测试项：
- fixture 导入 2 条
- DB 同名 skip
- 批内重复 skip
- 幂等
- `validate_production_seeds` → 50/30/20/20
- 空库生产导入 +120
- L3：`re.search(r"^.+（.+）$", name)` 对全部 120 条为真
- 步骤：每条 `description` 至少 3 行以 `^\d+\. ` 开头

```python
import re

STEP_LINE = re.compile(r"^\d+\. ")

def test_production_descriptions_have_steps():
    from app.services.japanese_recipes_seed import validate_production_seeds, default_seeds_dir
    from app.services.recipe_seed import JAPANESE_BUNDLE, load_seed_file
    validate_production_seeds()
    for filename in JAPANESE_BUNDLE.seed_files:
        for record in load_seed_file(default_seeds_dir() / filename):
            steps = [ln for ln in record["description"].splitlines() if STEP_LINE.match(ln)]
            assert len(steps) >= 3, record["name"]
```

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest -v`

Expected: 全部 PASS（含原中餐测试）

---

### Task 5: 文档

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-24-japanese-recipes-seed-design.md`（状态 → 已完成，链到本 plan）

README 增加：

```markdown
### Seed Japanese recipes (optional)

```bash
make seed-japanese-recipes
```

Adds ~120 home-style Japanese recipes. Same-name entries are skipped.
```

手动验收：

```bash
make seed-japanese-recipes   # 第一次 +120
make seed-japanese-recipes   # 第二次 imported=0
```

---

## 验收清单

- [ ] 120 条日餐 JSON，配额 50/30/20/20
- [ ] 120 个 L3 菜名全局唯一
- [ ] 120 条 `description` 均含 3–6 步编号步骤
- [ ] 重构后中餐 seed 行为与测试不变
- [ ] `make seed-japanese-recipes` 去重幂等
- [ ] pytest 全过
