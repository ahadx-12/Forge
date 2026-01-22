from __future__ import annotations

import logging
import os
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from forge_api.core.errors import APIError
from forge_api.core.request_context import get_request_id
from forge_api.routers.ai import router as ai_router
from forge_api.routers.ai_overlay import router as ai_overlay_router
from forge_api.routers.decode import router as decode_router
from forge_api.routers.documents import router as documents_router
from forge_api.routers.export import router as export_router
from forge_api.routers.health import router as health_router
from forge_api.routers.ir import router as ir_router
from forge_api.routers.patches import router as patches_router
from forge_api.routers.forge import router as forge_router
from forge_api.settings import get_settings


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("forge_api")


# -----------------------------------------------------------------------------
# CORS
# -----------------------------------------------------------------------------
def _cors_origins() -> list[str]:
    settings = get_settings()
    if settings.WEB_ORIGIN:
        return [origin.strip() for origin in settings.WEB_ORIGIN.split(",") if origin.strip()]
    if settings.FORGE_ENV.lower() == "production":
        return []
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------
app = FastAPI(title="Forge API", version="1.0.0")


@app.on_event("startup")
def assert_playwright_chromium_installed() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - dependency import logging
        logger.error("Playwright import failed: %s", exc)
        return
    with sync_playwright() as playwright:
        executable_path = playwright.chromium.executable_path
    if not os.path.exists(executable_path):
        logger.error(
            "Playwright chromium executable missing at %s. Run `playwright install --with-deps chromium`.",
            executable_path,
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Global exception handler (CRITICAL FOR DEBUGGING)
# -----------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Ensures ALL 500s print a full traceback to Railway Logs.
    """
    request_id = get_request_id(request)
    logger.error(
        "Unhandled exception on %s %s request_id=%s\n%s",
        request.method,
        request.url.path,
        request_id,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "path": request.url.path,
            "request_id": request_id,
        },
    )


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    request_id = get_request_id(request)
    logger.warning(
        "Handled API error on %s %s request_id=%s code=%s",
        request.method,
        request.url.path,
        request_id,
        exc.code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.code,
            "message": exc.message,
            "details": exc.details,
            "request_id": request_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = get_request_id(request)
    logger.info(
        "Validation error on %s %s request_id=%s",
        request.method,
        request.url.path,
        request_id,
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Invalid request payload",
            "details": exc.errors(),
            "request_id": request_id,
        },
    )


# -----------------------------------------------------------------------------
# Startup logging (confirms env + storage config)
# -----------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    settings = get_settings()
    logger.info("Forge API starting")
    logger.info("FORGE_ENV=%s", settings.FORGE_ENV)
    logger.info("STORAGE_DRIVER=%s", settings.FORGE_STORAGE_DRIVER)
    logger.info("S3_BUCKET=%s", getattr(settings, "FORGE_S3_BUCKET", None))
    logger.info("S3_ENDPOINT=%s", getattr(settings, "FORGE_S3_ENDPOINT", None))


# -----------------------------------------------------------------------------
# Routers
# -----------------------------------------------------------------------------
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(forge_router)
app.include_router(decode_router)
app.include_router(ir_router)
app.include_router(patches_router)
app.include_router(export_router)
app.include_router(ai_router)
app.include_router(ai_overlay_router)
