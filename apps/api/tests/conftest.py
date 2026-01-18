from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from forge_api.main import app
from forge_api.settings import get_settings
from tests.pdf_factory import make_contract_pdf_bytes, make_drawing_pdf_bytes, make_overlap_pdf_bytes


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    os.environ["FORGE_STORAGE_LOCAL_DIR"] = str(tmp_path / ".data")
    get_settings.cache_clear()
    return TestClient(app)


@pytest.fixture()
def upload_pdf(client: TestClient):
    def _upload(kind: str) -> TestClient:
        if kind == "drawing":
            data = make_drawing_pdf_bytes()
            filename = "drawing.pdf"
        elif kind == "contract":
            data = make_contract_pdf_bytes()
            filename = "contract.pdf"
        elif kind == "overlap":
            data = make_overlap_pdf_bytes()
            filename = "overlap.pdf"
        else:
            raise ValueError("Unknown PDF fixture")
        return client.post(
            "/v1/documents/upload",
            files={"file": (filename, data, "application/pdf")},
        )

    return _upload
