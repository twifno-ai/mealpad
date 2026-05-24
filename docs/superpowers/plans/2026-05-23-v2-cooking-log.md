# v2 实际制作记录与图片上传 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 支持基于膳食计划标记「实际做了」、计划外追加、每 log 一张实拍、食谱封面图，以及饮食记录页；图片存本地磁盘。

**Architecture:** 计划（`MealPlanEntry`）与实际（`CookedDishLog`）分离；封面用 `RecipeImage`（v2 仅 1 张 `is_cover`）。`backend/app/services/uploads.py` 统一校验/保存/删除；FastAPI 挂载 `/uploads`。前端并行 GET meal-plan + cooked-dishes 后 merge。

**Tech Stack:** FastAPI + SQLModel + SQLite；`python-multipart` + `Pillow`（缩略）；React PWA + Vitest。

**Spec:** [docs/superpowers/specs/2026-05-23-v2-cooking-log-design.md](../specs/2026-05-23-v2-cooking-log-design.md)  
**Milestone overview:** [docs/PLAN-v2.md](../../PLAN-v2.md)

---

## File map

| File | Responsibility |
|---|---|
| `backend/app/models.py` | `CookedDishLog`, `RecipeImage` |
| `backend/app/migrate.py` | 旧库建 v2 表 |
| `backend/app/config.py` | `upload_root` |
| `backend/app/services/uploads.py` | MIME/大小校验、保存、删除、可选 resize |
| `backend/app/routers/cooked_dishes.py` | 饮食记录 CRUD + multipart |
| `backend/app/routers/recipes.py` | cover POST/DELETE；list/get 带 `cover_url` |
| `backend/app/schemas.py` | `CookedDishLogRead`；`cover_url` on recipe schemas |
| `backend/app/main.py` | mount `/uploads`；include router |
| `backend/tests/conftest.py` | 临时 upload 目录 fixture |
| `frontend/src/api.ts` | types + multipart helpers |
| `frontend/src/components/MealSlotModal.tsx` | 计划/实际分区 |
| `frontend/src/pages/JournalPage.tsx` | 饮食记录页 |
| `frontend/src/pages/MealPlanPage.tsx` | merge cooked logs |
| `frontend/src/pages/RecipeFormPage.tsx` | 封面上传 |
| `frontend/src/pages/RecipesPage.tsx` | 列表缩略图 |

---

### Task 1: 配置、模型与上传服务（V2-M1）

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/config.py`
- Modify: `backend/app/models.py`
- Create: `backend/app/services/uploads.py`
- Modify: `backend/app/migrate.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/tests/test_uploads.py`

- [ ] **Step 1: 添加依赖**

在 `backend/pyproject.toml` 的 `dependencies` 增加：

```toml
"python-multipart>=0.0.9",
"Pillow>=11.0.0",
```

运行：`cd backend && .venv/bin/pip install -e ".[dev]"`

- [ ] **Step 2: 扩展 config**

```python
# backend/app/config.py
import os
from pathlib import Path

class Settings(BaseSettings):
  # ... existing fields ...
  upload_root: str = ""  # empty → sibling of db file

  def resolved_upload_root(self) -> Path:
    if self.upload_root:
      return Path(self.upload_root)
    return Path(self.db_path).parent / "uploads"
```

- [ ] **Step 3: 写失败测试 `test_uploads.py`**

```python
# backend/tests/test_uploads.py
from io import BytesIO

import pytest
from fastapi import UploadFile

from app.services import uploads

FAKE_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 200


def _upload_file(content: bytes, content_type: str, name: str = "photo.jpg") -> UploadFile:
  return UploadFile(file=BytesIO(content), filename=name, headers={"content-type": content_type})


def test_save_image_writes_file(upload_root):
  path = uploads.save_image(_upload_file(FAKE_JPEG, "image/jpeg"), subdir="test")
  assert path.startswith("test/")
  assert (upload_root / path).is_file()


def test_rejects_invalid_mime(upload_root):
  with pytest.raises(uploads.UploadError, match="格式"):
    uploads.save_image(_upload_file(b"not-image", "text/plain"), subdir="test")


