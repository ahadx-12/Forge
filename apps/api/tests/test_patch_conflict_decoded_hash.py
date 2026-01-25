from __future__ import annotations


def test_overlay_commit_conflict_with_decoded_hash(client, upload_pdf):
    response = upload_pdf("contract")
    doc_id = response.json()["document"]["doc_id"]

    decoded = client.get(f"/v1/documents/{doc_id}/decoded?v=1").json()
    page = decoded["pages"][0]
    element = next(item for item in page["elements"] if item["kind"] == "text_run")
    overlay_response = client.get(f"/v1/documents/{doc_id}/forge/overlay?page_index=0").json()
    overlay_version = overlay_response["overlay_version"]

    element_style = {
        "font_name": element.get("font_name"),
        "font_size_pt": element.get("font_size_pt"),
        "color": element.get("color"),
    }

    decoded_element = {
        "id": element["id"],
        "kind": element["kind"],
        "bbox_norm": element["bbox_norm"],
        "text": element["text"],
        "font_name": element.get("font_name"),
        "font_size_pt": element.get("font_size_pt"),
        "color": element.get("color"),
        "style": element_style,
        "content_hash": element.get("content_hash"),
    }

    commit = client.post(
        f"/v1/documents/{doc_id}/forge/overlay/commit",
        json={
            "doc_id": doc_id,
            "page_index": 0,
            "selection": [
                {
                    "element_id": element["id"],
                    "text": element["text"],
                    "content_hash": "mismatch",
                    "bbox": element["bbox_norm"],
                    "element_type": "text",
                    "style": element_style,
                }
            ],
            "base_overlay_version": overlay_version,
            "decoded_selection": {
                "page_index": 0,
                "region_bbox_norm": element["bbox_norm"],
                "primary_id": element["id"],
                "elements": [decoded_element],
            },
            "ops": [
                {
                    "type": "replace_element",
                    "element_id": element["id"],
                    "old_text": element["text"],
                    "new_text": "Forge Pact",
                }
            ],
        },
    )
    assert commit.status_code == 409
    payload = commit.json()
    assert payload["error"] == "PATCH_CONFLICT"
    assert payload["details"]["retry_hint"] == "refresh_decoded"
