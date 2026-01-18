from __future__ import annotations

import os
from uuid import uuid4

import pytest

from forge_api.services.storage import get_storage
from forge_api.settings import get_settings


def test_s3_storage_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    required = ["FORGE_S3_BUCKET", "FORGE_S3_ACCESS_KEY", "FORGE_S3_SECRET_KEY"]
    if not all(os.getenv(name) for name in required):
        pytest.skip("S3 env not configured")

    monkeypatch.setenv("FORGE_STORAGE_DRIVER", "s3")
    get_settings.cache_clear()
    try:
        storage = get_storage()
        key = f"tests/s3-smoke-{uuid4()}.txt"
        storage.put_bytes(key, b"ok", content_type="text/plain")
        assert storage.exists(key) is True
        assert storage.get_bytes(key) == b"ok"
    finally:
        get_settings.cache_clear()
