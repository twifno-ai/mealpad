# Mealpad — Product Spec

Family-oriented meal planning and recipe management for the home LAN: save recipes, plan meals by week/day, use AI to fill or regenerate plans, and generate shopping lists from the schedule — reducing repetitive decisions and preventing missed ingredients.

## Core capabilities (v1 + post-v1)

1. **Mobile PWA** — React app served from the same FastAPI origin; installable on phones/tablets on the local network.
2. **Recipes** — Manual entry: name, description, type (`soup`, `meat`, `veg`, `noodle`, `rice`, `salad`, `other`), free-text ingredients (one string per line).
3. **Meal plan** — Per-date lunch/dinner; each meal can hold **multiple dishes** (several recipes per slot). Manual add/replace/remove per dish; clear whole meal.
4. **AI meal planning** — Fill empty meals (3 dishes each: meat + veg + soup) or **regenerate** an entire week (replaces all dishes; deletes that week's shopping list). Does not overwrite meals that already have at least one dish when using fill-only.
5. **Shopping list** — AI merges ingredients across all planned recipes for a date range; check off items; regenerate list (resets checks).
6. **UI language** — Simplified Chinese throughout the frontend.
7. **AI providers** — Anthropic Claude or OpenAI (ChatGPT API), configured in `backend/.env` only (no UI). Auto-detect: Anthropic key preferred if both set.

## Users & deployment

- **Users:** One household on a trusted LAN; no login.
- **Server:** One machine runs `make serve` (`0.0.0.0:8000`); family devices use `http://<host-lan-ip>:8000`.
- **Data:** Single SQLite file `backend/data/mealpad.db` (backup = copy file).

## Meal plan model

- No `MealPlan` week entity. Plan = all `MealPlanEntry` rows in a date range.
- **Meal** = `(date, slot)` where `slot` is `lunch` or `dinner`.
- **Dishes** = one or more entries per meal (`recipe_id` + `sort_order`). Unique per `(date, slot, recipe_id)`.
- **Empty meal** = no entries for that `(date, slot)`.
- AI fill targets **empty meals only** and adds **three** recipes (one `meat`, one `veg`, one `soup`) when the recipe library includes all three types.
- **Regenerate** clears all entries in the range, re-runs AI for every meal in the range (3 dishes each), and removes the shopping list for that `(start_date, end_date)`.

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
- Photos, nutrition, calendar export, grocery delivery
- Configurable dishes-per-meal or per-meal type rules in UI
- English UI (Chinese only for now)

## Related docs

| Doc | Purpose |
|---|---|
| [PLAN.md](PLAN.md) | Original milestone plan + current architecture reference |
| [README.md](README.md) | Setup, LAN access, tests |
| [CLAUDE.md](CLAUDE.md) | Agent/convention guide |
| [docs/superpowers/specs/](docs/superpowers/specs/) | Design specs for post-v1 features |
