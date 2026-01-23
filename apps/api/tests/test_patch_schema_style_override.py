from __future__ import annotations

from pydantic import TypeAdapter

from forge_api.schemas.patch import OverlayPatchOp, OverlayPatchPlan


def test_overlay_patch_op_accepts_style_override() -> None:
    op = TypeAdapter(OverlayPatchOp).validate_python(
        {
            "type": "replace_element",
            "element_id": "el-1",
            "old_text": "Old",
            "new_text": "New",
            "style": {"color": "#ff0000", "font_size_pt": 11.0, "bold": True, "italic": False},
        }
    )
    assert op.style


def test_overlay_patch_op_preserves_legacy_payload() -> None:
    plan = OverlayPatchPlan.model_validate(
        {
            "schema_version": 2,
            "ops": [
                {
                    "type": "replace_element",
                    "element_id": "el-1",
                    "old_text": "Old",
                    "new_text": "New",
                    "style_changes": {"font_size_pt": 12.0},
                }
            ],
        }
    )
    assert plan.ops[0].style_changes
