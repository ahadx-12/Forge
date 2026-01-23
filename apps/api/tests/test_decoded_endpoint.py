from __future__ import annotations

from fastapi.testclient import TestClient


def test_decoded_endpoint_returns_payload(client: TestClient, upload_pdf) -> None:
    response = upload_pdf("contract")
    assert response.status_code == 200
    doc_id = response.json()["document"]["doc_id"]

    decoded = client.get(f"/v1/documents/{doc_id}/decoded?v=1")
    assert decoded.status_code == 200

    payload = decoded.json()
    assert payload["doc_id"] == doc_id
    assert payload["version"] == "v1"
    assert payload["type"] == "pdf"
    assert payload["page_count"] == len(payload["pages"])

    cached = client.get(f"/v1/documents/{doc_id}/decoded?v=1")
    assert cached.status_code == 200
