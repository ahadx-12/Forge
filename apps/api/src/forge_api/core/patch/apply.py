from __future__ import annotations

from dataclasses import dataclass
import logging

import fitz

from forge_api.core.fonts.resolve import resolve_builtin_font
from forge_api.core.patch.fonts import DEFAULT_FONT
from forge_api.schemas.ir import IRPage, IRPrimitive
from forge_api.schemas.patch import PatchOp, PatchOpResult, PatchReplaceText, PatchSetStyle


MIN_FONT_SCALE = 0.70
MAX_BBOX_EXPAND = 1.50
COLLISION_MARGIN = 2.0
FONT_SIZE_STEP_PT = 0.5

logger = logging.getLogger("forge_api")
_font_fallback_logged: set[tuple[str | None, int | None, str | None, str | None]] = set()


@dataclass
class FontContext:
    raw_font: str | None
    font_name: str
    fidelity: float
    reason: str
    warnings: list[dict[str, object]]


@dataclass(frozen=True)
class TextFitResult:
    ok: bool
    font_size: float
    bbox: list[float]
    overflow: bool
    font_adjusted: bool
    bbox_adjusted: bool
    code: str | None = None
    details: dict[str, object] | None = None


def _log_font_warning(
    doc_id: str,
    page_index: int,
    primitive_id: str,
    raw_font: str | None,
    error: Exception,
) -> None:
    key = (doc_id, page_index, primitive_id, raw_font)
    if key in _font_fallback_logged:
        return
    _font_fallback_logged.add(key)
    logger.warning(
        "Unsupported font fallback doc_id=%s page_index=%s primitive_id=%s font=%s error=%s",
        doc_id,
        page_index,
        primitive_id,
        raw_font,
        error.__class__.__name__,
    )


def _resolve_font(raw_font: str | None) -> FontContext:
    builtin_font, fidelity, reason = resolve_builtin_font(raw_font)
    warnings: list[dict[str, object]] = []
    if reason != "builtin":
        warnings.append(
            {
                "code": "font_fallback",
                "raw_font": raw_font,
                "used": builtin_font,
                "fidelity": fidelity,
                "reason": reason,
            }
        )
    return FontContext(
        raw_font=raw_font,
        font_name=builtin_font,
        fidelity=fidelity,
        reason=reason,
        warnings=warnings,
    )


def _measure_text_width(
    text: str,
    font: FontContext,
    font_size: float,
    doc_id: str,
    page_index: int,
    primitive_id: str,
) -> float:
    try:
        return fitz.get_text_length(text, fontname=font.font_name, fontsize=font_size)
    except (RuntimeError, ValueError) as exc:
        _log_font_warning(doc_id, page_index, primitive_id, font.raw_font, exc)
        if font.font_name != DEFAULT_FONT:
            font.warnings.append(
                {
                    "code": "font_fallback",
                    "raw_font": font.raw_font,
                    "used": DEFAULT_FONT,
                    "fidelity": 0.7,
                    "reason": "unsupported_font",
                }
            )
        font.font_name = DEFAULT_FONT
        return fitz.get_text_length(text, fontname=DEFAULT_FONT, fontsize=font_size)


def _fits_bbox(
    text: str,
    font: FontContext,
    font_size: float,
    bbox: list[float],
    doc_id: str,
    page_index: int,
    primitive_id: str,
) -> bool:
    width = _measure_text_width(text, font, font_size, doc_id, page_index, primitive_id)
    max_width = bbox[2] - bbox[0]
    max_height = bbox[3] - bbox[1]
    return width <= max_width and font_size <= max_height


def _bbox_overlaps(a: list[float], b: list[float], margin: float) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (
        ax1 + margin <= bx0
        or ax0 - margin >= bx1
        or ay1 + margin <= by0
        or ay0 - margin >= by1
    )


def _bbox_collides(
    candidate: list[float],
    primitives: list[IRPrimitive],
    target_id: str,
    margin: float,
) -> bool:
    for primitive in primitives:
        if primitive.id == target_id:
            continue
        if _bbox_overlaps(candidate, primitive.bbox, margin):
            return True
    return False