def test_delete_file_removes(upload_root):
  path = uploads.save_image(_upload_file(FAKE_JPEG, "image/jpeg"), subdir="test")
  uploads.delete_stored_file(path)
  assert not (upload_root / path).exists()
```

- [ ] **Step 4: conftest 增加 `upload_root` fixture**

```python
# backend/tests/conftest.py — 在 reset_db 之后添加
@pytest.fixture(name="upload_root")
def upload_root_fixture(tmp_path, monkeypatch):
  root = tmp_path / "uploads"
  root.mkdir()
  from app.config import settings

  monkeypatch.setattr(settings, "upload_root", str(root))
  return root
```

- [ ] **Step 5: 运行测试确认 FAIL**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/pytest tests/test_uploads.py -v`  
Expected: FAIL — `ModuleNotFoundError` or `UploadError` not defined

- [ ] **Step 6: 实现 `uploads.py`**

```python
# backend/app/services/uploads.py
import imghdr
import uuid
from pathlib import Path

from fastapi import UploadFile
from PIL import Image

from ..config import settings

MAX_BYTES = 5 * 1024 * 1024
ALLOWED = {"jpeg", "png", "webp"}


class UploadError(ValueError):
  pass


def _root() -> Path:
  root = settings.resolved_upload_root()
  root.mkdir(parents=True, exist_ok=True)
  return root


def save_image(file: UploadFile | None, *, subdir: str) -> str | None:
  if file is None or file.filename is None:
    return None
  data = file.file.read()
  if len(data) > MAX_BYTES:
    raise UploadError("图片过大，单张不超过 5MB")
  kind = imghdr.what(None, h=data)
  if kind not in ALLOWED:
    raise UploadError("不支持的图片格式，请使用 JPEG、PNG 或 WebP")
  ext = "jpg" if kind == "jpeg" else kind
  dest_dir = _root() / subdir
  dest_dir.mkdir(parents=True, exist_ok=True)
  name = f"{uuid.uuid4().hex}.{ext}"
  dest = dest_dir / name
  dest.write_bytes(data)
  try:
    with Image.open(dest) as img:
      img.thumbnail((1200, 1200))
      img.save(dest, optimize=True)
  except OSError:
    dest.unlink(missing_ok=True)
    raise UploadError("无法读取图片文件")
  return f"{subdir}/{name}"


def delete_stored_file(relative_path: str | None) -> None:
  if not relative_path:
    return
  path = _root() / relative_path
  if path.is_file() and path.resolve().is_relative_to(_root().resolve()):
    path.unlink()
```

- [ ] **Step 7: 添加模型**

```python
# backend/app/models.py — append
class CookedDishLog(SQLModel, table=True):
  id: int | None = Field(default=None, primary_key=True)
  date: Date = Field(index=True)
  slot: str
  recipe_id: int | None = Field(default=None, foreign_key="recipe.id", ondelete="SET NULL")
  recipe_name: str
  kind: str  # planned | extra
  meal_plan_entry_id: int | None = Field(
    default=None, foreign_key="mealplanentry.id", ondelete="SET NULL", unique=True
  )
  photo_path: str | None = None
  logged_at: datetime = Field(default_factory=datetime.utcnow)


class RecipeImage(SQLModel, table=True):
  id: int | None = Field(default=None, primary_key=True)
  recipe_id: int = Field(foreign_key="recipe.id", ondelete="CASCADE", index=True)
  file_path: str
  sort_order: int = 0
  is_cover: bool = False
  created_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 8: migrate 旧库建表**

```python
# backend/app/migrate.py — migrate_db() 末尾追加
def _ensure_v2_tables(conn) -> None:
  inspector = inspect(engine)
  if not inspector.has_table("cookeddishlog"):
    SQLModel.metadata.create_all(engine, tables=[models.CookedDishLog.__table__])
  if not inspector.has_table("recipeimage"):
    SQLModel.metadata.create_all(engine, tables=[models.RecipeImage.__table__])
```

在 `migrate_db()` 最后调用 `_ensure_v2_tables`（需 import models）。测试环境 `create_all` 已建表，migrate 仅生产旧库需要。

- [ ] **Step 9: main.py 挂载 uploads**

```python
# backend/app/main.py
from .config import settings
from .services import uploads as upload_service

