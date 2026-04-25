from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"


class Settings(BaseSettings):
    DATABASE_URL: str
    MISTRAL_API_KEY: str

    model_config = SettingsConfigDict(env_file=str(ENV_PATH), extra="ignore")


settings = Settings()  # type: ignore[call-arg]
