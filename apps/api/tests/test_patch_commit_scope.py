from __future__ import annotations

from forge_api.core.patch.selection import compute_content_hash


def test_commit_patch_out_of_scope(client, upload_pdf):
    response = upload_pdf("drawing")
    doc_id = response.json()["document"]["doc_id"]
    base_ir = client.get(f"/v1/ir/{doc_id}?page=0").json()
    path_item = next(item for item in base_ir["primitives"] if item["kind"] == "path")
    text_item = next(item for item in base_ir["primitives"] if item["kind"] == "text")

    commit_response = client.post(
        "/v1/patch/commit",
        json={
            "doc_id": doc_id,
            "allowed_targets": [
                {
                    "element_id": path_item["id"],
                    "page_index": 0,
                    "content_hash": "",
                    "bbox": path_item["bbox"],
                    "parent_id": None,
                }
            ],
            "patchset": {
                "ops": [
                    {
                        "op": "replace_text",
                        "target_id": text_item["id"],
                        "new_text": "Scoped",
                        "policy": "FIT_IN_BOX",
                    }
                ],
                "page_index": 0,
                "selected_ids": [path_item["id"]],
            },
        },
    )
    assert commit_response.status_code == 409
    payload = commit_response.json()
    assert payload["error"] == "PATCH_OUT_OF_SCOPE"


def test_commit_patch_missing_target_id(client, upload_pdf):
    response = upload_pdf("drawing")
    doc_id = response.json()["document"]["doc_id"]

    commit_response = client.post(
        "/v1/patch/commit",
        json={
            "doc_id": doc_id,
            "patchset": {
                "ops": [
                    {
                        "op": "replace_text",
                        "target_id": "",
                        "new_text": "Scoped",
                        "policy": "FIT_IN_BOX",
                    }
                ],
                "page_index": 0,
                "selected_ids": [],
            },
        },
    )
    assert commit_response.status_code == 400
    payload = commit_response.json()
    assert payload["error"] in {"invalid_patch_ops", "missing_selection"}


def test_commit_patch_content_conflict(client, upload_pdf):
    response = upload_pdf("contract")
    doc_id = response.json()["document"]["doc_id"]
    base_ir = client.get(f"/v1/ir/{doc_id}?page=0").json()
    text_item = next(item for item in base_ir["primitives"] if item["kind"] == "text")

    commit_response = client.post(
        "/v1/patch/commit",
        json={
            "doc_id": doc_id,
            "allowed_targets": [
                {
                    "element_id": text_item["id"],
                    "page_index": 0,
                    "content_hash": compute_content_hash("mismatch"),
                    "bbox": text_item["bbox"],
                    "parent_id": None,
                }
            ],
            "patchset": {
                "ops": [
                    {
                        "op": "replace_text",
                        "target_id": text_item["id"],
                        "new_text": "Scoped",
                        "policy": "FIT_IN_BOX",
                    }
                ],
                "page_index": 0,
            },
        },
    )
    assert commit_response.status_code == 409
    payload = commit_response.json()
    assert payload["error"] == "PATCH_CONFLICT"
