# 食谱菜系字段（cuisine）

**日期：** 2026-05-24  
**状态：** 已完成  
**实现计划：** [2026-05-24-recipe-cuisine.md](../plans/2026-05-24-recipe-cuisine.md)

为 `Recipe` 增加可选 **菜系** 维度（中餐、日餐、韩餐、泰餐、西餐、其他），与现有 **荤/素/汤/other**（`type`）并列，供列表筛选与展示；**不改变** AI 配餐选菜逻辑。

## 已确认决策

| 项 | 选择 |
|---|---|
| 枚举（L0） | `chinese` 中餐、`japanese` 日餐、`korean` 韩餐、`thai` 泰餐、`western` 西餐、`other` 其他 |
| 存储 | 可空列 `Recipe.cuisine`；`NULL` = 未分类 |
| 必填 | **D3 可选**；表单可选；UI 空值显示「未分类」 |
| AI 配餐 | **A1** 仍按 meat/veg/soup 全库选，不按菜系过滤 |
| 现有数据 | **M1** migration 按 seed JSON 菜名精确匹配回填 |
| Seed 导入 | `SeedBundle.default_cuisine`；中餐/日餐 upsert 含 `cuisine` |
| 架构 | 方案 1：`cuisine` 可选字符串 + 枚举校验 |

## 非目标

- AI 菜系偏好、一餐多菜系规则
- 子菜系（粤菜、川菜等）
- 多标签 `cuisines[]`
- 独立 `Cuisine` 表
- 修改 `type` 字段语义

## 数据模型

```python
# backend/app/models.py — Recipe
cuisine: str | None = Field(default=None, index=True)
```

```python
# backend/app/schemas.py
CUISINE_TYPES = {"chinese", "japanese", "korean", "thai", "western", "other"}
```

**API 规则：**

- `RecipeCreate` / `RecipeUpdate` / `RecipeRead` 含 `cuisine: str | None = None`
- 请求体传 `""` 或 `null` → 存 `None`
- 非空值必须在 `CUISINE_TYPES` 内，否则 422

## Migration（M1）

在 `backend/app/migrate.py` 增加步骤（幂等）：

1. 若 `recipe` 表无 `cuisine` 列 → `ALTER TABLE recipe ADD COLUMN cuisine TEXT`
2. 创建索引（若 ORM `index=True` 未自动建）
3. 从 `backend/data/seeds/classic_recipes_*.json` 收集全部 `name` → `UPDATE recipe SET cuisine='chinese' WHERE name IN (...)`
4. 从 `japanese_recipes_*.json` 收集全部 `name` → `UPDATE ... cuisine='japanese' WHERE name IN (...)`
5. **不**覆盖已有非空 `cuisine`（若用户已手动设置）

仅在 `cuisine IS NULL` 时写入。

## Seed 导入

`SeedBundle` 扩展：

```python
default_cuisine: str | None = None
```

| Bundle | `default_cuisine` | `update_on_match` 增加 |
|--------|-------------------|------------------------|
| CLASSIC | `chinese` | `cuisine` |
| JAPANESE | `japanese` | `cuisine` |

插入新食谱时：`recipe.cuisine = bundle.default_cuisine`  
Upsert 时：若 `cuisine` 在 `update_on_match` 中，从 seed 记录或 bundle 默认值更新。

Seed JSON **不必**含 `cuisine` 字段（由 bundle 注入）。

## 前端

| 位置 | 改动 |
|------|------|
| `api.ts` | `CuisineType`、`Recipe.cuisine` |
| `locale/zh.ts` | `cuisineLabel()`：未分类 + 6 菜系 |
| `RecipeFormPage` | 可选下拉（首项「未分类」） |
| `RecipesPage` | 菜系筛选；列表副标题显示菜系 |
| `RecipePicker` | 可选副标题菜系 |
| `MealSlotModal` | 计划内条目可选显示菜系 |

移动优先：筛选项 44px 触控；未分类不占过多视觉权重。

## 测试

**Backend：**

- migration 回填：预置「番茄炒蛋」→ migration 后 `cuisine=chinese`
- API create/update with/without cuisine；非法值 422
- seed import 新条目带 `default_cuisine`；upsert 更新 cuisine
- 已有用户手设 cuisine 不被 migration 覆盖

**Frontend（可选 Vitest）：**

- `cuisineLabel(null)` → 「未分类」

## 验收标准

- [ ] `recipe.cuisine` 列存在且可空
- [ ] 360 道 seed 同名记录在 migration 后为中/日餐
- [ ] 表单可选菜系；列表可筛选
- [ ] AI fill/regenerate 行为不变（无菜系参数）
- [ ] `pytest` + `npm test` + `npm run build` 通过

## 风险

| 风险 | 缓解 |
|------|------|
| 与 `type` 混淆 | UI/API 命名 `cuisine` vs `type`；中文「菜系」vs「类型」 |
| 跨菜系同名 | 去重仍按 `name`；migration 按 seed 文件顺序（日餐后写会覆盖？） | 

**Migration 顺序：** 先 `chinese` 后 `japanese`；同名极少，若冲突日餐覆盖（文档注明）。
