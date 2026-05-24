# 每餐多道菜 — 设计说明

**日期：** 2026-05-23  
**状态：** 已批准，待实现  

## 目标

支持每个餐次（午餐/晚餐）安排**多道菜**。AI 自动填充时每餐固定 **3 道**（1 荤 + 1 素 + 1 汤）；用户可**按单道菜**删除、替换或追加（含第 4 道及以后）。

## 已确认决策

| 项 | 选择 |
|---|---|
| AI 每餐道数 | 固定 3 道 |
| AI 搭配规则 | 1 × `meat` + 1 × `veg` + 1 × `soup`（按食谱 `type`） |
| 手动编辑粒度 | 单道菜：可删/换任意一道，可追加第 4 道 |
| 数据模型 | 放宽 `MealPlanEntry`，同一 `(date, slot)` 允许多行（方案 1） |
| fill 空槽 | 仅对 **0 道菜** 的餐次生成 3 道；已有 1–2 道不自动补 |
| regenerate | 整周重算，每餐重新写入 3 道；删除该周购物清单（沿用现有 regenerate） |

## 非目标

- 可配置每餐道数（`.env` / UI 设置）
- AI 自动补满已有 1–2 道的餐次
- 每餐手动添加上限（第 4 道及以后不限）
- 按「整餐」一次性替换 3 道（UI 以单道操作为主；regenerate 除外）

## 数据模型

### `MealPlanEntry` 变更

```text
MealPlanEntry
  id            PK
  date          index
  slot          lunch | dinner
  recipe_id     FK → recipe.id (CASCADE)
  sort_order    int, default 0   # 同餐内展示顺序
  created_at
```

**约束变更：**

- **移除** `UNIQUE(date, slot)`
- **新增** `UNIQUE(date, slot, recipe_id)` — 同一餐不重复同一食谱

### 迁移

1. SQLite migration：删旧 unique、加新 unique、加 `sort_order` 列（默认 0）
2. 现有数据：每条旧 entry 保留为对应餐次的 1 道菜，不自动补成 3 道

## API

