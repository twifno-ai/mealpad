import os

os.environ["MEALPAD_TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session

from app import models  # noqa: F401
from app.db import engine, get_session
from app.main import app


@pytest.fixture(autouse=True)
def reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


@pytest.fixture(name="session")
def session_fixture():
    with Session(engine) as session:
        yield session


@pytest.fixture(name="upload_root")
def upload_root_fixture(tmp_path, monkeypatch):
    root = tmp_path / "uploads"
    root.mkdir()
    from app.config import settings

    monkeypatch.setattr(settings, "upload_root", str(root))
    return root


@pytest.fixture(name="client")
def client_fixture():
    with TestClient(app) as client:
        yield client
