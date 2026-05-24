# Mealpad — Project Implementation Plan

## Context

SPEC.md describes a family-oriented meal planning tool: store recipes, plan meals by week, AI-generate plans from saved recipes, auto-generate shopping lists. **Milestones M1–M9 are complete.** Post-v1 enhancements (Chinese UI, dual AI provider, meal regenerate, multi-dish meals) are also shipped — see [Current state](#current-state-as-built) below.

The goal of v1 is to remove repetitive weekday "what's for dinner" decisions and prevent the family from arriving at the store missing one ingredient — nothing more. We are not building a recipe social network, nutrition tracker, or grocery delivery integration.

## Design Decisions (locked with the user)

| Area | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLModel, SQLite |
| Frontend | React + Vite + TypeScript, PWA, **Simplified Chinese UI** |
| AI | **Anthropic Claude or OpenAI** (`anthropic` / `openai` SDKs), tool use; provider via `.env` |
| Auth | None — trusted local-network deployment |
| Meal slots | Lunch + Dinner per day. **Multiple recipes per meal** (dishes). Stored per-date (no week container). |
| AI meals | Fill/regenerate assign **3 dishes** per meal: `meat` + `veg` + `soup` |
| Ingredients | Free-text per recipe; AI merges across recipes for shopping list |
| Recipe entry | Manual form only |
| Shopping list | Stateful per `(start_date, end_date)`, items can be checked off |

## Architecture

A single FastAPI process serves both the JSON API (`/api/...`) and the built React PWA (`/`) from the same origin — no CORS in production. AI SDKs are server-side only; API keys never reach the browser. SQLite lives at `backend/data/mealpad.db` (gitignored). **`app/migrate.py`** runs lightweight SQLite migrations on startup. Deployment is `uvicorn app.main:app --host 0.0.0.0 --port 8000` on a household machine; family members visit `http://<host>:8000` from any device on the **same LAN subnet**.

### File layout

```
mealpad/
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py                 # AI provider + model settings
│   │   ├── db.py
│   │   ├── migrate.py                # SQLite schema upgrades
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── routers/
│   │   │   ├── recipes.py
│   │   │   ├── meal_plan.py          # dishes CRUD + generate + regenerate
│   │   │   └── shopping_lists.py
│   │   └── services/
│   │       ├── ai.py                 # provider dispatch
│   │       ├── llm_config.py
│   │       ├── llm_errors.py
│   │       └── providers/
│   │           ├── base.py           # shared tool schemas + prompts
│   │           ├── anthropic.py
│   │           └── openai_provider.py
│   ├── tests/
│   └── data/                         # gitignored runtime DB
├── frontend/
│   └── src/
│       ├── api.ts
│       ├── httpErrors.ts             # Chinese HTTP error formatting
│       ├── locale/zh.ts              # UI strings
│       ├── pages/
│       └── components/
│           ├── RecipePicker.tsx
│           └── MealSlotModal.tsx     # per-meal dish list
├── docs/superpowers/specs/           # post-v1 design specs
├── Makefile
├── README.md
├── CLAUDE.md
├── PLAN.md
└── SPEC.md
```

## Data Model

```python
# app/models.py
from datetime import date, datetime
from sqlmodel import SQLModel, Field, Column, JSON, UniqueConstraint

class Recipe(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str = ""
    type: str = Field(index=True)                          # "soup" | "meat" | "veg" | "other"
    ingredients: list[str] = Field(sa_column=Column(JSON)) # free-text lines, one per ingredient
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MealPlanEntry(SQLModel, table=True):
    """One dish in a meal. Multiple rows per (date, slot) allowed."""
    __table_args__ = (UniqueConstraint("date", "slot", "recipe_id"),)
    id: int | None = Field(default=None, primary_key=True)
    date: date = Field(index=True)
    slot: str                                              # "lunch" | "dinner"
    recipe_id: int = Field(foreign_key="recipe.id", ondelete="CASCADE")
    sort_order: int = 0                                    # display order within the meal
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ShoppingList(SQLModel, table=True):
    """A consolidated grocery list for a date range. One list per (start, end)."""
    __table_args__ = (UniqueConstraint("start_date", "end_date"),)
    id: int | None = Field(default=None, primary_key=True)
    start_date: date = Field(index=True)
    end_date: date
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class ShoppingListItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    shopping_list_id: int = Field(foreign_key="shoppinglist.id", index=True)
    text: str                                              # merged free-text line, e.g. "garlic, 5 cloves"
    category: str = ""                                     # produce|meat|dairy|pantry|frozen|bakery|other
    checked: bool = False
```

Notes:
- **No "plan" entity.** Meal plans are derived: "the plan for week W" is just the set of `MealPlanEntry` rows whose `date` falls inside W.
- **Empty meal = no rows** for `(date, slot)`. The frontend renders "+ 添加" for empty meals.
- **Multiple dishes per meal.** Same `(date, slot)` can have many entries; `(date, slot, recipe_id)` is unique.
- **`recipe_id` is non-null on entries.** Foreign key uses `ON DELETE CASCADE`.
- **Shopping list is keyed by date range**, not by a plan id. Re-generating updates in place (resets checks). **Regenerating the meal plan** for a range deletes the shopping list for that range.
- `ingredients` is a JSON array column — keeps free-text lines without a separate table.

## API Surface

```
GET    /api/health

GET    /api/recipes?type=<type>
POST   /api/recipes
GET    /api/recipes/{id}
PUT    /api/recipes/{id}
DELETE /api/recipes/{id}

GET    /api/meal-plan?start=YYYY-MM-DD&end=YYYY-MM-DD   entries in range (one row per dish)
POST   /api/meal-plan/{date}/{slot}/items              body: {recipe_id}; add dish; 201
PUT    /api/meal-plan/items/{entry_id}                 body: {recipe_id}; replace dish
DELETE /api/meal-plan/items/{entry_id}                 remove one dish; 204
DELETE /api/meal-plan/{date}/{slot}                    clear all dishes in meal; 204
POST   /api/meal-plan/generate                         body: {start, end}; AI fills empty meals (3 dishes each)
POST   /api/meal-plan/regenerate                      body: {start, end}; AI rebuilds all meals; deletes shopping list

GET    /api/shopping-lists?start=YYYY-MM-DD&end=YYYY-MM-DD
POST   /api/shopping-lists                             body: {start, end}; AI merge; resets checks
PATCH  /api/shopping-list-items/{id}                   body: {checked: bool}
```

Collection routes use **no trailing slash** (e.g. `POST /api/recipes`, not `/api/recipes/`).

All non-`/api/*` paths fall through to the SPA `index.html` so React Router owns the client routes.

## AI Integration (`app/services/`)

Two AI operations — meal assignment and shopping-list merge — share a **provider layer**:

- `llm_config.py` — resolve `AI_PROVIDER` or auto-detect (Anthropic first)
- `providers/anthropic.py` — Claude via `anthropic` SDK
- `providers/openai_provider.py` — ChatGPT via `openai` SDK (`max_completion_tokens` on GPT-5+)
- `providers/base.py` — shared tool schemas and system prompts
- `llm_errors.py` — map SDK errors to Chinese messages

Both calls use **tool use** for guaranteed JSON. Anthropic uses **prompt caching** on system prompts. Misconfiguration → HTTP 502 with Chinese `detail`.

Default models: `claude-sonnet-4-6` (Anthropic), `gpt-5.5` (OpenAI); overridable in `.env`.

### `generate_plan(empty_meals, available_recipes) -> list[MealAssignment]`

Backs `POST /api/meal-plan/generate` and `POST /api/meal-plan/regenerate`. Server passes empty or all `(date, slot)` pairs plus recipes. Model returns **one assignment per meal**, each with **three dishes** (`meat`, `veg`, `soup`). Server validates types and recipe IDs before writing rows.

Tool schema (simplified):

```json
{
  "assignments": [{
    "date": "2026-05-12",
    "slot": "lunch",
    "dishes": [
      {"recipe_id": 1, "type": "meat"},
      {"recipe_id": 2, "type": "veg"},
      {"recipe_id": 3, "type": "soup"}
    ]
  }]
}
```

**Generate** only writes to meals with **zero** existing dishes. **Regenerate** calls AI first, then deletes all entries + shopping list in range, then writes new dishes.

System prompt guidance: don't repeat the same recipe within 2 days; vary choices across consecutive meals; only use `recipe_id` values from the provided list. Server validates every dish before writing.

### `merge_ingredients(ingredient_lines) -> list[{text, category}]`

Backs `POST /api/shopping-lists`. Server collects all ingredient lines from all meal-plan entries in the date range (duplicates included so the model can sum quantities).

Tool schema:

```json
{
  "name": "build_shopping_list",
  "description": "Consolidate ingredient lines into a deduped, summed, categorized shopping list.",
  "input_schema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "text": {"type": "string", "description": "Human-readable line, e.g. 'garlic, 5 cloves'"},
            "category": {"type": "string", "enum": ["produce","meat","dairy","pantry","frozen","bakery","other"]}
          },
          "required": ["text", "category"]
        }
      }
    },
    "required": ["items"]
  }
}
```

## Current state (as built)

Beyond M1–M9, these enhancements are **shipped**:

| Feature | Spec | Summary |
|---|---|---|
| Simplified Chinese UI | `docs/superpowers/specs/2026-05-23-ui-chinese-design.md` | All pages, errors, PWA manifest |
| Dual AI provider | `docs/superpowers/specs/2026-05-24-openai-provider-design.md` | Claude + OpenAI via `.env` |
| Regenerate meal plan | `docs/superpowers/specs/2026-05-24-meal-plan-regenerate-design.md` | Full-week AI replan; deletes shopping list |
| Multi-dish meals | `docs/superpowers/specs/2026-05-23-multi-dish-meal-design.md` | 3 AI dishes per meal; per-dish CRUD |

Historical milestone sections below document the original M1–M9 build order; treat **Context**, **Design Decisions**, **Data Model**, **API Surface**, and **AI Integration** above as the authoritative current reference.

---

## Milestones

Each milestone produces working, demoable software and ends in a commit. Use TDD where tests are listed: write the failing test first, see it fail, implement, see it pass.

---

### M1 — Repo Scaffold

**Files:**
- Create: `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/config.py`, `backend/.env.example`
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/styles.css`
- Create: `Makefile`, `README.md`
- Modify: `.gitignore` — append `frontend/node_modules/`, `frontend/dist/`, `backend/data/`, `backend/.env`

`backend/pyproject.toml` deps: `fastapi`, `uvicorn[standard]`, `sqlmodel`, `pydantic-settings`, `anthropic`, `python-dotenv`. Dev: `pytest`, `pytest-asyncio`, `httpx`, `ruff`.

`frontend/package.json` deps: `react`, `react-dom`, `react-router-dom`. Dev: `vite`, `@vitejs/plugin-react`, `typescript`, `vite-plugin-pwa`, `@types/react`, `@types/react-dom`.

`backend/app/main.py` (initial):

```python
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="mealpad")

