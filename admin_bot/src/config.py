from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ADMIN_BOT_TOKEN: str
    DATABASE_URL: str
    ADMIN_IDS: str  # Список: "123,456"
    TZ: str | None = None

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
