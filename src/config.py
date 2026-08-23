from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = ""
    feedback_provider: str = "mock"
    gemini_model: str = "gemini-3.5-flash"

    @property
    def uses_gemini(self) -> bool:
        return self.feedback_provider.lower() == "gemini"


def get_settings() -> Settings:
    return Settings()