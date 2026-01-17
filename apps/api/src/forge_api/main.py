from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forge_api.routers.decode import router as decode_router
from forge_api.routers.documents import router as documents_router
from forge_api.routers.health import router as health_router
from forge_api.settings import get_settings


def _cors_origins() -> list[str]:
    settings = get_settings()
    if settings.WEB_ORIGIN:
        return [origin.strip() for origin in settings.WEB_ORIGIN.split(",") if origin.strip()]
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


app = FastAPI(title="Forge API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(documents_router)
app.include_router(decode_router)
