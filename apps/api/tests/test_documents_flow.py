from __future__ import annotations

from fastapi.testclient import TestClient

from tests.pdf_factory import make_contract_pdf_bytes


def test_document_upload_and_download(client: TestClient) -> None:
    pdf_bytes = make_contract_pdf_bytes()
    files = {"file": ("contract.pdf", pdf_bytes, "application/pdf")}
    response = client.post("/v1/documents/upload", files=files)
    assert response.status_code == 200
    payload = response.json()
    assert "document" in payload
    doc_id = payload["document"]["doc_id"]

    meta_response = client.get(f"/v1/documents/{doc_id}")
    assert meta_response.status_code == 200
    meta = meta_response.json()
    assert meta["doc_id"] == doc_id
    assert meta["filename"] == "contract.pdf"

    download_response = client.get(f"/v1/documents/{doc_id}/download")
    assert download_response.status_code == 200
    assert download_response.content.startswith(b"%PDF")
    assert download_response.headers["content-type"].startswith("application/pdf")
    assert "inline" in download_response.headers.get("content-disposition", "")

    range_response = client.get(
        f"/v1/documents/{doc_id}/download", headers={"Range": "bytes=0-9"}
    )
    assert range_response.status_code == 206
    assert range_response.headers["content-type"].startswith("application/pdf")
    assert range_response.headers["content-range"].startswith("bytes 0-9/")
    assert len(range_response.content) == 10


def test_document_upload_and_decode(client: TestClient) -> None:
    pdf_bytes = make_contract_pdf_bytes()
    files = {"file": ("contract.pdf", pdf_bytes, "application/pdf")}
    response = client.post("/v1/documents/upload", files=files)
    assert response.status_code == 200
    doc_id = response.json()["document"]["doc_id"]

    decode_response = client.get(f"/v1/decode/{doc_id}")
    assert decode_response.status_code == 200
    payload = decode_response.json()
    assert payload["doc_id"] == doc_id
    assert payload["page_count"] >= 1
