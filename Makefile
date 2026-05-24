.PHONY: dev-backend dev-frontend build serve test setup-backend seed-recipes seed-japanese-recipes seed-french-recipes seed-spanish-recipes seed-italian-recipes seed-american-recipes

VENV := backend/.venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

setup-backend: $(VENV)/bin/uvicorn

$(VENV)/bin/uvicorn:
	python3 -m venv $(VENV)
	$(PIP) install -e "backend/.[dev]"

dev-backend: setup-backend
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

test: setup-backend
	cd backend && MEALPAD_TESTING=1 .venv/bin/python -m pytest -v

dev-frontend:
	cd frontend && npm run dev

build:
	cd frontend && npm run build

serve: setup-backend
	cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

seed-recipes: setup-backend
	cd backend && .venv/bin/python scripts/import_classic_recipes.py

seed-japanese-recipes: setup-backend
	cd backend && .venv/bin/python scripts/import_japanese_recipes.py

seed-french-recipes: setup-backend
	cd backend && .venv/bin/python scripts/import_french_recipes.py

seed-spanish-recipes: setup-backend
	cd backend && .venv/bin/python scripts/import_spanish_recipes.py

seed-italian-recipes: setup-backend
	cd backend && .venv/bin/python scripts/import_italian_recipes.py

seed-american-recipes: setup-backend
	cd backend && .venv/bin/python scripts/import_american_recipes.py
