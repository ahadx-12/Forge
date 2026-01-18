from __future__ import annotations

import fitz

from forge_api.schemas.patch import PatchCommitRequest, PatchsetInput


def test_export_pdf_overlay(client, upload_pdf):
    response = upload_pdf("drawing")
    doc_id = response.json()["document"]["doc_id"]

    base_ir = client.get(f"/v1/ir/{doc_id}?page=0")
    path_item = next(item for item in base_ir.json()["primitives"] if item["kind"] == "path")

    payload = PatchCommitRequest(
        doc_id=doc_id,
        patchset=PatchsetInput(
            page_index=0,
            ops=[
                {
                    "op": "set_style",
                    "target_id": path_item["id"],
                    "stroke_color": [0, 0, 1],
                    "stroke_width_pt": 3.0,
                }
            ],
            selected_ids=[path_item["id"]],
        ),
    )
    commit = client.post("/v1/patch/commit", json=payload.model_dump(mode="json"))
    assert commit.status_code == 200

    original = client.get(f"/v1/documents/{doc_id}/download")
    export = client.post(f"/v1/export/{doc_id}")

    assert export.status_code == 200
    assert export.content[:4] == b"%PDF"
    assert len(export.content) > len(original.content)

    exported_doc = fitz.open(stream=export.content, filetype="pdf")
    original_doc = fitz.open(stream=original.content, filetype="pdf")
    assert exported_doc.page_count == original_doc.page_count
    exported_doc.close()
    original_doc.close()
