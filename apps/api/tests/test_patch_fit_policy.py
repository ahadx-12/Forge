from __future__ import annotations

import fitz

from forge_api.core.patch.apply import MAX_BBOX_EXPAND, MIN_FONT_SCALE, apply_ops_to_page
from forge_api.schemas.ir import IRPage, IRPrimitive
from forge_api.schemas.patch import PatchReplaceText


def _make_page(font_size: float, bbox_width: float) -> IRPage:
    primitive = IRPrimitive(
        id="prim-1",
        kind="text",
        bbox=[0.0, 0.0, bbox_width, 20.0],
        z_index=0,
        style={"font": "helv", "size": font_size, "color": 0},
        signature_fields={},
        text="Original",
    )
    return IRPage(
        doc_id="doc-1",
        page_index=0,
        width_pt=500.0,
        height_pt=500.0,
        rotation=0,
        primitives=[primitive],
    )


def test_replace_text_shrinks_to_fit() -> None:
    text = "ShrinkTest"
    font_size = 12.0
    width = fitz.get_text_length(text, fontname="helv", fontsize=font_size)
    page = _make_page(font_size, bbox_width=width * 0.85)

    _, results = apply_ops_to_page(
        page,
        [
            PatchReplaceText(
                op="replace_text",
                target_id="prim-1",
                new_text=text,
                policy="FIT_IN_BOX",
            )
        ],
    )
    result = results[0]
    assert result.ok is True
    assert result.font_adjusted is True


def test_replace_text_rejects_when_too_long() -> None:
    text = "RejectTest"
    font_size = 12.0
    width = fitz.get_text_length(text, fontname="helv", fontsize=font_size)
    page = _make_page(font_size, bbox_width=width * 0.4)

    _, results = apply_ops_to_page(
        page,
        [
            PatchReplaceText(
                op="replace_text",
                target_id="prim-1",
                new_text=text,
                policy="FIT_IN_BOX",
            )
        ],
    )
    result = results[0]
    assert result.ok is False
    assert result.code == "TEXT_TOO_LONG"
    assert result.details == {"min_scale": MIN_FONT_SCALE, "max_expand": MAX_BBOX_EXPAND}
