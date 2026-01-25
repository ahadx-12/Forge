from __future__ import annotations

import logging
import os
import shutil
import subprocess

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
        _check_chromium_version(chromium_path, logger)
        return chromium_path

    message = (
        "Chromium executable not found. "
        "Set PLAYWRIGHT_CHROMIUM_EXECUTABLE or install system chromium."
    )
    logger.warning(message)
    if settings.FORGE_ENV.lower() != "production":
        return None
    return None


def _is_executable(path: str) -> bool:
    return os.path.exists(path) and os.access(path, os.X_OK)


def _check_chromium_version(path: str, logger: logging.Logger) -> None:
    try:
        result = subprocess.run(
            [path, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=1,
        )
        if result.returncode == 0:
            version = (result.stdout or result.stderr).strip()
            if version:
                logger.info("Chromium version check: %s", version)
        else:
            logger.warning("Chromium version check failed for %s", path)
    except Exception as exc:
        logger.warning("Chromium version check failed for %s: %s", path, exc)
