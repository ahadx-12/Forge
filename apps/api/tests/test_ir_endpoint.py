from __future__ import annotations

from fastapi.testclient import TestClient

from tests.pdf_factory import make_overlap_pdf_bytes


def test_ir_endpoint_stability(client: TestClient) -> None:
    pdf_bytes = make_overlap_pdf_bytes()
    files = {"file": ("overlap.pdf", pdf_bytes, "application/pdf")}
    response = client.post("/v1/documents/upload", files=files)
    assert response.status_code == 200
    doc_id = response.json()["document"]["doc_id"]

    first = client.get(f"/v1/ir/{doc_id}?page=0")
    assert first.status_code == 200
    second = client.get(f"/v1/ir/{doc_id}?page=0")
    assert second.status_code == 200

    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["doc_id"] == doc_id
    assert first_payload["page_index"] == 0
    assert first_payload["primitives"] == second_payload["primitives"]
    assert [item["id"] for item in first_payload["primitives"]] == [
        item["id"] for item in second_payload["primitives"]
    ]
