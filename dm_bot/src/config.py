from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    BOT2_TOKEN: str
    SHARED_SECRET: str
    REDIS_URL: str
    TZ: str | None = None

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        extra="ignore",
    )

settings = Settings()
