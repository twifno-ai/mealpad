# Mealpad（家餐）Project Constitution

These are immutable principles for this project. If any conflict arises, these rules win.

---

## Data & Privacy

- **Local-First**: All recipe, meal-plan, and shopping-list data is stored locally. No mandatory cloud login or sync. Export/import for backup is allowed; no feature may require an online account to use core flows.
- **No Execution of User Input**: Never execute user-provided content as code or shell commands. Imports (e.g. from file) must parse only declared formats (e.g. JSON); no arbitrary code execution.

---

## Scope (V1)

- **In Scope**: Recipes, meal calendar (assign recipes to dates/meals), auto-generated shopping list from calendar, portion scaling, and “what we ate” history. One primary UI (Web or desktop) plus optional CLI.
- **Out of Scope for V1**: Multi-user accounts, cloud sync, recipe clipper from the web, social sharing, comments, and nutrition/calorie analysis. Do not add these without an explicit scope change.

---

## User Experience

- **Mobile-Friendly**: The UI must be usable on phones: responsive layout, large enough touch targets, minimal steps for core actions (pick recipe, assign to day, tick off shopping item, view history). Key actions should be thumb-friendly or easy one-handed.
- **Clear Hierarchy**: Main functions (recipes, calendar, shopping list, history) must be easy to find and reach in few clicks. Information hierarchy and navigation must stay clear.

---

## Performance & Quality

- **Performance**: Meal calendar and shopping-list generation must complete within 3 seconds for up to 500 recipes and 90 days of calendar data.
- **Core Logic Under Test**: Recipe parsing, calendar aggregation, list generation, and portion scaling must have unit tests; changes to these areas must not drop coverage.

---

## Deliverables

- **LAN Access Docs**: If the product is a Web app, the deliverable must include instructions for multi-device access on the local network (bind address, port, how to find LAN IP, URL for other devices, and basic firewall/router notes).
