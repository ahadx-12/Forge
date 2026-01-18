from __future__ import annotations

from fastapi.testclient import TestClient

from tests.pdf_factory import make_colored_bg_pdf_bytes


def test_export_auto_bg_mask_mode(client: TestClient) -> None:
    upload = client.post(
        "/v1/documents/upload",
        files={"file": ("colored.pdf", make_colored_bg_pdf_bytes(), "application/pdf")},
    )
    assert upload.status_code == 200
    doc_id = upload.json()["document"]["doc_id"]

    ir_response = client.get(f"/v1/ir/{doc_id}?page=0")
    assert ir_response.status_code == 200
    ir_payload = ir_response.json()
    text_primitive = next(
        primitive for primitive in ir_payload["primitives"] if primitive["kind"] == "text"
    )

    patch_payload = {
        "doc_id": doc_id,
        "patchset": {
            "ops": [
                {
                    "op": "replace_text",
                    "target_id": text_primitive["id"],
                    "new_text": "Edited text",
                    "policy": "FIT_IN_BOX",
                }
            ],
            "page_index": 0,
            "selected_ids": [text_primitive["id"]],
            "rationale_short": "Export mask test",
        },
    }
    commit = client.post("/v1/patch/commit", json=patch_payload)
    assert commit.status_code == 200

    export = client.post(f"/v1/export/{doc_id}?mask_mode=AUTO_BG")
    assert export.status_code == 200
    assert export.headers.get("X-Forge-Mask-Mode") == "AUTO_BG"
    assert export.content.startswith(b"%PDF")