@asynccontextmanager
async def lifespan(_app: FastAPI):
  upload_service._root()  # ensure dir
  init_db()
  yield

upload_root = settings.resolved_upload_root()
if upload_root.exists():
  app.mount("/uploads", StaticFiles(directory=upload_root), name="uploads")
```

- [ ] **Step 10: 运行测试 PASS**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/pytest tests/test_uploads.py -v`

- [ ] **Step 11: Commit + push**

```bash
git add backend/pyproject.toml backend/app/config.py backend/app/models.py \
  backend/app/services/uploads.py backend/app/migrate.py backend/app/main.py \
  backend/tests/conftest.py backend/tests/test_uploads.py
git commit -m "feat(v2): add cooked log models, migration, and upload service"
git push
```

---

### Task 2: 饮食记录 API（V2-M2）

**Files:**
- Create: `backend/app/routers/cooked_dishes.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_cooked_dishes.py`
- Modify: `backend/tests/meal_plan_helpers.py`（可选 helper）

- [ ] **Step 1: 写 schema**

```python
# backend/app/schemas.py
class CookedDishLogRead(BaseModel):
  id: int
  date: Date
  slot: str
  recipe_id: int | None
  recipe_name: str
  kind: str
  meal_plan_entry_id: int | None
  photo_url: str | None
  logged_at: datetime
```

- [ ] **Step 2: 写失败测试（planned + 409）**

```python
# backend/tests/test_cooked_dishes.py
from tests.meal_plan_helpers import create_typed_recipes

FAKE_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 200


def _add_plan_entry(client, date, slot, recipe_id):
  return client.post(
    f"/api/meal-plan/{date}/{slot}/items",
    json={"recipe_id": recipe_id},
  ).json()


def test_mark_planned_dish(client):
  typed = create_typed_recipes(client)
  entry = _add_plan_entry(client, "2026-06-02", "lunch", typed["meat"]["id"])
  res = client.post(f"/api/cooked-dishes/planned/{entry['id']}")
  assert res.status_code == 201
  body = res.json()
  assert body["kind"] == "planned"
  assert body["recipe_name"] == "Meat Dish"
  assert body["meal_plan_entry_id"] == entry["id"]


def test_mark_planned_twice_returns_409(client):
  typed = create_typed_recipes(client)
  entry = _add_plan_entry(client, "2026-06-02", "lunch", typed["meat"]["id"])
  client.post(f"/api/cooked-dishes/planned/{entry['id']}")
  res = client.post(f"/api/cooked-dishes/planned/{entry['id']}")
  assert res.status_code == 409
```

Run: `pytest tests/test_cooked_dishes.py::test_mark_planned_dish -v` → FAIL (404 no route)

- [ ] **Step 3: 实现 router 核心**

```python
# backend/app/routers/cooked_dishes.py
from datetime import date as Date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlmodel import Session, select

from ..db import get_session
from ..models import CookedDishLog, MealPlanEntry, Recipe
from ..schemas import CookedDishLogRead
from ..services.uploads import UploadError, delete_stored_file, save_image

router = APIRouter()


def _to_read(log: CookedDishLog) -> CookedDishLogRead:
  return CookedDishLogRead(
    id=log.id,
    date=log.date,
    slot=log.slot,
    recipe_id=log.recipe_id,
    recipe_name=log.recipe_name,
    kind=log.kind,
    meal_plan_entry_id=log.meal_plan_entry_id,
    photo_url=f"/uploads/{log.photo_path}" if log.photo_path else None,
    logged_at=log.logged_at,
  )


@router.get("", response_model=list[CookedDishLogRead])
def list_cooked(
  start: Date = Query(...),
  end: Date = Query(...),
  session: Session = Depends(get_session),
):
  stmt = (
    select(CookedDishLog)
    .where(CookedDishLog.date >= start, CookedDishLog.date <= end)
    .order_by(CookedDishLog.date, CookedDishLog.slot, CookedDishLog.logged_at)
  )
  return [_to_read(row) for row in session.exec(stmt).all()]


@router.post("/planned/{entry_id}", response_model=CookedDishLogRead, status_code=201)
def mark_planned(
  entry_id: int,
  photo: UploadFile | None = File(default=None),
  session: Session = Depends(get_session),
):
  entry = session.get(MealPlanEntry, entry_id)
  if entry is None:
    raise HTTPException(status_code=404, detail="未找到计划条目")
  existing = session.exec(
    select(CookedDishLog).where(CookedDishLog.meal_plan_entry_id == entry_id)
  ).first()
  if existing:
    raise HTTPException(status_code=409, detail="该道菜已标记为已做")
  recipe = session.get(Recipe, entry.recipe_id)
  if recipe is None:
    raise HTTPException(status_code=422, detail="食谱不存在")
  try:
    photo_path = save_image(photo, subdir=f"cooked/pending")
  except UploadError as e:
    raise HTTPException(status_code=400, detail=str(e)) from e
  log = CookedDishLog(
    date=entry.date,
    slot=entry.slot,
    recipe_id=recipe.id,
    recipe_name=recipe.name,
    kind="planned",
    meal_plan_entry_id=entry.id,
    photo_path=photo_path,
  )
  session.add(log)
  session.commit()
  session.refresh(log)
  if photo_path and log.id:
    # rename pending → log id folder optional; or keep flat cooked/ uuid paths
    pass
  return _to_read(log)
```

