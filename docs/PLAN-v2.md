# Mealpad — v2 Implementation Plan

## Context

v1（M1–M9 + 多道菜 / 双 AI / 中文 UI / regenerate）已交付。v2 在 **不改变** 膳食计划、购物清单、AI 核心流程的前提下，增加：

- 基于计划标记「实际做了」+ 计划外追加（食谱库）
- 实际菜实拍（每 log 最多 1 张）
- 食谱封面（每食谱 1 张，结构预留多图）
- 饮食记录页（按周/按日浏览历史）

**设计 spec（权威细节）：** [superpowers/specs/2026-05-23-v2-cooking-log-design.md](superpowers/specs/2026-05-23-v2-cooking-log-design.md)

**前置：** 阅读 spec 中「已确认决策」「数据模型」「API」三节。

## v2 设计决策（锁定）

| 区域 | 选择 |
|---|---|
| 计划 vs 实际 | 独立 `CookedDishLog` 表；计划仍为 `MealPlanEntry` |
| 计划外 | 食谱库选菜，挂 lunch/dinner，UI 标「额外」 |
| 图片 | 本地磁盘 `backend/data/uploads/`；DB 存相对路径 |
| 静态访问 | FastAPI `mount /uploads` |
| 周计划数据 | 前端并行 GET meal-plan + cooked-dishes，本地 merge |
| 删食谱 | log 保留 `recipe_name` 快照；`recipe_id` SET NULL |

## 架构增量

```
backend/app/
├── models.py              # + CookedDishLog, RecipeImage
├── schemas.py             # + CookedDishLogRead, cover_url on RecipeRead
├── migrate.py             # 新表 migration
├── services/
│   └── uploads.py         # 保存/删除/校验图片；可选 PIL 缩略
├── routers/
│   ├── cooked_dishes.py   # 新
│   └── recipes.py         # + cover POST/DELETE
└── main.py                # mount /uploads, include cooked router

frontend/src/
├── pages/
│   ├── JournalPage.tsx    # 新
│   ├── MealPlanPage.tsx   # merge cooked logs
│   └── RecipeFormPage.tsx # 封面上传
├── components/
│   └── MealSlotModal.tsx  # 计划/实际分区
└── api.ts                 # cooked + cover API
```

## API Surface（v2 新增）

```
GET    /api/cooked-dishes?start=&end=
POST   /api/cooked-dishes/planned/{entry_id}     multipart, optional photo
POST   /api/cooked-dishes/extra                  multipart: date, slot, recipe_id, optional photo
PUT    /api/cooked-dishes/{log_id}/photo         multipart photo
DELETE /api/cooked-dishes/{log_id}/photo
DELETE /api/cooked-dishes/{log_id}

POST   /api/recipes/{id}/cover                   multipart photo
DELETE /api/recipes/{id}/cover

GET    /uploads/...                              static files
```

`RecipeRead` / `RecipeSummary` 响应增加 `cover_url: string | null`。

---

## Milestones

每个里程碑可独立 demo，结束时 **commit + push**（作者 `twifno-ai <twifnoai@gmail.com>`）。后端 listed 测试遵循 TDD：先写失败测试，再实现。

---

### V2-M1 — 数据模型、迁移与上传服务

**Files:**

- Modify: `backend/app/models.py` — `CookedDishLog`, `RecipeImage`
- Modify: `backend/app/migrate.py` — 建表 migration
- Create: `backend/app/services/uploads.py` — `save_image(file, subdir) -> relative_path`, `delete_file(path)`, MIME/size 校验
- Modify: `backend/app/config.py` — `upload_root: Path`（默认 `backend/data/uploads`）
- Modify: `backend/app/main.py` — 启动时 `ensure_upload_dirs()`；`mount /uploads`
- Modify: `.gitignore` — 确保 `backend/data/uploads/` 被忽略（或整个 `backend/data/` 已覆盖）

**Tests:**

- Create: `backend/tests/test_uploads.py` — 合法/非法 MIME、超大小、删除文件

**Verify:**

- `pytest backend/tests/test_uploads.py` 通过
- 启动后 `backend/data/uploads/` 存在；访问 `/uploads/` 不 404（空目录即可）

**Commit:** `feat(v2): add cooked log models, migration, and upload service`

---

### V2-M2 — 饮食记录 API

**Files:**

- Create: `backend/app/routers/cooked_dishes.py`
- Modify: `backend/app/schemas.py` — `CookedDishLogRead`
- Modify: `backend/app/main.py` — include router `/api/cooked-dishes`
- Create: `backend/tests/test_cooked_dishes.py`

**Tests:**

