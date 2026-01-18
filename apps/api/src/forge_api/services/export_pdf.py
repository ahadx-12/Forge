from __future__ import annotations

from io import BytesIO

import fitz

from forge_api.core.patch.apply import apply_ops_to_page
from forge_api.schemas.ir import IRPage
from forge_api.schemas.patch import PatchOp
from forge_api.services.ir_pdf import get_page_ir
from forge_api.services.patch_store import load_patch_log
from forge_api.services.storage import get_storage


DEFAULT_PADDING_PT = 1.5


def _to_rgb(color) -> tuple[float, float, float]:
    if color is None:
        return (0.0, 0.0, 0.0)
    if isinstance(color, int):
        r = ((color >> 16) & 0xFF) / 255
        g = ((color >> 8) & 0xFF) / 255
        b = (color & 0xFF) / 255
        return (r, g, b)
    if isinstance(color, (list, tuple)):
        return (float(color[0]), float(color[1]), float(color[2]))
    return (0.0, 0.0, 0.0)


def _overlay_rect(page: fitz.Page, bbox: list[float], padding: float) -> fitz.Rect:
    rect = fitz.Rect(bbox)
    rect.x0 -= padding
    rect.y0 -= padding
    rect.x1 += padding
    rect.y1 += padding
    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
    return rect


def _draw_text(page: fitz.Page, primitive, bbox: list[float]) -> None:
    font_name = primitive.style.get("font") or "helv"
    font_size = float(primitive.style.get("size") or 12)
    color = _to_rgb(primitive.style.get("color"))
    x0, y0, x1, y1 = bbox
    page.insert_textbox(
        fitz.Rect(x0, y0, x1, y1),
        primitive.text or "",
        fontname=font_name,
        fontsize=font_size,
        color=color,
        align=fitz.TEXT_ALIGN_LEFT,
    )


def _draw_path(page: fitz.Page, primitive, bbox: list[float]) -> None:
    stroke_color = _to_rgb(primitive.style.get("stroke_color"))
    fill_color = primitive.style.get("fill_color")
    fill = None
    if fill_color is not None:
        fill = _to_rgb(fill_color)
    width = float(primitive.style.get("stroke_width") or 0.0)
    rect = fitz.Rect(bbox)
    page.draw_rect(rect, color=stroke_color, fill=fill, width=width)


def _composite_page(doc_id: str, page_index: int, ops: list[PatchOp]) -> IRPage:
    page = get_page_ir(doc_id, page_index)
    patched, _ = apply_ops_to_page(page, ops)
    return patched


def export_pdf_with_overlays(doc_id: str, padding_pt: float = DEFAULT_PADDING_PT) -> bytes:
    storage = get_storage()
    pdf_path = storage.get_path(f"documents/{doc_id}/original.pdf")
    doc = fitz.open(pdf_path)
    try:
        patchsets = load_patch_log(doc_id)
        for page_index in range(len(doc)):
            page = doc[page_index]
            ops: list[PatchOp] = []
            for patchset in patchsets:
                if patchset.page_index == page_index:
                    ops.extend(patchset.ops)
            if not ops:
                continue
            composite_page = _composite_page(doc_id, page_index, ops)
            base_page = get_page_ir(doc_id, page_index)
            base_by_id = {primitive.id: primitive for primitive in base_page.primitives}
            for primitive in composite_page.primitives:
                base = base_by_id.get(primitive.id)
                if base is None:
                    continue
                if primitive.kind == "path" and primitive.style == base.style:
                    continue
                if primitive.kind == "text" and primitive.text == base.text and primitive.style == base.style:
                    continue
                _overlay_rect(page, primitive.bbox, padding_pt)
                if primitive.kind == "path":
                    _draw_path(page, primitive, primitive.bbox)
                elif primitive.kind == "text":
                    _draw_text(page, primitive, primitive.bbox)

        buffer = BytesIO()
        doc.save(buffer)
        return buffer.getvalue()
    finally:
        doc.close()
