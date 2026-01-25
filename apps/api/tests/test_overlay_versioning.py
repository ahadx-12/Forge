from __future__ import annotations


def test_overlay_version_increments_on_commit(client, upload_pdf) -> None:
    response = upload_pdf("contract")
    doc_id = response.json()["document"]["doc_id"]

    overlay_response = client.get(f"/v1/documents/{doc_id}/forge/overlay?page_index=0")
    assert overlay_response.status_code == 200
    overlay_payload = overlay_response.json()
    base_version = overlay_payload["overlay_version"]
    first_entry = overlay_payload["overlay"][0]

    commit = client.post(
        f"/v1/documents/{doc_id}/forge/overlay/commit",
        json={
            "doc_id": doc_id,
            "page_index": 0,
            "base_overlay_version": base_version,
            "selection": [
                {
                    "element_id": first_entry["element_id"],
                    "text": first_entry["text"],
                    "content_hash": first_entry["content_hash"],
                    "bbox": [0.0, 0.0, 1.0, 1.0],
                    "element_type": "text",
                    "style": {"font_family": "Helvetica", "font_size_pt": 12, "color": "#000"},
                }
            ],
            "ops": [
                {
                    "type": "replace_element",
                    "element_id": first_entry["element_id"],
                    "old_text": first_entry["text"],
                    "new_text": "Overlay Updated",
                }
            ],
        },
    )
    assert commit.status_code == 200
    commit_payload = commit.json()
    assert commit_payload["overlay_version"] == base_version + 1

    overlay_response = client.get(f"/v1/documents/{doc_id}/forge/overlay?page_index=0")
    assert overlay_response.status_code == 200
    assert overlay_response.json()["overlay_version"] == base_version + 1


def test_overlay_commit_rejects_stale_version(client, upload_pdf) -> None:
    response = upload_pdf("contract")
    doc_id = response.json()["document"]["doc_id"]

    overlay_response = client.get(f"/v1/documents/{doc_id}/forge/overlay?page_index=0").json()
    base_version = overlay_response["overlay_version"]
    first_entry = overlay_response["overlay"][0]

    commit = client.post(
        f"/v1/documents/{doc_id}/forge/overlay/commit",
        json={
            "doc_id": doc_id,
            "page_index": 0,
            "base_overlay_version": base_version + 1,
            "selection": [
                {
                    "element_id": first_entry["element_id"],
                    "text": first_entry["text"],
                    "content_hash": first_entry["content_hash"],
                    "bbox": [0.0, 0.0, 1.0, 1.0],
                    "element_type": "text",
                    "style": {"font_family": "Helvetica", "font_size_pt": 12, "color": "#000"},
                }
            ],
            "ops": [
                {
                    "type": "replace_element",
                    "element_id": first_entry["element_id"],
                    "old_text": first_entry["text"],
                    "new_text": "Overlay Updated",
                }
            ],
        },
    )
    assert commit.status_code == 409
    payload = commit.json()
    assert payload["error"] == "PATCH_CONFLICT"
    assert payload["details"]["current_overlay_version"] == base_version
