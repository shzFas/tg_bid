from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    BOT_TOKEN: str
    CHANNEL_ACCOUNTING_ID: int
    CHANNEL_LAW_ID: int
    CHANNEL_EGOV_ID: int
    OPERATOR_CHAT_ID: int
    TZ: str | None = None

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        extra="ignore",
    )

settings = Settings()

CATEGORY_TO_CHANNEL = {
    "ACCOUNTING": settings.CHANNEL_ACCOUNTING_ID,
    "LAW": settings.CHANNEL_LAW_ID,
    "EGOV": settings.CHANNEL_EGOV_ID,
}
