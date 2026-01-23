from __future__ import annotations

from forge_api.routers import ai_overlay


def test_ai_overlay_plan_with_decoded_selection(monkeypatch, client, upload_pdf):
    response = upload_pdf("contract")
    doc_id = response.json()["document"]["doc_id"]

    decoded = client.get(f"/v1/documents/{doc_id}/decoded?v=1")
    assert decoded.status_code == 200
    payload = decoded.json()
    page = payload["pages"][0]
    elements = [element for element in page["elements"] if element["kind"] == "text_run"]
    primary = elements[0]
    secondary = elements[1] if len(elements) > 1 else primary

    captured = {}

    class FakeClient:
        def response_json(self, system: str, user: str) -> dict:
            captured["user"] = user
            return {
                "schema_version": 2,
                "ops": [
                    {
                        "type": "replace_element",
                        "element_id": primary["id"],
                        "old_text": primary["text"],
                        "new_text": "Updated Text",
                    }
                ],
            }

    monkeypatch.setattr(ai_overlay, "OpenAIClient", lambda: FakeClient())

    primary_style = {
        "font_name": primary.get("font_name"),
        "font_size_pt": primary.get("font_size_pt"),
        "color": primary.get("color"),
    }
    secondary_style = {
        "font_name": secondary.get("font_name"),
        "font_size_pt": secondary.get("font_size_pt"),
        "color": secondary.get("color"),
    }

    def as_decoded_selection_element(element, style):
        return {
            "id": element["id"],
            "kind": element["kind"],
            "bbox_norm": element["bbox_norm"],
            "text": element["text"],
            "font_name": element.get("font_name"),
            "font_size_pt": element.get("font_size_pt"),
            "color": element.get("color"),
            "style": style,
            "content_hash": element.get("content_hash"),
        }

    request_payload = {
        "doc_id": doc_id,
        "page_index": 0,
        "selection": [
            {
                "element_id": primary["id"],
                "text": primary["text"],
                "content_hash": primary["content_hash"],
                "bbox": primary["bbox_norm"],
                "element_type": "text",
                "style": primary_style,
            },
            {
                "element_id": secondary["id"],
                "text": secondary["text"],
                "content_hash": secondary["content_hash"],
                "bbox": secondary["bbox_norm"],
                "element_type": "text",
                "style": secondary_style,
            },
        ],
        "user_prompt": "Update the primary label.",
        "decoded_selection": {
            "page_index": 0,
            "region_bbox_norm": primary["bbox_norm"],
            "primary_id": primary["id"],
            "elements": [
                as_decoded_selection_element(primary, primary_style),
                as_decoded_selection_element(secondary, secondary_style),
            ],
        },
    }

    response = client.post("/v1/ai/plan_overlay_patch", json=request_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["ops"][0]["element_id"] == primary["id"]
    assert "PRIMARY ELEMENT" in captured["user"]
