# Mealpad v2 — 实际制作记录与图片上传

**日期：** 2026-05-23  
**状态：** 已完成  
**实现计划：** [PLAN-v2.md](../../PLAN-v2.md)

## 目标

在 v1 膳食计划与食谱库之上，增加：

1. **记录当天（或任意计划周内日期）实际制作的菜** — 基于计划标记，计划外从食谱库追加。
2. **实际菜的实拍图** — 每道实际记录最多 1 张。
3. **食谱封面图** — v2 每食谱 1 张，数据模型预留多图扩展。

另增 **饮食记录页**，按日浏览历史实拍。

## 已确认决策

| 项 | 选择 |
|---|---|
| 实际 vs 计划 | **基于计划标记** — 在计划餐次里标记「做了」；计划外单独记 |
| 计划外来源 | **从食谱库选**（A1） |
| 计划外餐次 | **仅午餐/晚餐**（S1）；UI 区分「计划内 / 额外」 |
| 标记日期范围 | **周视图内任意日期**（D2） |
| 食谱图 | **v2 每食谱 1 张封面**（R3）；`RecipeImage` 表预留多图 |
| 实拍图 | **每道实际记录最多 1 张**（P1） |
| 图片存储 | **服务器本地磁盘**（F1）；DB 存相对路径 |
| 浏览入口 | **周计划页标记 + 独立饮食记录页**（V2） |
| 架构方案 | **独立 `CookedDishLog` 表**（与 `MealPlanEntry` 分离） |

## 非目标（v2）

- 食谱多图 UI、步骤图
- 独立「加餐」槽位（`snack`）
- 云存储 / CDN / 外网图床
- AI 识图、从照片生成食谱
- 营养分析、社交分享
- 强制上传图片才能标记「做了」（图片始终可选）

## 数据模型

### `CookedDishLog`（新表）

```text
CookedDishLog
  id                    PK
  date                  date, index
  slot                  lunch | dinner
  recipe_id             FK → recipe.id, nullable, ON DELETE SET NULL
  recipe_name           str              # 写入时快照，删食谱后日记仍可显示
  kind                  planned | extra
  meal_plan_entry_id    FK → mealplanentry.id, nullable, ON DELETE SET NULL, unique when not null
  photo_path            str, nullable    # 相对 backend/data/uploads/
  logged_at             datetime
```

**语义：**

- **planned：** 对应计划里某条 `MealPlanEntry`；同一 `meal_plan_entry_id` 只能有一条 log。
- **extra：** 计划外追加；`(date, slot, recipe_id)` 唯一（同一餐不重复同一食谱）。
- 写入时复制当前 `recipe.name` → `recipe_name`。
- **regenerate** 或手动删除计划 entry → `meal_plan_entry_id` SET NULL，log **保留**（历史不丢）；`kind` 仍为 `planned`。

### `RecipeImage`（新表，R3 预留）

```text
RecipeImage
  id            PK
  recipe_id     FK → recipe.id, ON DELETE CASCADE
  file_path     str
  sort_order    int, default 0
  is_cover      bool, default false
  created_at    datetime
```

**v2 规则：** 每 `recipe_id` 最多 1 行 `is_cover=true`。后续多图：加行、调 `sort_order`，无需改表。

### 文件存储

```text
backend/data/uploads/
  recipes/{recipe_id}/{uuid}.{ext}
  cooked/{log_id}/{uuid}.{ext}
```

- 整个 `backend/data/` gitignore（已有 DB；新增 uploads）。
- 备份 = 拷贝 `backend/data/`（SQLite + uploads）。
- 上传约束：JPEG / PNG / WebP；单张 ≤ 5MB；服务端可选缩略（宽 max 1200px，v2 推荐实现以省手机流量）。
- 替换/删除封面或 log 实拍时，删除磁盘上的旧文件。

## API

### 饮食记录 `/api/cooked-dishes`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/cooked-dishes?start=&end=` | 日期范围内全部 log（含 `recipe_name`、`photo_url`、`kind`） |
| POST | `/api/cooked-dishes/planned/{entry_id}` | 标记计划内某道菜；`multipart/form-data`，可选字段 `photo` |
| POST | `/api/cooked-dishes/extra` | 计划外追加；`multipart`：`date`、`slot`、`recipe_id` + 可选 `photo` |
| PUT | `/api/cooked-dishes/{log_id}/photo` | 补传/替换实拍（仍最多 1 张） |
| DELETE | `/api/cooked-dishes/{log_id}/photo` | 删实拍，保留 log |
| DELETE | `/api/cooked-dishes/{log_id}` | 取消标记；删 log + 磁盘图片 |

**校验与错误（中文 `detail`）：**

