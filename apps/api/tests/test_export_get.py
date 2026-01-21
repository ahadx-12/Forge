from __future__ import annotations


def test_export_get_returns_pdf(client, upload_pdf):
    response = upload_pdf("drawing")
    doc_id = response.json()["document"]["doc_id"]

    export = client.get(f"/v1/export/{doc_id}?mask_mode=AUTO_BG")

    assert export.status_code == 200
    assert "application/pdf" in export.headers.get("content-type", "")
    assert export.content[:4] == b"%PDF"
