from __future__ import annotations

import hashlib
from typing import Any

import fitz

from forge_api.core.ir.model import BBox, PageIR, PathPrimitive, PathStyle, TextRun, TextStyle


ROUND_PRECISION = 3


def _coerce_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _round(value: float | int) -> float | int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return round(_coerce_float(value), ROUND_PRECISION)


def _round_optional(value: float | int | None) -> float | int | None:
    if value is None:
        return None
    try:
        return _round(value)
    except (TypeError, ValueError):
        return None


def _normalize_color(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [_round(_coerce_float(channel)) for channel in value]
    return value


def _normalize_bbox(bbox: list[float | int | None] | tuple[float | int | None, float | int | None, float | int | None, float | int | None]) -> BBox:
    if bbox is None or len(bbox) < 4:
        return (0.0, 0.0, 0.0, 0.0)
    x0, y0, x1, y1 = bbox
    return (
        _round(_coerce_float(x0)),
        _round(_coerce_float(y0)),
        _round(_coerce_float(x1)),
        _round(_coerce_float(y1)),
    )


def _rect_to_bbox(rect: fitz.Rect) -> BBox:
    return _normalize_bbox((rect.x0, rect.y0, rect.x1, rect.y1))


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.{ROUND_PRECISION}f}"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (list, tuple)):
        return ",".join(_format_value(item) for item in value)
    return str(value)


def _bbox_signature(bbox: BBox) -> str:
    return ",".join(_format_value(value) for value in bbox)


def _stable_signature(fields: dict[str, Any]) -> str:
    ordered_items = [f"{key}={_format_value(fields[key])}" for key in sorted(fields.keys())]
    return "|".join(ordered_items)


def _stable_id(signature: str) -> str:
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()


def _sort_key(item: dict[str, Any]) -> tuple:
    bbox = item.get("bbox", (0.0, 0.0, 0.0, 0.0))
    kind_order = 0 if item.get("kind") == "text" else 1
    return (
        kind_order,
        bbox[1],
        bbox[0],
        bbox[3],
        bbox[2],
        item.get("text", ""),
        item.get("stroke_width", 0.0),
    )


def normalize_page(doc_id: str, page_index: int, page: fitz.Page) -> PageIR:
    text_items: list[dict[str, Any]] = []
    text_dict = page.get_text("dict")
    for block in text_dict.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = (span.get("text") or "").strip()
                if not text:
                    continue
                text_items.append(
                    {
                        "kind": "text",
                        "text": text,
                        "font": span.get("font"),
                        "size": _round_optional(span.get("size", 0.0)),
                        "color": span.get("color"),
                        "bbox": _normalize_bbox(span.get("bbox")),
                    }
                )

    path_items: list[dict[str, Any]] = []
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None:
            continue
        path_items.append(
            {
                "kind": "path",
                "bbox": _rect_to_bbox(rect),
                "stroke_width": _round_optional(drawing.get("width", 0.0)) or 0.0,
                "stroke_color": _normalize_color(drawing.get("color")),
                "fill_color": _normalize_color(drawing.get("fill")),
            }
        )

    raw_items = text_items + path_items
    raw_items.sort(key=_sort_key)

    primitives: list[TextRun | PathPrimitive] = []
    for z_index, item in enumerate(raw_items):
        bbox = item["bbox"]
        if item["kind"] == "text":
            style = TextStyle(font=item.get("font"), size=float(item.get("size") or 0.0), color=item.get("color"))
            signature_fields = {
                "doc_id": doc_id,
                "page_index": page_index,
                "kind": "text",
                "bbox": _bbox_signature(bbox),
                "text": item.get("text", ""),
                "font": item.get("font"),
                "size": style.size,
                "color": style.color,
                "z_index": z_index,
            }
            signature = _stable_signature(signature_fields)
            primitives.append(
                TextRun(
                    id=_stable_id(signature),
                    kind="text",
                    bbox=bbox,
                    z_index=z_index,
                    text=item.get("text", ""),
                    style=style,
                    signature_fields=signature_fields,
                )
            )
        else:
            style = PathStyle(
                stroke_color=item.get("stroke_color"),
                fill_color=item.get("fill_color"),
                stroke_width=float(item.get("stroke_width") or 0.0),
            )
            signature_fields = {
                "doc_id": doc_id,
                "page_index": page_index,
                "kind": "path",
                "bbox": _bbox_signature(bbox),
                "stroke_width": style.stroke_width,
                "stroke_color": style.stroke_color,
                "fill_color": style.fill_color,
                "z_index": z_index,
            }
            signature = _stable_signature(signature_fields)
            primitives.append(
                PathPrimitive(
                    id=_stable_id(signature),
                    kind="path",
                    bbox=bbox,
                    z_index=z_index,
                    style=style,
                    signature_fields=signature_fields,
                )
            )

    return PageIR(
        doc_id=doc_id,
        page_index=page_index,
        width_pt=_round(page.rect.width),
        height_pt=_round(page.rect.height),
        rotation=page.rotation,
        primitives=primitives,
    )
