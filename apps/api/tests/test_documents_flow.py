from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient

from tests.pdf_factory import make_contract_pdf_bytes


def test_upload_metadata_download(client: TestClient) -> None:
    pdf_bytes = make_contract_pdf_bytes()
    response = client.post(
        "/v1/documents/upload",
        files={"file": ("sample_contract.pdf", BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 200
    payload = response.json()
    doc_id = payload["doc_id"]

    meta_response = client.get(f"/v1/documents/{doc_id}")
    assert meta_response.status_code == 200
    meta = meta_response.json()
    assert meta["filename"] == "sample_contract.pdf"

    download_response = client.get(f"/v1/documents/{doc_id}/download")
    assert download_response.status_code == 200
    assert download_response.content.startswith(b"%PDF")
