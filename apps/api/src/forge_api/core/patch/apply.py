from __future__ import annotations

from dataclasses import dataclass

import fitz

from forge_api.schemas.ir import IRPage, IRPrimitive
from forge_api.schemas.patch import PatchOp, PatchOpResult, PatchReplaceText, PatchSetStyle


MIN_FONT_SIZE_PT = 6.0
FONT_SIZE_STEP_PT = 0.5


@dataclass(frozen=True)
class TextFitResult:
    font_size: float
    overflow: bool


def _measure_text_width(text: str, font_name: str | None, font_size: float) -> float:
    try:
        return fitz.get_text_length(text, fontname=font_name or "helv", fontsize=font_size)
    except RuntimeError:
        return fitz.get_text_length(text, fontname="helv", fontsize=font_size)


def _fits_bbox(text: str, font_name: str | None, font_size: float, bbox: list[float]) -> bool:
    width = _measure_text_width(text, font_name, font_size)
    max_width = bbox[2] - bbox[0]
    max_height = bbox[3] - bbox[1]
    return width <= max_width and font_size <= max_height


def fit_text_to_box(text: str, font_name: str | None, font_size: float, bbox: list[float]) -> TextFitResult:
    if _fits_bbox(text, font_name, font_size, bbox):
        return TextFitResult(font_size=font_size, overflow=False)

    next_size = font_size
    while next_size - FONT_SIZE_STEP_PT >= MIN_FONT_SIZE_PT:
        next_size = round(next_size - FONT_SIZE_STEP_PT, 2)
        if _fits_bbox(text, font_name, next_size, bbox):
            return TextFitResult(font_size=next_size, overflow=False)

    overflow = not _fits_bbox(text, font_name, MIN_FONT_SIZE_PT, bbox)
    return TextFitResult(font_size=MIN_FONT_SIZE_PT, overflow=overflow)


def _apply_set_style(primitive: IRPrimitive, op: PatchSetStyle) -> None:
    if op.stroke_color is not None:
        primitive.style["stroke_color"] = op.stroke_color
    if op.stroke_width_pt is not None:
        primitive.style["stroke_width"] = op.stroke_width_pt
    if op.fill_color is not None:
        primitive.style["fill_color"] = op.fill_color
    if op.opacity is not None:
        primitive.style["opacity"] = op.opacity


def _apply_replace_text(primitive: IRPrimitive, op: PatchReplaceText) -> PatchOpResult:
    primitive.text = op.new_text
    font_name = primitive.style.get("font") if isinstance(primitive.style, dict) else None
    font_size = float(primitive.style.get("size") or 0.0)

    if op.policy == "FIT_IN_BOX":
        fit = fit_text_to_box(op.new_text, font_name, font_size, primitive.bbox)
        primitive.style["size"] = fit.font_size
        primitive.patch_meta = {
            "overflow": fit.overflow,
            "fitted_font_size": fit.font_size,
        }
        return PatchOpResult(target_id=primitive.id, applied_font_size_pt=fit.font_size, overflow=fit.overflow)

    overflow = not _fits_bbox(op.new_text, font_name, font_size, primitive.bbox)
    primitive.patch_meta = {
        "overflow": overflow,
    }
    return PatchOpResult(target_id=primitive.id, applied_font_size_pt=font_size, overflow=overflow)


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
            results.append(_apply_replace_text(target, op))

    return patched_page, results
