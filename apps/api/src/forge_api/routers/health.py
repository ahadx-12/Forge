from __future__ import annotations

from fastapi import APIRouter

from forge_api.settings import get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "ok",
        "build_version": settings.FORGE_BUILD_VERSION or "dev",
        "storage_driver": settings.FORGE_STORAGE_DRIVER,
        "patch_store_driver": settings.FORGE_PATCH_STORE_DRIVER or settings.FORGE_STORAGE_DRIVER,
        "openai_configured": bool(settings.OPENAI_API_KEY),
    }
