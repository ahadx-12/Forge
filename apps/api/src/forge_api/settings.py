from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    FORGE_STORAGE_DRIVER: str = "local"
    FORGE_STORAGE_LOCAL_DIR: str = ".data"
    WEB_ORIGIN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
