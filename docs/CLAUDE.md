# Mealpad

Family-oriented meal planning + recipe + shopping-list tool. Single FastAPI server on the household LAN serves both a JSON API and a React PWA from the same origin.

See `SPEC.md` for the goal and `PLAN.md` for the milestone-by-milestone build plan.

## Stack

- **Backend:** Python 3.11+, FastAPI, SQLModel, SQLite. Lives in `backend/`.
- **Frontend:** React + Vite + TypeScript, PWA. Lives in `frontend/`.
- **AI:** Claude (Anthropic) or ChatGPT (OpenAI) — tool use for structured JSON; provider via `AI_PROVIDER` in `backend/.env` (auto-detect: Anthropic first). Server-side only; keys never reach the browser.
- **Auth:** none. Trusted local-network deployment.

## Commands

```
make dev-backend       # uvicorn app.main:app --reload (port 8000)
make dev-frontend      # vite dev server (port 5173, proxies /api → 8000)
make build             # build frontend into frontend/dist
make serve             # run prod server: uvicorn --host 0.0.0.0 --port 8000
cd backend && pytest   # backend tests
```

AI keys live in `backend/.env` (see `backend/.env.example`): `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, optional `AI_PROVIDER` (`anthropic` | `openai` | empty for auto-detect). The DB file is `backend/data/mealpad.db`, gitignored.

## Conventions

- **TDD for backend.** Write the failing test, see it fail, implement, see it pass, commit. See `PLAN.md` for per-milestone test lists.
- **One commit per milestone.** Milestones in `PLAN.md` are sized to be demoable on their own.
- **Auto-commit every change.** After completing a task or logical unit of work, commit immediately — do not ask the user for permission first. Group related edits into one focused commit; do not leave completed work uncommitted.
- **Commit and push together.** Every commit must be pushed to the remote before the task is considered done. After committing, run `git push` (or `git push -u origin <branch>` for a new branch). Do not leave local-only commits unless the user explicitly says not to push.
- **Mobile-first frontend.** Min 44px tap targets. Test at 375×667 (iPhone SE) before claiming a UI task done.
- **Free-text ingredients.** Recipes store ingredients as a JSON array of strings. The shopping list merge is Claude's job — do not introduce a normalized ingredient table.
- **Meal plan is keyed by date, not by a weekly container.** There is no `MealPlan` entity. `MealPlanEntry` rows have `(date, slot, recipe_id)` with a unique constraint on `(date, slot)`. Empty slot = no row. To clear a slot, `DELETE` the entry. The "weekly view" is a UI rendering of a date-range query.
- **Shopping lists are keyed by `(start_date, end_date)`.** Regenerating for the same range updates the existing row in place (same id, items wiped, checks reset).
- **AI calls are server-side only.** The browser never sees API keys. Always use tool use + forced tool choice for guaranteed JSON. Validate model output (recipe IDs exist, slots are still empty, dates are in range) before applying. Misconfigured provider returns HTTP 502 with a Chinese `detail`.
- **Don't overwrite manual choices.** AI fill only touches `(date, slot)` pairs that have no entry at the moment of application.

## Out of scope for v1

No auth, no recipe-import-from-URL, no photos, no nutrition, no calendar export, no grocery delivery integration. Resist scope creep — add to a follow-up SPEC if wanted later.

## Working with this repo

When implementing a milestone from `PLAN.md`:
1. Read the milestone's Files / Tests / Verify sections.
2. Follow TDD for backend work — tests first.
3. Run the milestone's Verify steps before committing.
4. Use the exact commit message listed at the end of the milestone.
5. Commit automatically when the milestone is done — no need to ask.
6. Push the commit to the remote immediately after it succeeds.

For any other code or doc change (bugfix, refactor, config): verify if applicable, commit with a clear message, push — all without asking.

When adding to the AI service (`backend/app/services/ai.py` and `providers/`):
- Default models: `claude-sonnet-4-6` (Anthropic), `gpt-5.5` (OpenAI); override via `ANTHROPIC_MODEL` / `OPENAI_MODEL`.
- Always declare a tool with a strict schema and force tool use for guaranteed JSON.
- Anthropic: mark long system prompts with `cache_control: {"type": "ephemeral"}`.
- Validate every field of model output before trusting it — never apply directly to the DB without checking referential integrity.
