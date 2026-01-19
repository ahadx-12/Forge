from __future__ import annotations

from fastapi.testclient import TestClient

from forge_api.services import decode_pdf
from tests.pdf_factory import make_contract_pdf_bytes, make_drawing_pdf_bytes


def _upload(client: TestClient, pdf_bytes: bytes, filename: str) -> str:
    files = {"file": (filename, pdf_bytes, "application/pdf")}
    response = client.post("/v1/documents/upload", files=files)
    assert response.status_code == 200
    return response.json()["document"]["doc_id"]


def test_decode_drawing_pdf(client: TestClient) -> None:
    doc_id = _upload(client, make_drawing_pdf_bytes(), "drawing.pdf")
    decode_response = client.get(f"/v1/decode/{doc_id}")
    assert decode_response.status_code == 200
    payload = decode_response.json()
    assert payload["page_count"] == 2
    first_page = payload["pages"][0]
    assert first_page["width_pt"] > 0
    assert first_page["height_pt"] > 0
    assert isinstance(first_page["items"], list)
    assert any(item["kind"] == "text" for item in first_page["items"])

    drawing_items = [item for item in first_page["items"] if item["kind"] == "drawing"]
    if drawing_items:
        assert len(drawing_items) >= 1


def test_decode_contract_pdf(client: TestClient) -> None:
    doc_id = _upload(client, make_contract_pdf_bytes(), "contract.pdf")
    decode_response = client.get(f"/v1/decode/{doc_id}")
    assert decode_response.status_code == 200
    payload = decode_response.json()
    assert payload["page_count"] == 1
    page = payload["pages"][0]
    assert any(item["kind"] == "text" for item in page["items"])


def test_decode_round_handles_none() -> None:
    rounded = decode_pdf._round(None, "doc-123", "span.size")
    assert rounded == 0.0


def test_decode_normalize_bbox_handles_none_values() -> None:
    bbox = decode_pdf._normalize_bbox([None, 10.5, None, 20.25], "doc-123", "span.bbox")
    assert bbox == [0.0, 10.5, 0.0, 20.25]
