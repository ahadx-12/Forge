from __future__ import annotations

from forge_api.core.patch.selection import compute_content_hash
from forge_api.schemas.ir import IRPage
from forge_api.services.ir_pdf import _cache_key, _serialize_ir_page
from forge_api.services.storage import get_storage


def test_commit_replace_text_with_font_fallback(client, upload_pdf):
    response = upload_pdf("contract")
    doc_id = response.json()["document"]["doc_id"]

    decode = client.get(f"/v1/decode/{doc_id}")
    assert decode.status_code == 200

    base_ir_payload = client.get(f"/v1/ir/{doc_id}?page=0").json()
    text_item = next(item for item in base_ir_payload["primitives"] if item["kind"] == "text")

    page = IRPage.model_validate(base_ir_payload)
    for primitive in page.primitives:
        if primitive.id == text_item["id"]:
            primitive.style["font"] = "calibri-bold"
            break

    storage = get_storage()
    storage.put_bytes(_cache_key(doc_id, 0), _serialize_ir_page(page))

    commit_response = client.post(
        "/v1/patch/commit",
        json={
            "doc_id": doc_id,
            "allowed_targets": [
                {
                    "element_id": text_item["id"],
                    "page_index": 0,
                    "content_hash": compute_content_hash(text_item.get("text")),
                    "bbox": text_item["bbox"],
                    "parent_id": None,
                }
            ],
            "patchset": {
                "ops": [
                    {
                        "op": "replace_text",
                        "target_id": text_item["id"],
                        "new_text": "Updated",
                        "policy": "FIT_IN_BOX",
                    }
                ],
                "page_index": 0,
                "selected_ids": [text_item["id"]],
            },
        },
    )
    assert commit_response.status_code == 200
    payload = commit_response.json()
    result = next(item for item in payload["patchset"]["results"] if item["target_id"] == text_item["id"])
    assert any(warning["code"] == "font_fallback" for warning in result.get("warnings", []))