@app.get("/api/health")
def health():
    return {"ok": True}

dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="spa")
```

`backend/app/config.py`:

```python
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str = ""
    db_path: str = str(Path(__file__).resolve().parent.parent / "data" / "mealpad.db")
    model_config = {"env_file": ".env"}

settings = Settings()
```

`frontend/vite.config.ts` — React plugin + `vite-plugin-pwa` (manifest filled in M8) + `server.proxy['/api'] = 'http://localhost:8000'`.

`Makefile` targets: `dev-backend`, `dev-frontend`, `build`, `serve`.

**Verify:**
- `cd backend && pip install -e . && uvicorn app.main:app --reload` → `curl localhost:8000/api/health` returns `{"ok": true}`.
- `cd frontend && npm install && npm run dev` → browser at `:5173` shows "mealpad" placeholder.

**Commit:** `chore: scaffold FastAPI backend and Vite/React frontend`

---

### M2 — Database & Models

**Files:**
- Create: `backend/app/db.py`, `backend/app/models.py`
- Modify: `backend/app/main.py` — add `@app.on_event("startup")` calling `init_db()`
- Create: `backend/tests/conftest.py`, `backend/tests/test_models.py`

`backend/app/db.py`:

```python
from sqlmodel import SQLModel, Session, create_engine
from .config import settings

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)

