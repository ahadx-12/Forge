from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from forge_api.settings import get_settings


@dataclass
class LocalStorageDriver:
    root: Path

    def ensure_root(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_join(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise ValueError("Invalid storage key")
        return candidate

    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> str:
        path = self._safe_join(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get_path(self, key: str) -> str:
        return str(self._safe_join(key))

    def exists(self, key: str) -> bool:
        return self._safe_join(key).exists()


def get_storage() -> LocalStorageDriver:
    settings = get_settings()
    driver = LocalStorageDriver(Path(settings.FORGE_STORAGE_LOCAL_DIR))
    driver.ensure_root()
    return driver
