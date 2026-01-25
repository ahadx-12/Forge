from __future__ import annotations

from datetime import datetime, timezone

from forge_api.schemas.patch import OverlayPatchRecord, OverlayPatchReplaceElement
from forge_api.services.forge_overlay import build_overlay_state


def test_replace_element_preserves_style_and_bbox_by_default() -> None:
    manifest = {
        "pages": [
            {
                "page_index": 0,
                "elements": [
                    {
                        "element_id": "el-1",
                        "text": "Original",
                        "bbox": [0.1, 0.2, 0.3, 0.4],
                        "style": {"font_size_pt": 12, "color": "#000", "font_family": "Helvetica"},
                        "element_type": "text",
                    }
                ],
            }
        ]
    }
    op = OverlayPatchReplaceElement(
        type="replace_element",
        element_id="el-1",
        old_text="Original",
        new_text="Updated",
        style_changes={"font_size_pt": 18, "color": "#ff0000"},
    )
    patchsets = [
        OverlayPatchRecord(
            patch_id="patch-1",
            created_at_iso=datetime.now(timezone.utc),
            ops=[op],
        )
    ]

    overlay_state = build_overlay_state(manifest, patchsets)
    entry = overlay_state[0]["primitives"]["el-1"]
    assert entry["bbox"] == [0.1, 0.2, 0.3, 0.4]
    assert entry["style"]["font_size_pt"] == 12
    assert entry["style"]["color"] == "#000"
