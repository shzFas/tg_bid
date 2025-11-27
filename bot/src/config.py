from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    BOT_TOKEN: str
    BOT2_TOKEN: str | None = None

    CHANNEL_ACCOUNTING_ID: int
    CHANNEL_LAW_ID: int
    CHANNEL_EGOV_ID: int
    OPERATOR_CHAT_ID: int
    
    CATEGORY_ACCOUNTING_NAME: str
    CATEGORY_LAW_NAME: str
    CATEGORY_EGOV_NAME: str

    BOT2_USERNAME: str | None = None
    SHARED_SECRET: str | None = None

    DATABASE_URL: str
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

CATEGORY_H = {
    "ACCOUNTING": settings.CATEGORY_ACCOUNTING_NAME,
    "LAW": settings.CATEGORY_LAW_NAME,
    "EGOV": settings.CATEGORY_EGOV_NAME,
}
