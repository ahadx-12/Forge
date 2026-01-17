from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Protocol

from forge_api.settings import get_settings


logger = logging.getLogger("forge_api.storage")


class StorageDriver(Protocol):
    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> str:
        ...

    def open_stream(self, key: str) -> BinaryIO:
        ...

    def get_path(self, key: str) -> Path:
        ...

    def exists(self, key: str) -> bool:
        ...


class LocalStorageDriver:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_key(self, key: str) -> Path:
        if key.startswith("/"):
            key = key[1:]
        pure = PurePosixPath(key)
        if any(part in {"..", "."} for part in pure.parts):
            raise ValueError("Invalid storage key")
        return self.base_dir / Path(*pure.parts)

    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> str:
        path = self._sanitize_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            handle.write(data)
        return key

    def open_stream(self, key: str) -> BinaryIO:
        path = self._sanitize_key(key)
        return path.open("rb")

    def get_path(self, key: str) -> Path:
        return self._sanitize_key(key)

    def exists(self, key: str) -> bool:
        path = self._sanitize_key(key)
        return path.exists()


def get_storage_driver() -> StorageDriver:
    settings = get_settings()
    if settings.storage_driver != "local":
        logger.warning("Unsupported storage driver %s, falling back to local", settings.storage_driver)
    return LocalStorageDriver(settings.resolved_storage_dir())
