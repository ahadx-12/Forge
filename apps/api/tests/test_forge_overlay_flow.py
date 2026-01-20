from __future__ import annotations

import fitz


def test_forge_manifest_overlay_export(client, upload_pdf):
    response = upload_pdf("contract")
    doc_id = response.json()["document"]["doc_id"]

    manifest = client.get(f"/v1/documents/{doc_id}/forge/manifest")
    assert manifest.status_code == 200
    payload = manifest.json()
    assert payload["page_count"] == 1
    first_item = payload["pages"][0]["items"][0]

    overlay_payload = {
        "doc_id": doc_id,
        "page_index": 0,
        "selection": [
            {
                "forge_id": first_item["forge_id"],
                "text": first_item["text"],
                "content_hash": first_item["content_hash"],
                "bbox": first_item["bbox"],
            }
        ],
        "ops": [
            {
                "type": "replace_overlay_text",
                "page_index": 0,
                "forge_id": first_item["forge_id"],
                "old_hash": first_item["content_hash"],
                "new_text": "Forge Pact",
            }
        ],
    }
    commit = client.post(f"/v1/documents/{doc_id}/forge/overlay/commit", json=overlay_payload)
    assert commit.status_code == 200
    commit_payload = commit.json()
    overlay_entries = commit_payload["overlay"]
    assert any(entry["text"] == "Forge Pact" for entry in overlay_entries)
    masks = commit_payload["masks"]
    assert masks
    mask_bbox = masks[0]["bbox_px"]
    expected_bbox = [
        first_item["bbox"][0] - 2,
        first_item["bbox"][1] - 2,
        first_item["bbox"][2] + 2,
        first_item["bbox"][3] + 2,
    ]
    assert mask_bbox == expected_bbox

    overlay = client.get(f"/v1/documents/{doc_id}/forge/overlay?page_index=0")
    assert overlay.status_code == 200
    assert any(entry["text"] == "Forge Pact" for entry in overlay.json()["overlay"])

    export = client.post(f"/v1/export/{doc_id}")
    assert export.status_code == 200
    exported_doc = fitz.open(stream=export.content, filetype="pdf")
    extracted = exported_doc[0].get_text()
    exported_doc.close()
    assert "Forge Pact" in extracted
