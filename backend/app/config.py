from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    db_path: str = str(Path(__file__).resolve().parent.parent / "data" / "mealpad.db")

    model_config = {"env_file": ".env"}


settings = Settings()
