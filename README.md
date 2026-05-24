# Mealpad

Family-oriented meal planning, recipes, and shopping lists for your home LAN.

## Prereqs

- Python 3.11+
- Node 20+
- An [Anthropic](https://console.anthropic.com/) and/or [OpenAI](https://platform.openai.com/) API key (see `backend/.env.example`)

## Setup

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — set ANTHROPIC_API_KEY and/or OPENAI_API_KEY (optional AI_PROVIDER)

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cd ../frontend
npm install
```

## Development

Terminal 1:

```bash
make dev-backend
```

Terminal 2:

```bash
make dev-frontend
```

Open http://localhost:5173 (Vite proxies `/api` to port 8000).

## Production / LAN

```bash
make build
make serve
```

Find your machine's LAN IP (macOS: `ipconfig getifaddr en0`, Linux: `ip addr`) and visit `http://<lan-ip>:8000` from phones on the same Wi‑Fi. Add to home screen for the PWA.

## Backups

All app state lives in `backend/data/mealpad.db` — copy that file to back up.

## Icons

Replace `frontend/public/icon-192.png` and `icon-512.png`, then `make build`.

## Tests

```bash
cd backend && MEALPAD_TESTING=1 .venv/bin/pytest -v
```
