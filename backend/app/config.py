from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ai_provider: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.5"
    db_path: str = str(Path(__file__).resolve().parent.parent / "data" / "mealpad.db")

    model_config = {"env_file": ".env"}


settings = Settings()
