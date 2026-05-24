from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import init_db
from .routers import meal_plan, recipes, shopping_lists
from .services import uploads as upload_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    upload_service.upload_root()
    init_db()
    yield


app = FastAPI(title="mealpad", lifespan=lifespan)

app.include_router(recipes.router, prefix="/api/recipes", tags=["recipes"])
app.include_router(meal_plan.router, prefix="/api/meal-plan", tags=["meal-plan"])
app.include_router(shopping_lists.router, prefix="/api/shopping-lists", tags=["shopping-lists"])
app.include_router(
    shopping_lists.items_router,
    prefix="/api/shopping-list-items",
    tags=["shopping-list-items"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


_upload_dir = settings.resolved_upload_root()
_upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_upload_dir), name="uploads")

dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="spa")
