from __future__ import annotations

def test_manifest_renders_at_2x_zoom(client, upload_pdf):
    response = upload_pdf("contract")
    doc_id = response.json()["document"]["doc_id"]

    manifest = client.get(f"/v1/documents/{doc_id}/forge/manifest")
    assert manifest.status_code == 200
    payload = manifest.json()
    page = payload["pages"][0]

    width_pt = page["width_pt"]
    height_pt = page["height_pt"]
    assert page["width_px"] == int(round(width_pt * 2))
    assert page["height_px"] == int(round(height_pt * 2))