简化：`subdir=f"cooked/{log.id or 'new'}"` 在 commit 后更新路径；或统一 `subdir="cooked"` 用 UUID 文件名（spec 允许 `cooked/{uuid}.jpg`）。

- [ ] **Step 4: 补全 extra POST、DELETE、photo PUT/DELETE**

```python
@router.post("/extra", response_model=CookedDishLogRead, status_code=201)
def add_extra(
  date: Date = Form(...),
  slot: str = Form(...),
  recipe_id: int = Form(...),
  photo: UploadFile | None = File(default=None),
  session: Session = Depends(get_session),
):
  if slot not in {"lunch", "dinner"}:
    raise HTTPException(status_code=422, detail="无效的餐次")
  recipe = session.get(Recipe, recipe_id)
  if recipe is None:
    raise HTTPException(status_code=404, detail="食谱不存在")
  dup = session.exec(
    select(CookedDishLog).where(
      CookedDishLog.date == date,
      CookedDishLog.slot == slot,
      CookedDishLog.recipe_id == recipe_id,
      CookedDishLog.kind == "extra",
    )
  ).first()
  if dup:
    raise HTTPException(status_code=422, detail="该餐已包含此食谱的实际记录")
  try:
    photo_path = save_image(photo, subdir="cooked")
  except UploadError as e:
    raise HTTPException(status_code=400, detail=str(e)) from e
  log = CookedDishLog(
    date=date,
    slot=slot,
    recipe_id=recipe.id,
    recipe_name=recipe.name,
    kind="extra",
    photo_path=photo_path,
  )
  session.add(log)
  session.commit()
  session.refresh(log)
  return _to_read(log)


@router.delete("/{log_id}", status_code=204)
def delete_log(log_id: int, session: Session = Depends(get_session)):
  log = session.get(CookedDishLog, log_id)
  if log is None:
    raise HTTPException(status_code=404, detail="未找到记录")
  delete_stored_file(log.photo_path)
  session.delete(log)
  session.commit()
```

- [ ] **Step 5: main.py include router**

```python
from .routers import cooked_dishes
app.include_router(cooked_dishes.router, prefix="/api/cooked-dishes", tags=["cooked-dishes"])
```

- [ ] **Step 6: 补全测试并扩展 regenerate 用例**

```python
def test_extra_duplicate_422(client):
  typed = create_typed_recipes(client)
  data = {"date": "2026-06-02", "slot": "dinner", "recipe_id": typed["veg"]["id"]}
  assert client.post("/api/cooked-dishes/extra", data=data).status_code == 201
  assert client.post("/api/cooked-dishes/extra", data=data).status_code == 422


def test_list_by_date_range(client):
  # ... create log, GET ?start=&end=
  pass


def test_delete_plan_entry_keeps_log(client):
  # mark planned, delete meal plan item, log still exists meal_plan_entry_id null
  pass
```

