from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ai_provider: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.5"
    db_path: str = str(Path(__file__).resolve().parent.parent / "data" / "mealpad.db")
    upload_root: str = ""

    model_config = {"env_file": ".env"}

    def resolved_upload_root(self) -> Path:
        if self.upload_root:
            return Path(self.upload_root)
        return Path(self.db_path).parent / "uploads"


settings = Settings()
