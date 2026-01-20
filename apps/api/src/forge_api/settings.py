from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    FORGE_ENV: str = "development"
    FORGE_STORAGE_DRIVER: str = "local"
    FORGE_PATCH_STORE_DRIVER: Optional[str] = None
    FORGE_STORAGE_LOCAL_DIR: str = ".data"
    FORGE_S3_BUCKET: Optional[str] = None
    FORGE_S3_REGION: Optional[str] = None
    FORGE_S3_ACCESS_KEY: Optional[str] = None
    FORGE_S3_SECRET_KEY: Optional[str] = None
    FORGE_S3_ENDPOINT: Optional[str] = None
    FORGE_S3_PREFIX: Optional[str] = None
    FORGE_MAX_UPLOAD_MB: int = 25
    FORGE_EXPORT_MASK_MODE: str = "AUTO_BG"
    FORGE_EXPORT_MASK_SOLID_COLOR: str = "255,255,255"
    FORGE_BUILD_VERSION: Optional[str] = None
    FORGE_OPENAI_MODEL: Optional[str] = None
    WEB_ORIGIN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: Optional[str] = None

    @model_validator(mode="after")
    def _validate_s3(self) -> "Settings":
        storage_driver = self.FORGE_STORAGE_DRIVER.lower()
        patch_driver = (self.FORGE_PATCH_STORE_DRIVER or self.FORGE_STORAGE_DRIVER).lower()
        if storage_driver == "s3" or patch_driver == "s3":
            missing = [
                name
                for name, value in {
                    "FORGE_S3_BUCKET": self.FORGE_S3_BUCKET,
                    "FORGE_S3_ACCESS_KEY": self.FORGE_S3_ACCESS_KEY,
                    "FORGE_S3_SECRET_KEY": self.FORGE_S3_SECRET_KEY,
                }.items()
                if not value
            ]
            if missing:
                raise ValueError(f"Missing required S3 settings: {', '.join(missing)}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