在 `test_meal_plan_regenerate.py` 加断言：regenerate 后 `GET /api/cooked-dishes` 条数不变。

- [ ] **Step 7: 全量 backend 测试 PASS**

Run: `cd backend && MEALPAD_TESTING=1 .venv/bin/pytest -v`

- [ ] **Step 8: Commit + push**

```bash
git commit -m "feat(v2): cooked dish log API with optional photos"
git push
```

---

### Task 3: 食谱封面 API（V2-M3）

**Files:**
- Modify: `backend/app/routers/recipes.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/tests/test_recipe_cover.py`

- [ ] **Step 1: 写失败测试**

```python
def test_upload_cover(client):
  recipe = client.post("/api/recipes", json={"name": "A", "type": "soup", "description": "", "ingredients": []}).json()
  res = client.post(
    f"/api/recipes/{recipe['id']}/cover",
    files={"photo": ("x.jpg", FAKE_JPEG, "image/jpeg")},
  )
  assert res.status_code == 201
  got = client.get(f"/api/recipes/{recipe['id']}").json()
  assert got["cover_url"] is not None
  assert got["cover_url"].startswith("/uploads/")
```

- [ ] **Step 2: 扩展 RecipeRead**

```python
class RecipeRead(RecipeBase):
  id: int
  created_at: datetime
  cover_url: str | None = None

class RecipeSummary(BaseModel):
  id: int
  name: str
  type: str
  cover_url: str | None = None
```

- [ ] **Step 3: 实现 helper + 路由**

```python
# recipes.py
from ..models import RecipeImage
from ..services.uploads import UploadError, delete_stored_file, save_image

def _cover_url(session: Session, recipe_id: int) -> str | None:
  img = session.exec(
    select(RecipeImage).where(RecipeImage.recipe_id == recipe_id, RecipeImage.is_cover == True)
  ).first()
  return f"/uploads/{img.file_path}" if img else None

def _recipe_read(session: Session, recipe: Recipe) -> RecipeRead:
  data = RecipeRead.model_validate(recipe)
  data.cover_url = _cover_url(session, recipe.id)
  return data

@router.post("/{recipe_id}/cover", status_code=201)
def upload_cover(recipe_id: int, photo: UploadFile = File(...), session: Session = Depends(get_session)):
  recipe = session.get(Recipe, recipe_id)
  if recipe is None:
    raise HTTPException(status_code=404, detail="Recipe not found")
  old = session.exec(select(RecipeImage).where(RecipeImage.recipe_id == recipe_id, RecipeImage.is_cover == True)).first()
  try:
    path = save_image(photo, subdir=f"recipes/{recipe_id}")
  except UploadError as e:
    raise HTTPException(status_code=400, detail=str(e)) from e
  if old:
    delete_stored_file(old.file_path)
    session.delete(old)
  session.add(RecipeImage(recipe_id=recipe_id, file_path=path, is_cover=True))
  session.commit()
  return {"cover_url": f"/uploads/{path}"}

@router.delete("/{recipe_id}/cover", status_code=204)
def delete_cover(...):
  # delete RecipeImage is_cover + file
```

更新 `list_recipes` / `get_recipe` 返回 `_recipe_read`。`MealPlanEntryRead` 内嵌的 `RecipeSummary` 也需带 `cover_url`（在 meal_plan router 组装时查询）。

- [ ] **Step 4: pytest tests/test_recipe_cover.py 全绿**

- [ ] **Step 5: Commit + push**

```bash
git commit -m "feat(v2): recipe cover image upload"
git push
```

---

### Task 4: 周计划页标记与追加（V2-M4）

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/locale/zh.ts`
- Modify: `frontend/src/components/MealSlotModal.tsx`
- Modify: `frontend/src/pages/MealPlanPage.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/locale/zh.test.ts`（若存在）

- [ ] **Step 1: api.ts 类型与方法**

```typescript
export interface CookedDishLog {
  id: number;
  date: string;
  slot: "lunch" | "dinner";
  recipe_id: number | null;
  recipe_name: string;
  kind: "planned" | "extra";
  meal_plan_entry_id: number | null;
  photo_url: string | null;
  logged_at: string;
}

