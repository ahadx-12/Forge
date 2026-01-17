from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient

from tests.pdf_factory import make_drawing_pdf_bytes


def test_decode_endpoint(client: TestClient) -> None:
    pdf_bytes = make_drawing_pdf_bytes()
    response = client.post(
        "/v1/documents/upload",
        files={"file": ("sample_drawing.pdf", BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 200
    doc_id = response.json()["doc_id"]

    decode_response = client.get(f"/v1/decode/{doc_id}")
    assert decode_response.status_code == 200
    payload = decode_response.json()
    assert payload["page_count"] == 2
    assert payload["pages"][0]["width_pt"]
    assert payload["pages"][0]["height_pt"]
    assert isinstance(payload["pages"][0]["items"], list)
    kinds = {item.get("kind") for page in payload["pages"] for item in page.get("items", [])}
    assert "text" in kinds
    if "path" in kinds:
        path_count = sum(
            1 for page in payload["pages"] for item in page.get("items", []) if item.get("kind") == "path"
        )
        assert path_count >= 1