def _fit_text_to_box(
    text: str,
    font: FontContext,
    font_size: float,
    bbox: list[float],
    page_width: float,
    primitives: list[IRPrimitive],
    doc_id: str,
    page_index: int,
    primitive_id: str,
) -> TextFitResult:
    if _fits_bbox(text, font, font_size, bbox, doc_id, page_index, primitive_id):
        return TextFitResult(
            ok=True,
            font_size=font_size,
            bbox=bbox,
            overflow=False,
            font_adjusted=False,
            bbox_adjusted=False,
        )

    min_size = round(font_size * MIN_FONT_SCALE, 2)
    next_size = font_size
    while next_size - FONT_SIZE_STEP_PT >= min_size:
        next_size = round(next_size - FONT_SIZE_STEP_PT, 2)
        if _fits_bbox(text, font, next_size, bbox, doc_id, page_index, primitive_id):
            return TextFitResult(
                ok=True,
                font_size=next_size,
                bbox=bbox,
                overflow=False,
                font_adjusted=True,
                bbox_adjusted=False,
            )

    x0, y0, x1, y1 = bbox
    width = x1 - x0
    max_width = min(page_width, x0 + width * MAX_BBOX_EXPAND) - x0
    expanded_bbox = [x0, y0, x0 + max_width, y1]
    if max_width > width:
        if not _bbox_collides(expanded_bbox, primitives, primitive_id, COLLISION_MARGIN):
            if _fits_bbox(text, font, min_size, expanded_bbox, doc_id, page_index, primitive_id):
                return TextFitResult(
                    ok=True,
                    font_size=min_size,
                    bbox=expanded_bbox,
                    overflow=False,
                    font_adjusted=min_size < font_size,
                    bbox_adjusted=True,
                )

    return TextFitResult(
        ok=False,
        font_size=min_size,
        bbox=bbox,
        overflow=True,
        font_adjusted=True,
        bbox_adjusted=False,
        code="TEXT_TOO_LONG",
        details={"min_scale": MIN_FONT_SCALE, "max_expand": MAX_BBOX_EXPAND},
    )


def _apply_set_style(primitive: IRPrimitive, op: PatchSetStyle) -> None:
    if op.stroke_color is not None:
        primitive.style["stroke_color"] = op.stroke_color
    if op.stroke_width_pt is not None:
        primitive.style["stroke_width"] = op.stroke_width_pt
    if op.fill_color is not None:
        primitive.style["fill_color"] = op.fill_color
    if op.opacity is not None:
        primitive.style["opacity"] = op.opacity


def _apply_replace_text(
    page: IRPage,
    primitive: IRPrimitive,
    op: PatchReplaceText,
    primitives: list[IRPrimitive],
) -> PatchOpResult:
    font_name = primitive.style.get("font") if isinstance(primitive.style, dict) else None
    font_size = float(primitive.style.get("size") or 0.0)
    font = _resolve_font(font_name)
    fit = _fit_text_to_box(
        op.new_text,
        font,
        font_size,
        primitive.bbox,
        page.width_pt,
        primitives,
        page.doc_id,
        page.page_index,
        primitive.id,
    )

    if not fit.ok:
        return PatchOpResult(
            target_id=primitive.id,
            ok=False,
            code=fit.code,
            details=fit.details,
            applied_font_size_pt=fit.font_size,
            overflow=True,
            did_not_fit=True,
            font_adjusted=fit.font_adjusted,
            bbox_adjusted=fit.bbox_adjusted,
            warnings=font.warnings,
        )

    primitive.text = op.new_text
    primitive.style["size"] = fit.font_size
    primitive.bbox = fit.bbox
    primitive.patch_meta = {
        "overflow": fit.overflow,
        "fitted_font_size": fit.font_size,
        "did_not_fit": fit.overflow,
        "font_adjusted": fit.font_adjusted,
        "bbox_adjusted": fit.bbox_adjusted,
    }
    return PatchOpResult(
        target_id=primitive.id,
        applied_font_size_pt=fit.font_size,
        overflow=fit.overflow,
        did_not_fit=fit.overflow,
        font_adjusted=fit.font_adjusted,
        bbox_adjusted=fit.bbox_adjusted,
        warnings=font.warnings,
    )


def apply_ops_to_page(page: IRPage, ops: list[PatchOp]) -> tuple[IRPage, list[PatchOpResult]]:
    patched_page = page.model_copy(deep=True)
    primitive_by_id = {primitive.id: primitive for primitive in patched_page.primitives}
    results: list[PatchOpResult] = []

    for op in ops:
        target = primitive_by_id.get(op.target_id)
        if target is None:
            continue
        if op.op == "set_style" and target.kind == "path":
            _apply_set_style(target, op)
            results.append(PatchOpResult(target_id=target.id))
        elif op.op == "replace_text" and target.kind == "text":
            results.append(_apply_replace_text(patched_page, target, op, patched_page.primitives))

    return patched_page, results