async function reqForm<T>(path: string, form: FormData, method = "POST"): Promise<T> {
  const res = await fetch(path, { method, body: form });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json();
}

export const api = {
  // ...
  getCookedDishes: (start: string, end: string) =>
    req<CookedDishLog[]>(`/api/cooked-dishes?start=${start}&end=${end}`),
  markPlannedCooked: (entryId: number, photo?: File) => {
    const form = new FormData();
    if (photo) form.append("photo", photo);
    return reqForm<CookedDishLog>(`/api/cooked-dishes/planned/${entryId}`, form);
  },
  addExtraCooked: (date: string, slot: string, recipeId: number, photo?: File) => {
    const form = new FormData();
    form.append("date", date);
    form.append("slot", slot);
    form.append("recipe_id", String(recipeId));
    if (photo) form.append("photo", photo);
    return reqForm<CookedDishLog>("/api/cooked-dishes/extra", form);
  },
  deleteCookedLog: (logId: number) =>
    req<void>(`/api/cooked-dishes/${logId}`, { method: "DELETE" }),
};
```

- [ ] **Step 2: zh.ts 文案**

```typescript
cooked: {
  sectionPlanned: "计划",
  sectionActual: "实际",
  markDone: "标记已做",
  unmark: "取消标记",
  addExtra: "追加实际做的菜",
  planned: "计划内",
  extra: "额外",
  uploadPhoto: "上传照片",
},
journal: {
  title: "饮食记录",
  empty: "本周还没有饮食记录",
},
```

- [ ] **Step 3: MealPlanPage 并行加载**

```typescript
const [cookedLogs, setCookedLogs] = useState<CookedDishLog[]>([]);

const load = useCallback(async () => {
  const [plan, cooked] = await Promise.all([
    api.getMealPlan(startIso, endIso),
    api.getCookedDishes(startIso, endIso),
  ]);
  setEntries(plan);
  setCookedLogs(cooked);
}, [startIso, endIso]);

function cookedForMeal(date: string, slot: string) {
  return cookedLogs.filter((l) => l.date === date && l.slot === slot);
}

function cookedForEntry(entryId: number) {
  return cookedLogs.find((l) => l.meal_plan_entry_id === entryId);
}
```

- [ ] **Step 4: MealSlotModal 分节 UI**

Props 扩展：

```typescript
interface Props {
  // existing...
  cookedLogs: CookedDishLog[];
  onMarkCooked: (entryId: number, photo?: File) => Promise<void>;
  onUnmarkCooked: (logId: number) => Promise<void>;
  onAddExtra: () => void;
}
```

计划列表每行：若 `cookedForEntry(entry.id)` 存在 → 显示 ✓ + `<img src={photo_url}>` + 取消；否则「标记已做」+ 隐藏 file input。

实际区块：过滤 `kind === "extra"` 的 logs 列出；底部「追加实际做的菜」触发父组件打开 RecipePicker → `api.addExtraCooked`。

- [ ] **Step 5: CSS 缩略图**

```css
.cooked-thumb {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 6px;
}
.meal-section-title {
  font-weight: 600;
  margin: 12px 0 8px;
}
```

- [ ] **Step 6: Vitest zh keys**

Run: `cd frontend && npm test`

- [ ] **Step 7: 手动 375×667 验证后 commit + push**

```bash
git commit -m "feat(v2): mark cooked dishes on meal plan page"
git push
```

---

### Task 5: 食谱封面 UI（V2-M5）

**Files:**
- Modify: `frontend/src/pages/RecipeFormPage.tsx`
- Modify: `frontend/src/pages/RecipesPage.tsx`
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: api cover helpers**

```typescript
uploadRecipeCover: (id: number, photo: File) => {
  const form = new FormData();
  form.append("photo", photo);
  return reqForm<{ cover_url: string }>(`/api/recipes/${id}/cover`, form);
},
deleteRecipeCover: (id: number) =>
  req<void>(`/api/recipes/${id}/cover`, { method: "DELETE" }),