1. POST planned — 201；`recipe_name` 快照正确
2. 重复 POST planned → 409
3. POST extra；重复 `(date, slot, recipe_id)` → 422
4. GET `?start=&end=` 过滤
5. PUT/DELETE photo；DELETE log
6. 删 plan entry 后 log 仍在，`meal_plan_entry_id` null
7. regenerate 后 log 仍在（复用/扩展现有 regenerate 测试）

**Verify:**

- `pytest backend/tests/test_cooked_dishes.py` 全绿

**Commit:** `feat(v2): cooked dish log API with optional photos`

---

### V2-M3 — 食谱封面 API

**Files:**

- Modify: `backend/app/routers/recipes.py` — POST/DELETE cover
- Modify: `backend/app/schemas.py` — `cover_url` on `RecipeRead`, `RecipeSummary`
- Create: `backend/tests/test_recipe_cover.py`

**Tests:**

1. POST cover — 201；GET recipe 含 `cover_url`
2. 替换封面 — 旧文件删除（mock）
3. DELETE cover — `cover_url` null
4. 非法文件 → 400/413

**Verify:**

- `pytest backend/tests/test_recipe_cover.py` 通过
- `curl` 上传后浏览器可打开 `/uploads/recipes/...`

**Commit:** `feat(v2): recipe cover image upload`

---

### V2-M4 — 周计划页：标记与追加

**Files:**

- Modify: `frontend/src/api.ts` — cooked-dishes 客户端
- Modify: `frontend/src/components/MealSlotModal.tsx` — 计划/实际分区 UI
- Modify: `frontend/src/pages/MealPlanPage.tsx` — 并行加载 cooked logs；摘要 ✓/缩略图
- Modify: `frontend/src/locale/zh.ts` — cooked.* 文案
- Modify: `frontend/src/styles.css` — 缩略图、上传按钮（≥44px）

**Tests:**

- Vitest：`zh.cooked.*` keys 存在

**Verify（手动 375×667）:**

1. 计划内标记「已做」+ 可选上传照片
2. 追加计划外菜，显示「额外」
3. 取消标记后 UI 恢复
4. 切换周仍正确加载

**Commit:** `feat(v2): mark cooked dishes on meal plan page`

---

### V2-M5 — 食谱封面 UI

**Files:**

- Modify: `frontend/src/pages/RecipesPage.tsx` — 列表缩略图
- Modify: `frontend/src/pages/RecipeFormPage.tsx` — 封面上传/预览/删除
- Modify: `frontend/src/api.ts` — cover multipart helpers

**Verify（手动）:**

1. 新建食谱后可补封面
2. 替换/删除封面即时更新列表

**Commit:** `feat(v2): recipe cover upload in UI`

---

### V2-M6 — 饮食记录页

**Files:**

- Create: `frontend/src/pages/JournalPage.tsx`
- Modify: `frontend/src/App.tsx` — 路由 `/journal/:weekStart?`；导航「记录」
- Modify: `frontend/src/locale/zh.ts` — journal.* 文案

**Verify（手动）:**

1. 按日分组显示午/晚餐与实际记录
2. 缩略图点击预览；有 `recipe_id` 可跳详情
3. 周导航与计划页一致

**Commit:** `feat(v2): journal page for cooking history`

---

### V2-M7 — 文档与全量验证

**Files:**

- Modify: `docs/SPEC.md` — 增加 v2 能力；从「Explicitly out of scope」移除 Photos
- Modify: `README.md` — 备份说明含 `uploads/`；可选 v2 功能一句
- Modify: `docs/superpowers/specs/2026-05-23-v2-cooking-log-design.md` — 状态改为「已完成」

**Verify:**

```bash
cd backend && MEALPAD_TESTING=1 .venv/bin/pytest -v
cd frontend && npm test && npm run build
make build && make serve   # 手机 LAN 抽检上传
```

**Commit:** `docs: update SPEC and README for v2 cooking log and images`

---

## 全量回归清单（v2 完成后）

- [ ] v1 膳食计划 CRUD / AI fill / regenerate 仍正常
- [ ] 购物清单生成不受 cooked log 影响
- [ ] regenerate 不删饮食记录
- [ ] 拷贝 `backend/data/` 可完整恢复 DB + 图片
- [ ] 中文错误信息在上传失败时可见

## Related docs

| Doc | Purpose |
|---|---|
| [SPEC.md](SPEC.md) | 产品 spec（v2 完成后更新） |
| [PLAN.md](PLAN.md) | v1 里程碑与当前架构 |
| [2026-05-23-v2-cooking-log-design.md](superpowers/specs/2026-05-23-v2-cooking-log-design.md) | v2 设计细节 |
