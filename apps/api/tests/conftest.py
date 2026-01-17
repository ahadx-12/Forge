from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from forge_api.main import app
from forge_api.settings import get_settings


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    os.environ["FORGE_STORAGE_LOCAL_DIR"] = str(tmp_path / ".data")
    get_settings.cache_clear()
    return TestClient(app)