```

- [ ] **Step 2: RecipeFormPage 封面上传区**

编辑模式（有 `id`）显示：

```tsx
{recipe?.cover_url && <img src={recipe.cover_url} alt="" className="recipe-cover-preview" />}
<input type="file" accept="image/*" onChange={(e) => handleCover(e.target.files?.[0])} />
<button type="button" onClick={handleDeleteCover}>{zh.delete}</button>
```

`handleCover` 调用 `api.uploadRecipeCover` 后 refresh recipe。

- [ ] **Step 3: RecipesPage 列表缩略图**

在 `list-row-title` 前加： `{r.cover_url && <img className="recipe-list-thumb" src={r.cover_url} alt="" />}`

- [ ] **Step 4: npm run build 通过；commit + push**

```bash
git commit -m "feat(v2): recipe cover upload in UI"
git push
```

---

### Task 6: 饮食记录页（V2-M6）

**Files:**
- Create: `frontend/src/pages/JournalPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/MealPlanPage.tsx`（header 加链接）
- Modify: `frontend/src/pages/RecipesPage.tsx`（可选导航）
- Modify: `frontend/src/locale/zh.ts`

- [ ] **Step 1: JournalPage 骨架**

复用 `MealPlanPage` 的 week-nav（`mondayOfWeek` / `goWeek`）。按 7 天 loop：

```tsx
for (let i = 0; i < 7; i++) {
  const day = formatIsoDate(addDays(weekStart, i));
  const dayLogs = logs.filter((l) => l.date === day);
  // render lunch/dinner groups with slotLabel
}
```

每条 log：缩略图、`recipe_name`、badge（`zh.cooked.planned` / `zh.cooked.extra`）；`recipe_id` 存在则 `<Link to={/recipes/${id}/edit}>`。

- [ ] **Step 2: 路由与导航**

```tsx
// App.tsx
<Route path="/journal" element={<Navigate to={`/journal/${defaultWeek}`} replace />} />
<Route path="/journal/:weekStart" element={<JournalPage />} />

// MealPlanPage header
<Link to={`/journal/${startIso}`} className="btn btn-secondary">{zh.journal.title}</Link>
```

- [ ] **Step 3: 大图预览（轻量）**

点击缩略图 → `window.open(photo_url)` 或简单 modal，不引入新库。

- [ ] **Step 4: 手动验证 + commit + push**

```bash
git commit -m "feat(v2): journal page for cooking history"
git push
```

---

### Task 7: 文档与全量验证（V2-M7）

**Files:**
- Modify: `docs/SPEC.md`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-23-v2-cooking-log-design.md` — 状态 → 已完成
- Modify: `CLAUDE.md` — 可选一句 v2 uploads 备份说明

- [ ] **Step 1: 更新 SPEC.md**

在 Core capabilities 增加第 8–10 条（实际记录、实拍、封面、日记页）。从 Out of scope 删除 Photos 一行。

- [ ] **Step 2: README 备份说明**

```markdown
Backup: copy the entire `backend/data/` directory (includes `mealpad.db` and `uploads/`).
```

- [ ] **Step 3: 全量验证**

```bash
cd backend && MEALPAD_TESTING=1 .venv/bin/pytest -v
cd frontend && npm test && npm run build
make build && make serve
```

手机 LAN：标记一顿 + 上传照片 + 日记页可见。

- [ ] **Step 4: Commit + push**

```bash
git commit -m "docs: update SPEC and README for v2 cooking log and images"
git push
```

---

## Spec coverage checklist

| Spec 要求 | Task |
|---|---|
| CookedDishLog 模型 + SET NULL | Task 1–2 |
| RecipeImage 预留 | Task 1, 3 |
| 本地 uploads + /uploads 挂载 | Task 1 |
| cooked-dishes API 全套 | Task 2 |
| recipe cover API | Task 3 |
| 周计划 merge + modal | Task 4 |
| 食谱封面 UI | Task 5 |
| JournalPage | Task 6 |
| regenerate 不删 log | Task 2 测试 |
| SPEC/README 更新 | Task 7 |

## 全量回归清单

- [ ] v1 膳食计划 / AI fill / regenerate / 购物清单正常
- [ ] regenerate 后饮食记录仍在
- [ ] 拷贝 `backend/data/` 可恢复 DB + 图片
- [ ] 中文上传错误可见
- [ ] 375×667 tap targets ≥ 44px