def init_db() -> None:
    from . import models  # noqa: F401 — register tables
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
```

`backend/tests/conftest.py` — fixture swapping `engine` for `sqlite:///:memory:` and yielding a session.

**Tests (write first, watch fail, implement, watch pass):**
1. Create a Recipe with ingredients=`["2 cloves garlic", "salt"]`, reload from DB, ingredients round-trip as a list.
2. Create `MealPlanEntry` rows for several `(date, slot)` pairs across two weeks, query by date range, get back the expected rows ordered by `(date, slot)`.
3. Inserting a second `MealPlanEntry` with the same `(date, slot)` raises `IntegrityError`.
4. Deleting a Recipe referenced by an entry removes the entry (CASCADE) — verify the entry no longer exists.
5. Create a `ShoppingList` for `(start_date, end_date)`; inserting another for the same range raises `IntegrityError`.

**Verify:** `cd backend && pytest -v` — 5 model tests pass.

**Commit:** `feat: data model (recipes, meal plans, shopping lists)`

---

### M3 — Recipes CRUD API

**Files:**
- Create: `backend/app/schemas.py`, `backend/app/routers/recipes.py`
- Modify: `backend/app/main.py` — `app.include_router(recipes.router, prefix="/api/recipes")`
- Create: `backend/tests/test_recipes.py`