| 场景 | HTTP |
|---|---|
| entry 不存在 | 404 |
| entry 已有 log | 409 |
| extra 重复 `(date, slot, recipe_id)` | 422 |
| 非法 MIME / 超大文件 | 400 / 413 |
| 磁盘写入失败 | 502 |

### 食谱封面 `/api/recipes/{id}/cover`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/recipes/{id}/cover` | 上传/替换封面（`multipart` `photo`） |
| DELETE | `/api/recipes/{id}/cover` | 删封面及文件 |

**响应扩展：** `RecipeRead`、`RecipeSummary` 增加 `cover_url: str | null`（由 `is_cover` 行拼 `/uploads/...`）。

### 周计划 GET

**不改动** `GET /api/meal-plan` 结构。前端并行请求 `cooked-dishes` 后在本地 merge。

### 静态文件

```python
app.mount("/uploads", StaticFiles(directory=UPLOAD_ROOT), name="uploads")
```

- `UPLOAD_ROOT` = `backend/data/uploads`（与 DB 同目录树）。
- 上传时生成 UUID 文件名；禁止 `..` 路径穿越。
- 生产与 dev 均从 FastAPI 同源提供（PWA 直接 `<img src="/uploads/...">`）。

## 前端

### 周计划页（`MealPlanPage` + `MealSlotModal`）

餐次 modal 分两块：

1. **计划** — 现有菜品列表；未标记 →「标记已做」；已标记 → ✓ + 缩略图（换图 / 取消标记）。
2. **实际（额外）** —「+ 追加实际做的菜」→ `RecipePicker` → POST extra。

餐次摘要行：计划菜名；若有已做 log 显示 ✓ 或小图角标。

### 饮食记录页（新 `JournalPage`）

- 路由：`/journal/:weekStart?`（默认当前周；周导航与计划页一致）。
- 按日分组：午/晚餐 → 菜名 + 缩略图 + 标签「计划内 / 额外」。
- 点击缩略图大图预览；点击菜名跳食谱详情（`recipe_id` 为空时仅显示 `recipe_name`）。
- 主导航增加「记录」入口。

### 食谱页

- **列表：** 有封面则显示缩略图。
- **表单/详情：** 封面上传（`input type=file accept="image/*"`，移动端可用 `capture`）；预览、替换、删除。
- 创建食谱时可后补封面，不阻塞保存。

### 文案（`locale/zh.ts` 示例）

| key | 文案 |
|---|---|
| `journal.title` | 饮食记录 |
| `cooked.markDone` | 标记已做 |
| `cooked.unmark` | 取消标记 |
| `cooked.addExtra` | 追加实际做的菜 |
| `cooked.planned` | 计划内 |
| `cooked.extra` | 额外 |
| `cooked.uploadPhoto` | 上传照片 |
| `recipe.cover` | 食谱封面 |

## 与 v1 行为的交互

| v1 操作 | 对 v2 数据的影响 |
|---|---|
| regenerate 清计划 | `CookedDishLog` **不删**；`meal_plan_entry_id` → NULL |
| 删单条 plan entry | 对应 log 的 `meal_plan_entry_id` → NULL |
| 删食谱 | plan entry CASCADE 删；log 的 `recipe_id` → NULL，保留 `recipe_name`；`RecipeImage` CASCADE 删 |
| 购物清单 / AI | **无变更** |

## 错误处理

- 上传失败：不写 DB；若已写 DB 则事务回滚并删半成品文件。
- 磁盘满或权限错误：502 + 中文提示。

## 测试

### 后端（TDD）

文件建议：`backend/tests/test_cooked_dishes.py`、`backend/tests/test_recipe_cover.py`

1. POST planned — 201；重复 POST → 409
2. POST extra — 201 sync 422
3. GET 日期过滤
4. DELETE log — 204；mock 断言删文件
5. regenerate 后 log 仍在，`meal_plan_entry_id` 为 null
6. POST cover — `cover_url` 非空；替换删旧文件
7. 非法 MIME / 超大 → 400/413

### 前端

- Vitest：`zh` 新 key 存在
- 手动：375×667 上传与标记可点；日记页缩略图加载正常

## Verify（手动）

1. 计划内标记 + 上传实拍 → 周视图与日记页均可见
2. 计划外从食谱库追加 → 显示「额外」标签
3. 补记上周某天（D2）→ 日记页可见
4. regenerate 后历史「实际做了」仍在
5. 食谱封面上传 → 列表/详情显示
6. 备份：拷贝 `backend/data/` 后在新环境可看到图

## 相关文档

| 文档 | 用途 |
|---|---|
| [PLAN-v2.md](../../PLAN-v2.md) | 分里程碑实现顺序 |
| [SPEC.md](../../SPEC.md) | v2 完成后更新产品能力（V2-M7） |
| [PLAN.md](../../PLAN.md) | v1 架构与已完成里程碑 |
