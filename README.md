# Mealpad

Family-oriented meal planning, recipes, and shopping lists for your home LAN. UI is in **Simplified Chinese**.

## Features

- **Recipes** — CRUD with types and free-text ingredients
- **Weekly meal plan** — Lunch/dinner per day; **multiple dishes per meal** (tap a meal to add, replace, or remove individual recipes)
- **AI fill** — Fills **empty meals** with 3 dishes each (荤 + 素 + 汤); requires meat/veg/soup recipes in the library
- **AI regenerate plan** — Rebuilds the whole week (3 dishes per meal); deletes that week's shopping list
- **Shopping list** — AI-merged ingredients by category, check off while shopping, regenerate list
- **PWA** — Add to home screen from the phone browser

## Prereqs

- Python 3.11+
- Node 20+
- An [Anthropic](https://console.anthropic.com/) and/or [OpenAI](https://platform.openai.com/) API key

## Setup

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — see AI configuration below

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cd ../frontend
npm install
```

### AI configuration (`backend/.env`)

```bash
# Optional: anthropic | openai | (empty = auto-detect, Anthropic first)
AI_PROVIDER=
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.5
```

At least one API key is required for AI fill and shopping-list generation. The app starts without keys; AI actions return a Chinese error in the UI.

## Development

Terminal 1:

```bash
make dev-backend
```

Terminal 2:

```bash
make dev-frontend
```

Open http://localhost:5173 (Vite proxies `/api` to port 8000). Dev servers bind to localhost — **use production mode for phone access** (below).

## Production / LAN (phones & tablets)

```bash
make build
make serve
```

1. Find the server's **LAN IP** (same Wi‑Fi subnet as the phone):
   - macOS: `ipconfig getifaddr en0`
   - Linux: `ip addr`
2. On the phone, open **`http://<lan-ip>:8000`** (use `http`, not `https`).
3. Optional: Safari / Chrome → **Add to Home Screen** for full-screen PWA.

**Troubleshooting**

| Problem | Fix |
|---|---|
| "Couldn't connect" | Use `make serve`, not dev-only backend; phone and Mac must be on the **same subnet** (e.g. both `192.168.x.x`) |
| Page loads but AI fails | Check `.env` keys; read the Chinese error on screen |
| AI fill/regenerate 422 | Add at least one **meat**, **veg**, and **soup** recipe |

## Backups

All app state lives in `backend/data/mealpad.db` — copy that file to back up. On first start after upgrades, the server runs a small SQLite migration automatically.

## Icons

Replace `frontend/public/icon-192.png` and `icon-512.png`, then `make build`.

## Tests

```bash
cd backend && MEALPAD_TESTING=1 .venv/bin/pytest -v
cd frontend && npm test && npm run build
```

## API overview

| Area | Endpoints |
|---|---|
| Recipes | `GET/POST /api/recipes`, `GET/PUT/DELETE /api/recipes/{id}` |
| Meal plan | `GET /api/meal-plan?start&end` |
| Dishes | `POST /api/meal-plan/{date}/{slot}/items`, `PUT/DELETE /api/meal-plan/items/{id}`, `DELETE /api/meal-plan/{date}/{slot}` |
| AI plan | `POST /api/meal-plan/generate` (fill empty meals), `POST /api/meal-plan/regenerate` (full week) |
| Shopping | `GET/POST /api/shopping-lists?start&end`, `PATCH /api/shopping-list-items/{id}` |

See [SPEC.md](SPEC.md) and [PLAN.md](PLAN.md) for full behavior.