`schemas.py` (recipe section):

```python
from pydantic import BaseModel, Field
from datetime import datetime

RECIPE_TYPES = {"soup", "meat", "veg", "other"}

class RecipeBase(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    type: str
    ingredients: list[str]

class RecipeCreate(RecipeBase): pass
class RecipeUpdate(RecipeBase): pass

class RecipeRead(RecipeBase):
    id: int
    created_at: datetime
```

Router endpoints (each ~5-line FastAPI handler using `Session = Depends(get_session)`):
- `GET /` with optional `?type=` query
- `POST /` — validates `type in RECIPE_TYPES`, returns 201
- `GET /{id}` — 404 if missing
- `PUT /{id}` — full replace, 404 if missing
- `DELETE /{id}` — 204

**Tests (TDD, one per endpoint + edge cases):**
1. `POST` then `GET /` returns the created recipe.
2. `POST` with invalid `type` → 422.
3. `GET /?type=soup` filters correctly.
4. `PUT` updates fields, `created_at` unchanged.
5. `DELETE` removes; subsequent `GET /{id}` → 404.

**Verify:** `pytest backend/tests/test_recipes.py -v` green; manual `curl -X POST localhost:8000/api/recipes -H 'content-type: application/json' -d '{"name":"Tomato soup","type":"soup","description":"","ingredients":["3 tomatoes","1 onion"]}'` round-trips.

**Commit:** `feat: recipe CRUD API`

---

### M4 — Frontend Recipe Pages

**Files:**
- Create: `frontend/src/api.ts`
- Create: `frontend/src/pages/RecipesPage.tsx`, `frontend/src/pages/RecipeFormPage.tsx`
- Modify: `frontend/src/App.tsx` — add routes `/recipes`, `/recipes/new`, `/recipes/:id/edit`; redirect `/` → `/plan` (route will exist in M5)
- Modify: `frontend/src/styles.css` — mobile-first, large tap targets (min 44px), single-column layout under 600px

`frontend/src/api.ts`:

```ts
export type RecipeType = 'soup' | 'meat' | 'veg' | 'other';
export const RECIPE_TYPES: RecipeType[] = ['soup','meat','veg','other'];

export interface Recipe {
  id: number;
  name: string;
  description: string;
  type: RecipeType;
  ingredients: string[];
  created_at: string;
}
export interface RecipeInput {
  name: string; description: string; type: RecipeType; ingredients: string[];
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { 'content-type': 'application/json' }, ...init });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  listRecipes: (type?: RecipeType) =>
    req<Recipe[]>(`/api/recipes${type ? `?type=${type}` : ''}`),
  getRecipe: (id: number) => req<Recipe>(`/api/recipes/${id}`),
  createRecipe: (body: RecipeInput) =>
    req<Recipe>('/api/recipes', { method: 'POST', body: JSON.stringify(body) }),
  updateRecipe: (id: number, body: RecipeInput) =>
    req<Recipe>(`/api/recipes/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteRecipe: (id: number) =>
    req<void>(`/api/recipes/${id}`, { method: 'DELETE' }),
};
```

`RecipesPage.tsx`: lists recipes grouped by type, "+ New recipe" button, swipe-or-button delete with confirm.

`RecipeFormPage.tsx`: name (text), type (select from `RECIPE_TYPES`), description (textarea), ingredients (textarea — one line per ingredient, split on `\n` before submit, join with `\n` when loading for edit).

**Verify:** Browser at `:5173/recipes` — add 3 recipes of different types, edit one, delete another. Reload — state persists. Open Chrome devtools "responsive" mode at 375×667 (iPhone SE) — tap targets fit, no horizontal scroll.

**Commit:** `feat: recipe management UI`

---

### M5 — Meal Plan (manual): API + UI

**API files:**
- Create: `backend/app/routers/meal_plan.py`
- Extend: `backend/app/schemas.py` — `MealPlanEntryRead` (includes `date`, `slot`, `recipe: RecipeSummary`), `EntryUpsert { recipe_id: int }`, `RecipeSummary { id, name, type }`
- Modify: `backend/app/main.py` — include router at `prefix="/api/meal-plan"`
- Create: `backend/tests/test_meal_plan.py`

Endpoints:
- `GET /api/meal-plan?start=YYYY-MM-DD&end=YYYY-MM-DD`: returns all entries with `start <= date <= end`, each embedding the joined recipe summary. Empty range returns `[]`.
- `PUT /api/meal-plan/{date}/{slot}` body `{recipe_id}`: upserts the entry. Validates `slot in {"lunch","dinner"}`, `recipe_id` exists. Returns the persisted entry with embedded recipe summary.
- `DELETE /api/meal-plan/{date}/{slot}`: deletes the entry if it exists; 204 either way (idempotent).

**Tests:**
1. With no entries, `GET ?start=...&end=...` returns `[]`.
2. `PUT` an entry, then `GET` returns it with the embedded recipe summary.
3. `PUT` the same `(date, slot)` again with a different `recipe_id` — replaces in place (still one row, new recipe).
4. `PUT` with non-existent recipe → 422.
5. `DELETE` removes the entry; `GET` no longer returns it. Re-`DELETE` is still 204.
6. `GET` with a date range crossing a week boundary returns rows from both weeks.

**UI files:**
- Create: `frontend/src/pages/MealPlanPage.tsx`, `frontend/src/components/RecipePicker.tsx`
- Modify: `frontend/src/App.tsx` — route `/plan` (defaults to the current ISO Monday), `/plan/:weekStart`
- Extend: `frontend/src/api.ts` with meal-plan calls and types

Page layout (mobile-first): the view is weekly, but the data is fetched as `GET /api/meal-plan?start=<Mon>&end=<Sun>`. Vertical list of 7 days; each day shows two rows (Lunch / Dinner); each row shows the assigned recipe name or `+ add` for empty slots. Tapping a row opens `RecipePicker` (modal): search field, live-filtered recipe list, plus a "Clear slot" option that `DELETE`s. Picking a recipe `PUT`s and closes. Week navigation: ◀ / ▶ buttons that jump 7 days; the URL updates to `/plan/<new Monday>`. No "create plan" step — every week is plannable by default.

**Verify:** Assign 4 recipes across different days/slots in this week. Clear one. Navigate to next week — it's empty. Back — state intact. Refresh — state persists. Test on phone-sized viewport.

**Commit:** `feat: meal plan with date-keyed entries`

---

### M6 — AI Meal Plan Generation

**Files:**
- Create: `backend/app/services/ai.py`
- Modify: `backend/app/routers/meal_plan.py` — add `POST /api/meal-plan/generate`
- Create: `backend/tests/test_ai_generate.py` (mock the Anthropic client with `monkeypatch`)
- Modify: `frontend/src/pages/MealPlanPage.tsx` — add "Auto-fill empty slots with AI" button (visible if at least one slot in the current week is empty); shows spinner while in flight; on success, refetches the week's entries

`app/services/ai.py`:

```python
from datetime import date
from anthropic import Anthropic
from ..config import settings
from typing import TypedDict

