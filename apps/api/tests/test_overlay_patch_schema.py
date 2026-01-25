from __future__ import annotations

from forge_api.schemas.patch import OverlayPatchCommitRequest


def test_overlay_patch_commit_accepts_update_style() -> None:
    payload = OverlayPatchCommitRequest.model_validate(
        {
            "doc_id": "doc-123",
            "page_index": 0,
            "base_overlay_version": 0,
            "selection": [
                {
                    "element_id": "path-1",
                    "text": "",
                    "content_hash": "hash",
                    "bbox": [0.1, 0.1, 0.2, 0.2],
                    "element_type": "path",
                    "style": {"stroke_color": "#000000"},
                }
            ],
            "ops": [
                {
                    "type": "update_style",
                    "element_id": "path-1",
                    "kind": "path",
                    "style": {"stroke_color": "#ff0000", "stroke_width_pt": 2},
                }
            ],
        }
    )

    assert payload.ops[0].type == "update_style"
