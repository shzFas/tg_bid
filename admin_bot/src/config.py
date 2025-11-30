from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ADMIN_BOT_TOKEN: str
    DM_BOT_TOKEN: str
    DATABASE_URL: str
    ADMIN_IDS: str
    TZ: str | None = None

    CHANNEL_ACCOUNTING_ID: int
    CHANNEL_LAW_ID: int
    CHANNEL_EGOV_ID: int

    DM_BOT_USERNAME: str  # например ZayavkaWorkKzHelperBot

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        extra="ignore",
    )

    @property
    def admin_ids_list(self) -> list[int]:
        return [
            int(x.strip())
            for x in self.ADMIN_IDS.split(",")
            if x.strip().isdigit()
        ]


settings = Settings()

CATEGORY_TO_CHANNEL = {
    "ACCOUNTING": settings.CHANNEL_ACCOUNTING_ID,
    "LAW": settings.CHANNEL_LAW_ID,
    "EGOV": settings.CHANNEL_EGOV_ID,
}
