.PHONY: dev-backend dev-frontend build serve test

PYTHON := backend/.venv/bin/python
UVICORN := backend/.venv/bin/uvicorn

dev-backend:
	cd backend && $(UVICORN) app.main:app --reload --port 8000

test:
	cd backend && MEALPAD_TESTING=1 $(PYTHON) -m pytest -v

dev-frontend:
	cd frontend && npm run dev

build:
	cd frontend && npm run build

serve:
	cd backend && $(UVICORN) app.main:app --host 0.0.0.0 --port 8000
