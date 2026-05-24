# 膳食计划重新生成 — 设计说明

**日期：** 2026-05-24  
**状态：** 已批准，待实现  

## 目标

在现有「AI 自动填充空槽」之外，支持**整周重新生成膳食计划**：清空该周所有餐次，由 AI 重新安排；若该周已有购物清单，一并删除。

## 已确认决策

| 项 | 选择 |
|---|---|
| 重算范围 | 整周全部重算（清空后 AI 重新安排所有 lunch/dinner 槽位） |
| 手动选择 | 不保留；重新生成覆盖全部已有安排 |
| 购物清单 | 自动删除该 `(start_date, end_date)` 对应的购物清单及全部条目 |
| API 形态 | 新增专用端点 `POST /api/meal-plan/regenerate`（不修改现有 generate 语义） |
| 日期范围 | 与周视图一致，由前端传入当前周的 `start`（周一）与 `end`（周日） |

## 非目标

- 不重算部分日期（如仅周三–周五）
- 不区分「AI 填的」与「手动选的」槽位
- 不自动重新生成购物清单（用户需手动点「生成购物清单」）
- 不做撤销/历史版本

## 架构

```
MealPlanPage
  ├─ 「AI 自动填充空槽」→ POST /api/meal-plan/generate（不变）
  └─ 「重新生成计划」    → POST /api/meal-plan/regenerate（新增）

meal_plan router
  regenerate_meal_plan()
    1. generate_plan(all_slots, recipes)   # 先 AI，失败则不碰 DB
    2. validate assignments; if applied==0 → 502
    3. DELETE MealPlanEntry + ShoppingList in range
    4. INSERT assignments → commit
```

与购物清单「重新生成清单」对称：专用端点、确认对话框、破坏性操作。

## API

### `POST /api/meal-plan/regenerate`

**Request body：** 与现有 `DateRange` 相同

```json
{ "start": "2026-05-19", "end": "2026-05-25" }
```

**Response：** `200` + `MealPlanEntry[]`（该范围内完整计划，与 `GET /api/meal-plan` 一致）

**行为（单数据库事务，AI 先于删库）：**

1. 校验 `start <= end`
2. 若无任何食谱 → `422`，detail：`请先添加至少一个食谱，再进行 AI 填充`
3. 计算范围内全部 `(date, slot)`（`lunch` + `dinner` × 天数）
4. **先**调用 `generate_plan(all_slots, recipe_dicts)`；若 AI 失败 → `502`，**不修改数据库**
5. 校验 assignments（规则与现有 generate 相同）；统计 `applied`；若 `applied == 0` → `502`，**不修改数据库**
6. **再**在同一事务内：删除 `start..end` 内全部 `MealPlanEntry`；删除匹配的 `ShoppingList`（条目级联删除）；写入新 assignments
7. `commit`，返回该范围条目列表

**错误：**

| 条件 | HTTP | detail（中文） |
|---|---|---|
| 无食谱 | 422 | 请先添加至少一个食谱，再进行 AI 填充 |
| AI 未配置 / API 失败 | 502 | 沿用 `AIServiceError` / `format_llm_api_error` |
| AI 返回无有效 assignment | 502 | AI 未返回有效的膳食安排… |

### `POST /api/meal-plan/generate`

**不变。** 仍只填充当前为空 `(date, slot)` 的槽位，不删除已有条目，不触碰购物清单。

## 前端

### 文件

- `frontend/src/api.ts` — 新增 `regenerateMealPlan(start, end)`
- `frontend/src/locale/zh.ts` — 新增文案
- `frontend/src/pages/MealPlanPage.tsx` — 按钮、确认、调用、刷新 `hasList`

### UI

| 按钮 | 显示条件 | 行为 |
|---|---|---|
| AI 自动填充空槽 | `emptySlots > 0` | 现有逻辑 |
| 重新生成计划 | 本周 `entries.length > 0` | `confirm()` → regenerate API |

两按钮可同时显示（部分已填、部分空槽）。

**确认文案：**

> 重新生成本周膳食计划？所有餐次将被 AI 重新安排，该周购物清单将被删除。

**成功后：**

- 刷新计划列表（`load()`）
- `setHasList(false)`，主按钮恢复为「生成购物清单」
- 错误展示沿用 `getErrorMessage(e, fallback)`

### 文案键（`zh.mealPlan`）

| key | 文案 |
|---|---|
| `regenerate` | 重新生成计划 |
| `regenerating` | 重新生成中… |
| `regenerateConfirm` | 重新生成本周膳食计划？所有餐次将被 AI 重新安排，该周购物清单将被删除。 |
| `regenerateFailed` | 重新生成计划失败 |

## 测试

### 后端（TDD）

文件：`backend/tests/test_meal_plan_regenerate.py`

1. **happy path：** 创建食谱 + 2 个计划条目 + 购物清单 → regenerate → 条目数 = 天数×2（mock AI），购物清单 GET 404
2. **无食谱：** 422
3. **AI 返回空：** 502，且**原有条目与购物清单保持不变**（AI 先于删库）
4. **generate 不变：** 现有 `test_ai_generate.py` 全部仍绿

### 前端

- 可选：Vitest 测 `zh` 键存在；主要依赖手动 Verify

## Verify（手动）

1. 计划一周并生成购物清单
2. 点「重新生成计划」→ 确认 → 餐次全部更新，「生成购物清单」按钮恢复
3. 进入购物清单路由 → 404 或需重新生成
4. 「AI 自动填充空槽」对空周仍正常工作

## 与现有约定的一致性

- AI 调用仍走 `app.services.ai.generate_plan`，server-side only
- 不引入 auth
- 移动端：按钮 min 44px tap target（沿用现有 `.btn`）
- 中文 UI
