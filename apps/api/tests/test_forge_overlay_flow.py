from __future__ import annotations

import fitz
import pytest


def test_forge_manifest_overlay_export(client, upload_pdf):
    response = upload_pdf("contract")
    doc_id = response.json()["document"]["doc_id"]

    manifest = client.get(f"/v1/documents/{doc_id}/forge/manifest")
    assert manifest.status_code == 200
    payload = manifest.json()
    assert payload["page_count"] == 1
    first_item = payload["pages"][0]["elements"][0]

    overlay_response = client.get(f"/v1/documents/{doc_id}/forge/overlay?page_index=0")
    assert overlay_response.status_code == 200
    overlay_payload = overlay_response.json()
    overlay_entry = next(
        entry for entry in overlay_payload["overlay"] if entry["element_id"] == first_item["element_id"]
    )
    overlay_version = overlay_payload["overlay_version"]

    overlay_payload = {
        "doc_id": doc_id,
        "page_index": 0,
        "base_overlay_version": overlay_version,
        "selection": [
            {
                "element_id": first_item["element_id"],
                "text": first_item["text"],
                "content_hash": overlay_entry["content_hash"],
                "bbox": first_item["bbox"],
                "element_type": first_item["element_type"],
                "style": first_item["style"],
            }
        ],
        "ops": [
            {
                "type": "replace_element",
                "element_id": first_item["element_id"],
                "old_text": first_item["text"],
                "new_text": "Forge Pact",
            }
        ],
    }
    commit = client.post(f"/v1/documents/{doc_id}/forge/overlay/commit", json=overlay_payload)
    assert commit.status_code == 200
    commit_payload = commit.json()
    assert commit_payload["overlay_version"] == overlay_version + 1
    overlay_entries = commit_payload["overlay"]
    assert any(entry["text"] == "Forge Pact" for entry in overlay_entries)
    masks = commit_payload["masks"]
    assert masks
    mask_bbox = masks[0]["bbox"]
    expected_bbox = [
        max(0, first_item["bbox"][0] - 0.01),
        max(0, first_item["bbox"][1] - 0.01),
        min(1, first_item["bbox"][2] + 0.01),
        min(1, first_item["bbox"][3] + 0.01),
    ]
    assert mask_bbox == pytest.approx(expected_bbox, abs=1e-4)

    overlay = client.get(f"/v1/documents/{doc_id}/forge/overlay?page_index=0")
    assert overlay.status_code == 200
    assert any(entry["text"] == "Forge Pact" for entry in overlay.json()["overlay"])

    export = client.post(f"/v1/export/{doc_id}")
    assert export.status_code == 200
    exported_doc = fitz.open(stream=export.content, filetype="pdf")
    extracted = exported_doc[0].get_text()
    exported_doc.close()
    assert "Forge Pact" in extracted


def test_forge_overlay_commit_conflict_payload(client, upload_pdf):
    response = upload_pdf("contract")
    doc_id = response.json()["document"]["doc_id"]

    manifest = client.get(f"/v1/documents/{doc_id}/forge/manifest").json()
    first_item = manifest["pages"][0]["elements"][0]
    overlay_response = client.get(f"/v1/documents/{doc_id}/forge/overlay?page_index=0").json()
    overlay_entry = next(
        entry for entry in overlay_response["overlay"] if entry["element_id"] == first_item["element_id"]
    )
    overlay_version = overlay_response["overlay_version"]

    commit = client.post(
        f"/v1/documents/{doc_id}/forge/overlay/commit",
        json={
            "doc_id": doc_id,
            "page_index": 0,
            "selection": [
                {
                    "element_id": first_item["element_id"],
                    "text": first_item["text"],
                    "content_hash": "mismatch",
                    "bbox": first_item["bbox"],
                    "element_type": first_item["element_type"],
                    "style": first_item["style"],
                }
            ],
            "base_overlay_version": overlay_version,
            "ops": [
                {
                    "type": "replace_element",
                    "element_id": first_item["element_id"],
                    "old_text": first_item["text"],
                    "new_text": "Forge Pact",
                }
            ],
        },
    )
    assert commit.status_code == 409
    payload = commit.json()
    assert payload["error"] == "PATCH_CONFLICT"
    assert payload["details"]["resolved_element_id"] == first_item["element_id"]
    assert payload["details"]["current_content_hash"] == overlay_entry["content_hash"]
    assert payload["details"]["expected_content_hash"] == "mismatch"
    assert payload["details"]["current_entry"]["element_id"] == first_item["element_id"]
    assert payload["details"]["retry_hint"] == "refresh_overlay"
