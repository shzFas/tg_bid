from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    BOT2_TOKEN: str
    SHARED_SECRET: str
    DATABASE_URL: str
    TZ: str | None = None

    # Каналы по категориям
    CHANNEL_ACCOUNTING_ID: str
    CHANNEL_LAW_ID: str
    CHANNEL_EGOV_ID: str
    
    CATEGORY_ACCOUNTING_NAME: str
    CATEGORY_LAW_NAME: str
    CATEGORY_EGOV_NAME: str

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        extra="ignore",
    )


settings = Settings()


# ----------------------------------------------------
# CATEGORY → CHANNEL_ID
# ----------------------------------------------------

CATEGORY_TO_CHANNEL = {
    "ACCOUNTING": settings.CHANNEL_ACCOUNTING_ID,
    "LAW": settings.CHANNEL_LAW_ID,
    "EGOV": settings.CHANNEL_EGOV_ID,
}

# ----------------------------------------------------
# CATEGORY → HUMAN_READABLE_NAME 
# ----------------------------------------------------

CATEGORY_H = {
    "ACCOUNTING": settings.CATEGORY_ACCOUNTING_NAME,
    "LAW": settings.CATEGORY_LAW_NAME,
    "EGOV": settings.CATEGORY_EGOV_NAME,
}
