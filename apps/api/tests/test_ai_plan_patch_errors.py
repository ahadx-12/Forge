from __future__ import annotations

from forge_api.core.patch.selection import compute_content_hash
from forge_api.services import ai_patch_planner
from forge_api.settings import get_settings


def _selection_from_item(item: dict) -> dict:
    return {
        "element_id": item["id"],
        "page_index": 0,
        "bbox": item["bbox"],
        "text": item.get("text"),
        "font_name": item.get("style", {}).get("font"),
        "font_size": item.get("style", {}).get("size"),
        "parent_id": None,
    }


def test_plan_patch_missing_openai_key(monkeypatch, client, upload_pdf):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    response = upload_pdf("drawing")
    doc_id = response.json()["document"]["doc_id"]
    base_ir = client.get(f"/v1/ir/{doc_id}?page=0").json()
    target = next(item for item in base_ir["primitives"] if item["kind"] == "path")

    payload = {
        "doc_id": doc_id,
        "page_index": 0,
        "selected_ids": [target["id"]],
        "user_instruction": "Make it green",
        "selection": _selection_from_item(target),
    }
    response = client.post("/v1/ai/plan_patch", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "ai_not_configured"


def test_ai_flow_plan_and_commit(monkeypatch, client, upload_pdf):
    response = upload_pdf("contract")
    doc_id = response.json()["document"]["doc_id"]

    decode = client.get(f"/v1/decode/{doc_id}")
    assert decode.status_code == 200

    base_ir = client.get(f"/v1/ir/{doc_id}?page=0").json()
    text_item = next(item for item in base_ir["primitives"] if item["kind"] == "text")

    def fake_response_json(system: str, user: str) -> dict:
        return {
            "ops": [
                {
                    "op": "replace_text",
                    "target_id": text_item["id"],
                    "new_text": "AHAD",
                    "policy": "FIT_IN_BOX",
                    "old_text": text_item["text"],
                }
            ],
            "rationale_short": "Update name",
        }

    class FakeClient:
        def response_json(self, system: str, user: str) -> dict:
            return fake_response_json(system, user)

    monkeypatch.setattr(ai_patch_planner, "OpenAIClient", lambda: FakeClient())

    plan_payload = {
        "doc_id": doc_id,
        "page_index": 0,
        "selected_ids": [text_item["id"]],
        "user_instruction": "Change the name to AHAD",
        "selection": _selection_from_item(text_item),
    }
    plan_response = client.post("/v1/ai/plan_patch", json=plan_payload)
    assert plan_response.status_code == 200
    proposed = plan_response.json()["proposed_patchset"]

    commit_response = client.post(
        "/v1/patch/commit",
        json={
            "doc_id": doc_id,
            "allowed_targets": [
                {
                    "element_id": text_item["id"],
                    "page_index": 0,
                    "content_hash": compute_content_hash(text_item["text"]),
                    "bbox": text_item["bbox"],
                    "parent_id": None,
                }
            ],
            "patchset": {
                "ops": proposed["ops"],
                "page_index": proposed["page_index"],
                "selected_ids": [text_item["id"]],
                "rationale_short": proposed["rationale_short"],
            },
        },
    )
    assert commit_response.status_code == 200

    patches_response = client.get(f"/v1/patches/{doc_id}")
    assert patches_response.status_code == 200
    assert len(patches_response.json()["patchsets"]) == 1


def test_ai_plan_patch_invalid_target(monkeypatch, client, upload_pdf):
    response = upload_pdf("drawing")
    doc_id = response.json()["document"]["doc_id"]

    base_ir = client.get(f"/v1/ir/{doc_id}?page=0").json()
    target = next(item for item in base_ir["primitives"] if item["kind"] == "path")

    def fake_response_json(system: str, user: str) -> dict:
        return {
            "ops": [{"op": "set_style", "target_id": "not-real", "stroke_color": [0, 1, 0]}],
            "rationale_short": "Make it green",
        }

    class FakeClient:
        def response_json(self, system: str, user: str) -> dict:
            return fake_response_json(system, user)

    monkeypatch.setattr(ai_patch_planner, "OpenAIClient", lambda: FakeClient())

    payload = {
        "doc_id": doc_id,
        "page_index": 0,
        "selected_ids": [target["id"]],
        "user_instruction": "Make the line green",
        "selection": _selection_from_item(target),
    }
    response = client.post("/v1/ai/plan_patch", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "AI_OUT_OF_SCOPE"