class Assignment(TypedDict):
    date: str          # YYYY-MM-DD as returned by the model
    slot: str
    recipe_id: int

ASSIGN_TOOL = {
    "name": "assign_meals",
    "description": "Assign one recipe_id to each empty slot, optimizing for variety.",
    "input_schema": {
        "type": "object",
        "properties": {
            "assignments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "YYYY-MM-DD"},
                        "slot": {"type": "string", "enum": ["lunch", "dinner"]},
                        "recipe_id": {"type": "integer"},
                    },
                    "required": ["date", "slot", "recipe_id"],
                },
            }
        },
        "required": ["assignments"],
    },
}

SYSTEM = (
    "You plan family meals. Given a list of empty (date, slot) pairs and "
    "available recipes, return one assignment per empty slot. Rules: "
    "(1) only use recipe_id values from the provided recipes; "
    "(2) avoid repeating the same recipe within 2 days; "
    "(3) vary recipe types across consecutive meals; "
    "(4) limit reuse of any recipe within a 7-day window. "
    "Always call the assign_meals tool with one assignment per empty slot."
)

def _client() -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key)

def generate_plan(empty_slots: list[tuple[date, str]], recipes: list[dict]) -> list[Assignment]:
    user_msg = (
        f"Empty slots: {[(d.isoformat(), s) for d, s in empty_slots]}\n\n"
        f"Available recipes (id, name, type): "
        f"{[(r['id'], r['name'], r['type']) for r in recipes]}"
    )
    resp = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        tools=[ASSIGN_TOOL],
        tool_choice={"type": "tool", "name": "assign_meals"},
        messages=[{"role": "user", "content": user_msg}],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "assign_meals":
            return block.input["assignments"]
    return []
```

Router endpoint logic (`POST /api/meal-plan/generate` body `{start, end}`):
1. Compute the full set of `(date, slot)` pairs in the range × `{"lunch","dinner"}`.
2. Subtract the set of already-assigned `(date, slot)` pairs in that range → empty slots.
3. If empty is empty → return the existing entries unchanged.
4. Call `generate_plan(empty_slots, all_recipes)`.
5. For each returned assignment, validate: date parses, falls in `[start, end]`, slot is valid, `(date, slot)` is still empty, `recipe_id` exists. Drop invalid items silently.
6. Upsert the valid assignments. Return the refreshed range.

**Tests (mock the Anthropic client):**
1. With 4 empty slots in the range and 5 recipes, mock returns 4 valid assignments — endpoint upserts all 4.
2. Mock returns an assignment for a `(date, slot)` that's already filled — endpoint ignores it (manual choice preserved).
3. Mock returns a `recipe_id` not in the recipes table — endpoint ignores it.
4. Mock returns a date outside the requested range — endpoint ignores it.
5. With zero empty slots in the range, endpoint returns 200 without calling Anthropic (assert mock not called).

**Verify (live, with real key):** Add 8+ recipes. On `/plan` for the current week, all 14 slots empty. Click "Auto-fill" — slots fill with variety (no recipe used twice within 2 days). Manually set one slot, clear another, click again — only the empty slot is filled, manual choice untouched.

**Commit:** `feat: AI-generated meal plans`

---

### M7 — Shopping List API

**Files:**
- Create: `backend/app/routers/shopping_lists.py`
- Extend: `backend/app/services/ai.py` — `merge_ingredients()`
- Extend: `backend/app/schemas.py` — `ShoppingListRead { id, start_date, end_date, items_by_category }`, `ShoppingListItemRead`, `ShoppingListGenerate { start, end }`, `ItemUpdate { checked }`
- Modify: `backend/app/main.py` — include router
- Create: `backend/tests/test_shopping_lists.py`

`merge_ingredients()` in `ai.py`:

```python
MERGE_TOOL = {
    "name": "build_shopping_list",
    "description": "Consolidate ingredient lines into a deduped, summed, categorized shopping list.",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "category": {"type": "string", "enum":
                            ["produce","meat","dairy","pantry","frozen","bakery","other"]},
                    },
                    "required": ["text", "category"],
                },
            }
        },
        "required": ["items"],
    },
}

