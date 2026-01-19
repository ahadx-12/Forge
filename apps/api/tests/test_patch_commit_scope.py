from __future__ import annotations


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
    assert commit_response.status_code == 400
    payload = commit_response.json()
    assert payload["error"] == "patch_out_of_scope"


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
