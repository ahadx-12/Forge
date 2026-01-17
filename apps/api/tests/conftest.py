from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from forge_api.main import create_app
from forge_api.settings import get_settings


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FORGE_STORAGE_LOCAL_DIR", str(tmp_path))
    get_settings.cache_clear()
    app = create_app()
    return TestClient(app)
