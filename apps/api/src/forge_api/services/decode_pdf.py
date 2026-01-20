from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import fitz

from forge_api.services.storage import get_storage


logger = logging.getLogger("forge_api.decode")


def _coerce_float(value: Any, default: float, doc_id: str, field: str) -> float:
    if value is None:
        logger.warning("doc_id=%s field=%s missing numeric value; defaulting to %.3f", doc_id, field, default)
        return default
    if isinstance(value, bool):
        logger.warning("doc_id=%s field=%s invalid bool value=%r; defaulting to %.3f", doc_id, field, value, default)
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        logger.warning("doc_id=%s field=%s invalid numeric value=%r; defaulting to %.3f", doc_id, field, value, default)
        return default


def _round(value: Any, doc_id: str, field: str, default: float = 0.0) -> float | int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return round(_coerce_float(value, default, doc_id, field), 3)


def _rect_to_list(rect: fitz.Rect, doc_id: str, field: str) -> list[float]:
    return [
        _round(rect.x0, doc_id, f"{field}.x0"),
        _round(rect.y0, doc_id, f"{field}.y0"),
        _round(rect.x1, doc_id, f"{field}.x1"),
        _round(rect.y1, doc_id, f"{field}.y1"),
    ]


def _normalize_bbox(
    bbox: list[float | int | None] | tuple[float | int | None, float | int | None, float | int | None, float | int | None],
    doc_id: str,
    field: str,
) -> list[float]:
    if bbox is None or len(bbox) < 4:
        logger.warning("doc_id=%s field=%s invalid bbox=%r; defaulting to zeros", doc_id, field, bbox)
        return [0.0, 0.0, 0.0, 0.0]
    return [
        _round(bbox[0], doc_id, f"{field}.x0"),
        _round(bbox[1], doc_id, f"{field}.y0"),
        _round(bbox[2], doc_id, f"{field}.x1"),
        _round(bbox[3], doc_id, f"{field}.y1"),
    ]


def _sort_key(item: dict[str, Any]) -> tuple:
    bbox = item.get("bbox", [0, 0, 0, 0])
    return (
        item.get("kind", ""),
        bbox[1],
        bbox[0],
        bbox[3],
        bbox[2],
        item.get("text", ""),
    )


def decode_document(doc_id: str) -> dict[str, Any]:
    storage = get_storage()
    decode_key = f"documents/{doc_id}/decode.json"
    if storage.exists(decode_key):
        return json.loads(storage.get_bytes(decode_key).decode("utf-8"))

    pdf_key = f"documents/{doc_id}/original.pdf"
    if not storage.exists(pdf_key):
        raise FileNotFoundError("Document PDF missing")

    pdf_bytes = storage.get_bytes(pdf_key)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[dict[str, Any]] = []

    try:
        page_count = len(doc)
        for index in range(page_count):
            page = doc[index]
            page_items: list[dict[str, Any]] = []

            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        page_items.append(
                            {
                                "kind": "text",
                                "bbox": _normalize_bbox(span.get("bbox"), doc_id, "span.bbox"),
                                "text": text,
                                "font": span.get("font"),
                                "size": _round(span.get("size", 0.0), doc_id, "span.size"),
                                "color": span.get("color"),
                                "font_ref": {
                                    "pdf_font_name": span.get("font"),
                                    "embedded": False,
                                },
                            }
                        )

            for drawing in page.get_drawings():
                rect = drawing.get("rect")
                if rect is None:
                    continue
                page_items.append(
                    {
                        "kind": "drawing",
                        "bbox": _rect_to_list(rect, doc_id, "drawing.rect"),
                        "width": _round(drawing.get("width", 0.0), doc_id, "drawing.width"),
                        "color": drawing.get("color"),
                        "fill": drawing.get("fill"),
                    }
                )

            page_items.sort(key=_sort_key)
            pages.append(
                {
                    "index": index,
                    "width_pt": _round(page.rect.width, doc_id, "page.width_pt"),
                    "height_pt": _round(page.rect.height, doc_id, "page.height_pt"),
                    "rotation": page.rotation,
                    "items": page_items,
                }
            )
    finally:
        doc.close()

    payload = {
        "doc_id": doc_id,
        "page_count": page_count,
        "pages": pages,
        "extracted_at_iso": datetime.now(timezone.utc).isoformat(),
    }

    storage.put_bytes(decode_key, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    return payload
