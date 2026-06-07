import json
import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    min_watch_seconds: int = 30
    execution_mode: Literal["sequential", "parallel"] = "sequential"
    headless: bool = True
    browser_channel: Literal["auto", "chromium", "chrome", "msedge"] = "auto"
    google_drive_file_id: str = ""
    google_service_account_json: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def get_service_account_info(self) -> dict | None:
        raw = self.google_service_account_json.strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            if os.path.isfile(raw):
                with open(raw, encoding="utf-8") as handle:
                    return json.load(handle)
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON must be valid JSON or a file path")


@lru_cache
def get_settings() -> Settings:
    return Settings()
