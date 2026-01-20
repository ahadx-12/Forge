from __future__ import annotations


def test_forge_manifest_bbox_normalized_bounds(client, upload_pdf):
    response = upload_pdf("contract")
    doc_id = response.json()["document"]["doc_id"]

    manifest = client.get(f"/v1/documents/{doc_id}/forge/manifest")
    assert manifest.status_code == 200
    payload = manifest.json()
    page = payload["pages"][0]

    width_px = page["width_px"]
    height_px = page["height_px"]
    assert width_px > 0
    assert height_px > 0

    elements = page["elements"]
    assert len(elements) < 20
    for element in elements:
        x0, y0, x1, y1 = element["bbox"]
        assert 0 <= x0 <= x1 <= 1
        assert 0 <= y0 <= y1 <= 1
