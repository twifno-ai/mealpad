# Mealpad — Product Spec

Family-oriented meal planning and recipe management for the home LAN: save recipes, plan meals by week/day, use AI to fill or regenerate plans, and generate shopping lists from the schedule — reducing repetitive decisions and preventing missed ingredients.

## Core capabilities (v1 + post-v1)

1. **Mobile PWA** — React app served from the same FastAPI origin; installable on phones/tablets on the local network. **v3:** bottom tab navigation (plan / recipes / journal / shopping), connection health screen, settings page.
2. **Recipes** — Manual entry: name, description, type (`soup`, `meat`, `veg`, `other`), free-text ingredients (one string per line).
3. **Meal plan** — Per-date lunch/dinner; each meal can hold **multiple dishes** (several recipes per slot). Manual add/replace/remove per dish; clear whole meal.
4. **AI meal planning** — Fill empty meals (3 dishes each: meat + veg + soup) or **regenerate** an entire week (replaces all dishes; deletes that week's shopping list). Does not overwrite meals that already have at least one dish when using fill-only.
5. **Shopping list** — AI merges ingredients across all planned recipes for a date range; check off items; regenerate list (resets checks).
6. **UI language** — Simplified Chinese throughout the frontend.
7. **AI providers** — Anthropic Claude or OpenAI (ChatGPT API), configured in `backend/.env` only (no UI). Auto-detect: Anthropic key preferred if both set.
8. **Cooking log** — Mark planned dishes as actually cooked; add off-plan dishes from the recipe library; optional one photo per log.
9. **Recipe covers** — One cover image per recipe (local upload).
10. **Journal page** — Browse weekly cooking history with photos.

## Users & deployment

- **Users:** One household on a trusted LAN; no login.
- **Server:** One machine runs `make serve` (`0.0.0.0:8000`); family devices use `http://<host-lan-ip>:8000`.
- **Data:** `backend/data/` — SQLite (`mealpad.db`) plus uploaded images (`uploads/`). Backup = copy the whole `data/` directory.

## Meal plan model

- No `MealPlan` week entity. Plan = all `MealPlanEntry` rows in a date range.
- **Meal** = `(date, slot)` where `slot` is `lunch` or `dinner`.
- **Dishes** = one or more entries per meal (`recipe_id` + `sort_order`). Unique per `(date, slot, recipe_id)`.
- **Empty meal** = no entries for that `(date, slot)`.
- AI fill targets **empty meals only** and adds **three** recipes (one `meat`, one `veg`, one `soup`) when the recipe library includes all three types.
- **Regenerate** clears all entries in the range, re-runs AI for every meal in the range (3 dishes each), and removes the shopping list for that `(start_date, end_date)`. **Does not delete** cooking log entries (links to plan entries may be cleared).

## Cooking log model (v2)

- **Planned cooked** — One log per `MealPlanEntry` when marked done (`kind=planned`).
- **Extra cooked** — Dishes actually made but not on the plan (`kind=extra`), chosen from the recipe library; unique per `(date, slot, recipe_id)`.
- **Photos** — At most one image per log; stored under `backend/data/uploads/`.
- **Recipe covers** — `RecipeImage` table; v2 allows one `is_cover` row per recipe.

## Shopping list model

- One list per `(start_date, end_date)`.
- Regenerating the list for the same range updates items in place and clears checkmarks.
- Ingredient merge is AI-driven from free-text recipe lines (no normalized ingredient table).

## AI & errors

- All AI calls are server-side with forced tool use for structured JSON.
- Misconfiguration or API failures return **HTTP 502** with a **Chinese** `detail` string shown in the UI.
- Recipe library must include at least one recipe, and for AI fill/regenerate must include **meat, veg, and soup** types.

## Explicitly out of scope

- Auth / multi-user accounts
- Recipe import from URL
- Recipe step photos / multi-image gallery (v2 is cover-only)
- Nutrition, calendar export, grocery delivery
- Configurable dishes-per-meal or per-meal type rules in UI
- English UI (Chinese only for now)

## Related docs

| Doc | Purpose |
|---|---|
| [PLAN.md](PLAN.md) | Original milestone plan + current architecture reference |
| [PLAN-v2.md](PLAN-v2.md) | v2 milestones (cooking log + images) |
| [PLAN-v3-pwa.md](PLAN-v3-pwa.md) | v3 PWA mobile shell (tabs + connection UX) |
| [README.md](../README.md) | Setup, LAN access, tests |
| [CLAUDE.md](../CLAUDE.md) | Agent/convention guide |
| [superpowers/specs/](superpowers/specs/) | Design specs for post-v1 features |
