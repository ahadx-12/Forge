from __future__ import annotations

from forge_api.schemas.patch import PatchCommitRequest, PatchsetInput


def test_patch_apply_composite_ir(client, upload_pdf):
    response = upload_pdf("drawing")
    doc_id = response.json()["document"]["doc_id"]

    base_ir = client.get(f"/v1/ir/{doc_id}?page=0")
    assert base_ir.status_code == 200
    base_payload = base_ir.json()
    path_item = next(item for item in base_payload["primitives"] if item["kind"] == "path")

    payload = PatchCommitRequest(
        doc_id=doc_id,
        patchset=PatchsetInput(
            page_index=0,
            ops=[
                {
                    "op": "set_style",
                    "target_id": path_item["id"],
                    "stroke_color": [1, 0, 0],
                    "stroke_width_pt": 4.0,
                }
            ],
            selected_ids=[path_item["id"]],
        ),
    )

    commit = client.post("/v1/patch/commit", json=payload.model_dump(mode="json"))
    assert commit.status_code == 200

    composite = client.get(f"/v1/composite/ir/{doc_id}?page=0")
    assert composite.status_code == 200
    composite_payload = composite.json()
    patched_item = next(item for item in composite_payload["primitives"] if item["id"] == path_item["id"])

    assert patched_item["style"]["stroke_color"] == [1, 0, 0]
    assert patched_item["style"]["stroke_width"] == 4.0
    assert patched_item["bbox"] == path_item["bbox"]
    assert patched_item["id"] == path_item["id"]
