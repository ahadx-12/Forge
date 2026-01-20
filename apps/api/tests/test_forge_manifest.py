from __future__ import annotations

from forge_api.services.forge_manifest import _merge_line_spans


def test_manifest_renders_at_2x_zoom(client, upload_pdf):
    response = upload_pdf("contract")
    doc_id = response.json()["document"]["doc_id"]

    manifest = client.get(f"/v1/documents/{doc_id}/forge/manifest")
    assert manifest.status_code == 200
    payload = manifest.json()
    page = payload["pages"][0]

    width_pt = page["width_pt"]
    height_pt = page["height_pt"]
    assert page["scale"] == 2.0
    assert page["width_px"] == int(round(width_pt * 2))
    assert page["height_px"] == int(round(height_pt * 2))


def test_span_merging_does_not_create_overlapping_boxes():
    spans = [
        {"text": "H", "bbox": [10.0, 20.0, 15.0, 30.0], "font": "Arial", "size": 10.0, "color": "#000000"},
        {"text": "E", "bbox": [15.0, 20.0, 20.0, 30.0], "font": "Arial", "size": 10.0, "color": "#000000"},
        {"text": "L", "bbox": [20.0, 20.0, 25.0, 30.0], "font": "Arial", "size": 10.0, "color": "#000000"},
        {"text": "L", "bbox": [25.0, 20.0, 30.0, 30.0], "font": "Arial", "size": 10.0, "color": "#000000"},
        {"text": "O", "bbox": [30.0, 20.0, 35.0, 30.0], "font": "Arial", "size": 10.0, "color": "#000000"},
        {"text": "W", "bbox": [40.0, 20.0, 47.0, 30.0], "font": "Arial", "size": 10.0, "color": "#000000"},
        {"text": "O", "bbox": [47.0, 20.0, 54.0, 30.0], "font": "Arial", "size": 10.0, "color": "#000000"},
        {"text": "R", "bbox": [54.0, 20.0, 60.0, 30.0], "font": "Arial", "size": 10.0, "color": "#000000"},
        {"text": "L", "bbox": [60.0, 20.0, 65.0, 30.0], "font": "Arial", "size": 10.0, "color": "#000000"},
        {"text": "D", "bbox": [65.0, 20.0, 72.0, 30.0], "font": "Arial", "size": 10.0, "color": "#000000"},
    ]

    merged = _merge_line_spans(spans)

    assert len(merged) == 2
    assert merged[0]["text"] == "HELLO"
    assert merged[1]["text"] == "WORLD"

    for idx in range(len(merged) - 1):
        current_right = merged[idx]["bbox"][2]
        next_left = merged[idx + 1]["bbox"][0]
        assert next_left >= current_right