### 保留

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/meal-plan?start=&end=` | 返回 entry 列表（每道菜一行），按 `date, slot, sort_order` 排序 |

### 新增 / 变更

| 方法 | 路径 | Body | 说明 |
|---|---|---|---|
| POST | `/api/meal-plan/{date}/{slot}/items` | `{ recipe_id }` | 追加一道；校验 slot、recipe 存在；重复 `(date,slot,recipe_id)` → 422 |
| PUT | `/api/meal-plan/items/{entry_id}` | `{ recipe_id }` | 替换该 entry 的食谱 |
| DELETE | `/api/meal-plan/items/{entry_id}` | — | 删除单道菜 |
| DELETE | `/api/meal-plan/{date}/{slot}` | — | 清空该餐全部 entry（保留） |

### 废弃

- `PUT /api/meal-plan/{date}/{slot}` — 移除或改为 410；前端改调新 API

### `POST /api/meal-plan/generate`（fill 空餐次）

- **空餐次** = 该 `(date, slot)` 下 **0 条** entry
- 对每个空餐次，AI 返回 3 道 → 写入 3 条 entry
- 食谱库缺 `meat` / `veg` / `soup` 任一类型 → `422`，detail 中文说明缺哪种类型
- AI 失败 → `502`，不修改 DB

### `POST /api/meal-plan/regenerate`

- 行为不变（先 AI 后删库），但每餐写入 **3 条** entry
- 删购物清单逻辑不变

## AI

### Tool schema（`assign_meals`）

每餐一次 assignment，内含 3 道菜：

```json
{
  "assignments": [
    {
      "date": "2026-05-12",
      "slot": "lunch",
      "dishes": [
        { "recipe_id": 1, "type": "meat" },
        { "recipe_id": 2, "type": "veg" },
        { "recipe_id": 3, "type": "soup" }
      ]
    }
  ]
}
```

`dishes` 必填且长度必须为 3；`type` 必须为 `meat` | `veg` | `soup`；`recipe_id` 须存在于库中且与声明的 `type` 一致。

### System prompt 要点

- 每个 `(date, slot)` 输出 exactly 3 dishes：meat + veg + soup 各一
- 仅使用提供的 recipe_id；7 天内尽量不重复；连续餐次多样化
- Anthropic / OpenAI 两 provider 共用 `providers/base.py` schema

### 服务端校验

1. `dishes` 长度 = 3
2. types 集合 = `{meat, veg, soup}`
3. 每个 `recipe_id` 存在且 `recipe.type` 匹配
4. 写入时按 meat → veg → soup 顺序设 `sort_order`（0, 1, 2）

## 前端

### 文件

- `frontend/src/api.ts` — 新 API 方法；更新 `MealPlanEntry` 消费方式
- `frontend/src/pages/MealPlanPage.tsx` — 按 `(date, slot)` 分组展示；餐次详情 modal
- `frontend/src/components/RecipePicker.tsx` — `mode: "add" | "replace"`，`entryId?`
- `frontend/src/locale/zh.ts` — 新文案

### UI

**周视图槽位行：**

- 0 道：「+ 添加」
- 1+ 道：显示菜名列表（「 · 」分隔或换行），点击打开餐次详情

**餐次详情 modal：**

- 列出该餐每道菜（类型标签可选：荤/素/汤）
- 每行：菜名 +「更换」+「删除」
- 底部：「+ 添加菜品」
- 可关闭返回周视图

**工具栏：**

- 「AI 自动填充空餐次」（原「空槽」文案更新）
- 「重新生成计划」逻辑不变

### 文案（`zh.mealPlan` 等）

| key | 文案 |
|---|---|
| `autoFill` | AI 自动填充空餐次 |
| `mealDetail` | 本餐菜单 |
| `addDish` | 添加菜品 |
| `replaceDish` | 更换 |
| `removeDish` | 删除 |
| `emptyMeal` | 尚未安排菜品 |

## 购物清单

无业务逻辑变更：`generate_shopping_list` 遍历范围内全部 `MealPlanEntry`，汇总所有 `recipe.ingredients`。

## 错误处理

| 场景 | HTTP | detail（中文） |
|---|---|---|
| 食谱库无 meat/veg/soup | 422 | 缺少荤菜/素菜/汤类食谱，无法生成完整一餐 |
| 追加重复食谱到同一餐 | 422 | 该餐已包含此食谱 |
| entry_id 不存在 | 404 | 未找到 |
| AI 无效输出 | 502 | 沿用现有文案 |

## 测试

### 后端（TDD）

文件：`backend/tests/test_meal_plan_items.py`、`backend/tests/test_meal_plan_multi_dish.py`

1. POST items 追加；同餐 3 条 entry 共存
2. POST 重复 recipe_id → 422
3. PUT / DELETE 单条 entry 不影响同餐其他菜
4. DELETE `/{date}/{slot}` 清空整餐
5. generate 空餐次 → 3 条/餐（mock AI）
6. generate 缺 soup 类型 → 422
7. regenerate → 天数×2×3 条 entry
8. 更新 `test_ai_generate.py`、`test_meal_plan_regenerate.py`

### 前端

- Vitest：`zh` 新 key 存在
- 手动：375×667 下 modal 可点、多菜展示正常

## Verify（手动）

1. 旧数据（每餐 1 道）打开仍正常显示
2. 点某一餐 → 可再加第 2、3、4 道
3. AI 填充空餐次 → 一次出现 3 道（荤素汤）
4. 重新生成计划 → 每餐 3 道，购物清单被删
5. 生成购物清单 → 含所有餐次全部食材

## 与现有约定的一致性

- 膳食计划仍按 `(date, slot)` 查询，无 `MealPlan` 容器实体
- AI server-side only；tool use + 强制 schema
- 中文 UI；mobile-first tap targets
- regenerate 仍先 AI 后删库
