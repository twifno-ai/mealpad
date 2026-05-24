# 食谱菜系字段 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** 为 Recipe 增加可选 `cuisine`（6 枚举 + 未分类），migration 回填 seed，前端筛选/表单，AI 逻辑不变。

**Spec:** [docs/superpowers/specs/2026-05-24-recipe-cuisine-design.md](../specs/2026-05-24-recipe-cuisine-design.md)

---

### Task 1: 模型、Schema、Migration

**Files:** `models.py`, `schemas.py`, `migrate.py`, `routers/recipes.py`, `tests/test_recipe_cuisine.py`

- [ ] `Recipe.cuisine: str | None`, index
- [ ] `CUISINE_TYPES`, schemas 加字段；router 校验
- [ ] `migrate.py`：ADD COLUMN + 从 seed JSON 名回填（仅 NULL）
- [ ] pytest：migration、API 422/OK

### Task 2: Seed 导入

**Files:** `recipe_seed.py`, `tests/test_import_*_recipes.py`

- [ ] `SeedBundle.default_cuisine`
- [ ] CLASSIC=`chinese`, JAPANESE=`japanese`
- [ ] `update_on_match` 含 `cuisine`；insert 写 default
- [ ] 测试 import/upsert 写入 cuisine

### Task 3: 前端

**Files:** `api.ts`, `locale/zh.ts`, `RecipeFormPage.tsx`, `RecipesPage.tsx`, `RecipePicker.tsx`, `MealSlotModal.tsx`

- [ ] 类型与 `cuisineLabel`
- [ ] 表单下拉（未分类）
- [ ] 列表筛选 + 副标题
- [ ] Picker/Modal 可选显示

### Task 4: 验证与文档

- [ ] `pytest` + `npm test` + `npm run build`
- [ ] README 一句；spec 状态已完成
- [ ] 本地启动确认 migration 后 seed 食谱显示菜系

---

## 验收

- [ ] 360 seed 回填正确
- [ ] 手动食谱可为未分类
- [ ] AI fill 无回归
