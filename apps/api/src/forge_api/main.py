from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forge_api.routers import decode, documents, health
from forge_api.settings import get_settings


logger = logging.getLogger("forge_api")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="FORGE API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(decode.router)

    return app


app = create_app()
