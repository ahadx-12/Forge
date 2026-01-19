from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import logging

import fitz

from forge_api.core.patch.apply import apply_ops_to_page
from forge_api.core.patch.fonts import DEFAULT_FONT, normalize_font_name
from forge_api.schemas.ir import IRPage
from forge_api.schemas.patch import PatchOp
from forge_api.services.ir_pdf import get_page_ir
from forge_api.services.patch_store import load_patch_log
from forge_api.settings import get_settings
from forge_api.services.storage import get_storage


DEFAULT_PADDING_PT = 1.5
logger = logging.getLogger("forge_api")


@dataclass(frozen=True)
class ExportResult:
    payload: bytes
    mask_mode: str
    warning: str | None = None


def _to_rgb(color) -> tuple[float, float, float]:
    if color is None:
        return (0.0, 0.0, 0.0)
    if isinstance(color, int):
        r = ((color >> 16) & 0xFF) / 255
        g = ((color >> 8) & 0xFF) / 255
        b = (color & 0xFF) / 255
        return (r, g, b)
    if isinstance(color, (list, tuple)):
        def _channel(value: object) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0

        return (_channel(color[0]), _channel(color[1]), _channel(color[2]))
    return (0.0, 0.0, 0.0)


def _overlay_rect(page: fitz.Page, bbox: list[float], padding: float, fill_color: tuple[float, float, float]) -> fitz.Rect:
    rect = fitz.Rect(bbox)
    rect.x0 -= padding
    rect.y0 -= padding
    rect.x1 += padding
    rect.y1 += padding
    page.draw_rect(rect, color=fill_color, fill=fill_color)
    return rect


def _parse_solid_color(value: str) -> tuple[float, float, float]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 3:
        return (1.0, 1.0, 1.0)
    try:
        channels = [min(255, max(0, int(part))) for part in parts]
        return tuple(channel / 255 for channel in channels)  # type: ignore[return-value]
    except ValueError:
        return (1.0, 1.0, 1.0)


def _sample_background_color(page: fitz.Page, rect: fitz.Rect) -> tuple[float, float, float] | None:
    try:
        clip = fitz.Rect(rect)
        if clip.is_empty or clip.width <= 0 or clip.height <= 0:
            return None
        scale = 0.2
        pix = page.get_pixmap(clip=clip, matrix=fitz.Matrix(scale, scale), alpha=False)
        if pix.width == 0 or pix.height == 0:
            return None
        samples = pix.samples
        channels = pix.n
        total_pixels = pix.width * pix.height
        stride = max(1, total_pixels // 64)
        total = [0, 0, 0]
        count = 0
        for i in range(0, len(samples), channels * stride):
            total[0] += samples[i]
            total[1] += samples[i + 1]
            total[2] += samples[i + 2]
            count += 1
        if count == 0:
            return None
        return (total[0] / (255 * count), total[1] / (255 * count), total[2] / (255 * count))
    except Exception:
        return None


def _draw_text(page: fitz.Page, primitive, bbox: list[float], doc_id: str, page_index: int) -> None:
    raw_font = primitive.style.get("font")
    font_name = normalize_font_name(raw_font) or DEFAULT_FONT
    font_size = float(primitive.style.get("size") or 12)
    color = _to_rgb(primitive.style.get("color"))
    x0, y0, x1, y1 = bbox
    try:
        page.insert_textbox(
            fitz.Rect(x0, y0, x1, y1),
            primitive.text or "",
            fontname=font_name,
            fontsize=font_size,
            color=color,
            align=fitz.TEXT_ALIGN_LEFT,
        )
    except (RuntimeError, ValueError) as exc:
        logger.warning(
            "Unsupported font fallback doc_id=%s page_index=%s primitive_id=%s font=%s error=%s",
            doc_id,
            page_index,
            primitive.id,
            raw_font,
            exc.__class__.__name__,
        )
        page.insert_textbox(
            fitz.Rect(x0, y0, x1, y1),
            primitive.text or "",
            fontname=DEFAULT_FONT,
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


def export_pdf_with_overlays(
    doc_id: str,
    padding_pt: float = DEFAULT_PADDING_PT,
    mask_mode: str | None = None,
) -> ExportResult:
    storage = get_storage()
    pdf_key = f"documents/{doc_id}/original.pdf"
    pdf_bytes = storage.get_bytes(pdf_key)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    settings = get_settings()
    requested_mode = (mask_mode or settings.FORGE_EXPORT_MASK_MODE).upper()
    if requested_mode not in {"SOLID", "AUTO_BG"}:
        requested_mode = "SOLID"
    solid_color = _parse_solid_color(settings.FORGE_EXPORT_MASK_SOLID_COLOR)
    warning: str | None = None
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
                fill_color = solid_color
                if requested_mode == "AUTO_BG":
                    sampled = _sample_background_color(page, fitz.Rect(primitive.bbox))
                    if sampled is None:
                        warning = "AUTO_BG_FAILED"
                        fill_color = solid_color
                    else:
                        fill_color = sampled
                _overlay_rect(page, primitive.bbox, padding_pt, fill_color)
                if primitive.kind == "path":
                    _draw_path(page, primitive, primitive.bbox)
                elif primitive.kind == "text":
                    _draw_text(page, primitive, primitive.bbox, doc_id, page_index)

        buffer = BytesIO()
        doc.save(buffer)
        return ExportResult(payload=buffer.getvalue(), mask_mode=requested_mode, warning=warning)
    finally:
        doc.close()
