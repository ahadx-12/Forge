from __future__ import annotations

from forge_api.services import ai_patch_planner


def test_ai_plan_patch_schema(monkeypatch, client, upload_pdf):
    response = upload_pdf("drawing")
    doc_id = response.json()["document"]["doc_id"]

    base_ir = client.get(f"/v1/ir/{doc_id}?page=0").json()
    target = next(item for item in base_ir["primitives"] if item["kind"] == "path")

    def fake_response_json(system: str, user: str) -> dict:
        return {
            "ops": [{"op": "set_style", "target_id": target["id"], "stroke_color": [0, 1, 0]}],
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
        "selection": {
            "element_id": target["id"],
            "page_index": 0,
            "bbox": target["bbox"],
            "text": target.get("text"),
            "font_name": target.get("style", {}).get("font"),
            "font_size": target.get("style", {}).get("size"),
            "parent_id": None,
        },
    }
    response = client.post("/v1/ai/plan_patch", json=payload)
    assert response.status_code == 200
    data = response.json()["proposed_patchset"]
    assert data["schema_version"] == "v1"
    assert data["ops"][0]["target_id"] == target["id"]
    assert data["page_index"] == 0