MERGE_SYSTEM = (
    "You build grocery shopping lists. Given raw ingredient lines from "
    "multiple recipes (with duplicates), produce a consolidated list. "
    "Rules: (1) sum quantities when the same ingredient appears multiple times "
    "(e.g. '2 cloves garlic' + '3 cloves garlic' -> 'garlic, 5 cloves'); "
    "(2) keep quantities human-readable; "
    "(3) assign each item to one category from the enum; "
    "(4) don't invent items the user didn't list. "
    "Always call build_shopping_list."
)

def merge_ingredients(ingredient_lines: list[str]) -> list[dict]:
    resp = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[{"type": "text", "text": MERGE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        tools=[MERGE_TOOL],
        tool_choice={"type": "tool", "name": "build_shopping_list"},
        messages=[{"role": "user", "content":
            "Raw ingredient lines:\n" + "\n".join(f"- {line}" for line in ingredient_lines)}],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "build_shopping_list":
            return block.input["items"]
    return []
```

Endpoints:
- `POST /api/shopping-lists` body `{start, end}`: load every `MealPlanEntry` in `[start, end]`; collect every ingredient line from every referenced recipe (duplicates intentional — Claude needs them to total); call `merge_ingredients`. If a `ShoppingList` already exists for `(start, end)`, delete its items and reuse the row (preserves the URL); otherwise insert a new one. Insert items with `checked=false`. Return the list.
- `GET /api/shopping-lists?start=YYYY-MM-DD&end=YYYY-MM-DD`: return the list for that exact range with items grouped server-side into `{category: [items]}`. 404 if no list exists for that range.
- `PATCH /api/shopping-list-items/{id}` body `{checked: bool}`: toggle and return the updated item.

**Tests (mock Anthropic):**
1. Range with 3 assigned entries (recipes that share ingredients) — endpoint passes every line (with duplicates) to the mock, persists returned items in the right shape.
2. Regenerating for the same range wipes prior items and resets checks (no orphans, same `shopping_list.id`).
3. `GET` returns items grouped by category in the documented category order.
4. `PATCH` toggles `checked` and persists.
5. `GET` for a range with no list → 404.
6. Generating for a range with no meal-plan entries → empty list (mock not called).

**Verify (live):** Plan a week with 4–5 recipes sharing ingredients (garlic, onion, oil). Generate list — ingredients merged with summed quantities and reasonable categories. Toggle items, reload — checks persist. Regenerate — checks reset.

**Commit:** `feat: AI-merged shopping list with check-off state`

---

### M8 — Shopping List UI + PWA Polish

**Files:**
- Create: `frontend/src/pages/ShoppingListPage.tsx`
- Modify: `frontend/src/pages/MealPlanPage.tsx` — add "Shopping list" button at top of page; routes to `/plan/:weekStart/shopping`. The frontend calls `GET /api/shopping-lists?start=<Mon>&end=<Sun>` to detect existence: if 404, button label is "Generate shopping list" and triggers `POST /api/shopping-lists`; if 200, label is "View shopping list" and navigates. A "Regenerate" link with confirmation lives on the list page itself.
- Modify: `frontend/src/App.tsx` — add `/plan/:weekStart/shopping` route
- Extend: `frontend/src/api.ts` — `getShoppingList`, `generateShoppingList`, `toggleShoppingItem`
- Modify: `frontend/vite.config.ts` — configure `vite-plugin-pwa`:

```ts
VitePWA({
  registerType: 'autoUpdate',
  manifest: {
    name: 'Mealpad',
    short_name: 'Mealpad',
    description: 'Family meal planning',
    theme_color: '#2e7d32',
    background_color: '#ffffff',
    display: 'standalone',
    start_url: '/plan',
    icons: [
      { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
    ],
  },
})
```

- Create: `frontend/public/icon-192.png`, `frontend/public/icon-512.png` (any solid-color placeholder works; README notes how to replace)

UI: items grouped by category in this order — produce, meat, dairy, bakery, frozen, pantry, other. Each item is a large row: checkbox on the left, text on the right; tapping anywhere on the row toggles. Checked items get a strikethrough and lower opacity but stay in place (so the shopper can see what they've already picked up). "Regenerate" button at the bottom with a confirm dialog warning that checks will reset.

**Verify (end-to-end on a phone):**
1. `make build` (builds frontend into `frontend/dist`).
2. `make serve` (runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`).
3. From phone on same wifi, visit `http://<host>:8000`.
4. "Add to home screen" — confirm the manifest is detected.
5. Open from home screen — full-screen PWA, no browser chrome.
6. Walk through entire flow: add a recipe, plan a week, auto-fill, generate shopping list, check items off in a different room.

**Commit:** `feat: shopping list UI + installable PWA`

---

### M9 — README + LAN Deployment Notes

**Files:**
- Modify: `README.md`

Sections:
- **Prereqs:** Python 3.11+, Node 20+, an Anthropic API key.
- **Setup:** `cp backend/.env.example backend/.env` and fill in `ANTHROPIC_API_KEY`; `cd backend && pip install -e .[dev]`; `cd frontend && npm install`.
- **Development:** `make dev-backend` in one terminal, `make dev-frontend` in another; visit `:5173`.
- **Production / LAN deployment:** `make build` then `make serve`; find the host's LAN IP (`ipconfig getifaddr en0` on macOS, `ip addr` on Linux); family devices visit `http://<lan-ip>:8000`.
- **Backups:** the entire app state lives in `backend/data/mealpad.db` — copy that file to back up.
- **Replacing icons:** drop `icon-192.png` and `icon-512.png` into `frontend/public/` and rebuild.

**Commit:** `docs: setup and LAN deployment instructions`

---

## Verification (end-to-end)

Run this walkthrough on a phone (`make build && make serve`, same Wi‑Fi subnet):

1. Open `http://<lan-ip>:8000` → lands on `/plan` for the current week (Chinese UI).
2. Add recipes including at least one **meat**, **veg**, and **soup**.
3. Tap an empty meal → add dishes manually, or use **AI 自动填充空餐次** (3 dishes per empty meal).
4. Tap a meal with dishes → **本餐菜单** modal: replace, delete, or add a 4th dish.
5. **重新生成计划** → confirm → whole week replaced; shopping list for that week removed.
6. **生成购物清单** → merged ingredients by category; check items; reload persists checks.
7. Second device on same LAN sees the same data.

If any step fails, the failure is the bug.

## Out of Scope (do not build without a new SPEC)

- Auth / per-user accounts
- Recipe import from URL or text
- Photo uploads for recipes
- Nutritional info
- Calendar / iCal export
- Grocery store integrations
- Multi-household / multi-tenant
- Configurable AI dishes-per-meal in UI
- English UI (Chinese only today)

Each of these is tempting and each will add weeks. If they're wanted later, write a follow-up SPEC under `docs/superpowers/specs/`.
