from __future__ import annotations

import os

from fastapi.testclient import TestClient

from forge_api.main import app
from forge_api.settings import get_settings
from forge_api.services import export_html_pdf, export_pdf
from tests.pdf_factory import make_drawing_pdf_bytes


def test_export_get_returns_pdf(client, upload_pdf):
    response = upload_pdf("drawing")
    doc_id = response.json()["document"]["doc_id"]

    export = client.get(f"/v1/export/{doc_id}?mask_mode=AUTO_BG")

    assert export.status_code == 200
    assert "application/pdf" in export.headers.get("content-type", "")
    assert export.headers.get("content-disposition") == f'attachment; filename="{doc_id}.pdf"'
    assert export.content[:4] == b"%PDF"


def test_export_get_returns_503_when_chromium_missing(monkeypatch, tmp_path):
    os.environ["FORGE_STORAGE_LOCAL_DIR"] = str(tmp_path / ".data")
    os.environ["FORGE_RENDER_MODE"] = "html"
    get_settings.cache_clear()
    client = TestClient(app)

    response = client.post(
        "/v1/documents/upload",
        files={"file": ("drawing.pdf", make_drawing_pdf_bytes(), "application/pdf")},
    )
    doc_id = response.json()["document"]["doc_id"]

    monkeypatch.setattr(export_pdf, "_playwright_available", lambda: True)
    monkeypatch.setattr(export_html_pdf, "resolve_chromium_executable", lambda: None)

    export = client.get(f"/v1/export/{doc_id}?mask_mode=AUTO_BG")

    assert export.status_code == 503
    assert export.json()["error"] == "EXPORT_UNAVAILABLE"
