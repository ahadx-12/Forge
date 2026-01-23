from __future__ import annotations

import logging
import os
import shutil

from forge_api.settings import Settings


def resolve_chromium_executable() -> str | None:
    env_candidates = [
        os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
        os.getenv("PLAYWRIGHT_CHROMIUM_PATH"),
        os.getenv("CHROMIUM_PATH"),
    ]
    for candidate in env_candidates:
        if candidate and _is_executable(candidate):
            return candidate

    path_candidates = [
        "/usr/bin/chromium",
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        shutil.which("chrome"),
    ]
    for candidate in path_candidates:
        if candidate and _is_executable(candidate):
            return candidate

    return None


def log_chromium_startup_status(settings: Settings, logger: logging.Logger) -> str | None:
    chromium_path = resolve_chromium_executable()
    if chromium_path:
        logger.info("Chromium executable resolved at %s", chromium_path)
        return chromium_path

    message = (
        "Chromium executable not found. "
        "Set PLAYWRIGHT_CHROMIUM_EXECUTABLE or install system chromium."
    )
    logger.error(message)
    if settings.FORGE_ENV.lower() != "production":
        return None
    return None


def _is_executable(path: str) -> bool:
    return os.path.exists(path) and os.access(path, os.X_OK)
