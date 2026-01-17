from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    storage_driver: str = Field("local", alias="FORGE_STORAGE_DRIVER")
    storage_local_dir: Path = Field(Path("./.data"), alias="FORGE_STORAGE_LOCAL_DIR")
    web_origin: Optional[str] = Field(default=None, alias="WEB_ORIGIN")
    api_base_url: Optional[str] = Field(default=None, alias="API_BASE_URL")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    def resolved_storage_dir(self) -> Path:
        if self.storage_local_dir.is_absolute():
            return self.storage_local_dir
        return (Path.cwd() / self.storage_local_dir).resolve()

    def allowed_origins(self) -> List[str]:
        if self.web_origin:
            return [origin.strip() for origin in self.web_origin.split(",") if origin.strip()]
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
