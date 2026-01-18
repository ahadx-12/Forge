from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import fitz

from forge_api.services.storage import get_storage


def _round(value: float | int) -> float | int:
    if isinstance(value, int):
        return value
    return round(float(value), 3)


def _rect_to_list(rect: fitz.Rect) -> list[float]:
    return [_round(rect.x0), _round(rect.y0), _round(rect.x1), _round(rect.y1)]


def _normalize_bbox(bbox: list[float] | tuple[float, float, float, float]) -> list[float]:
    return [_round(float(bbox[0])), _round(float(bbox[1])), _round(float(bbox[2])), _round(float(bbox[3]))]


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
                                "bbox": _normalize_bbox(span.get("bbox")),
                                "text": text,
                                "font": span.get("font"),
                                "size": _round(span.get("size", 0.0)),
                                "color": span.get("color"),
                            }
                        )

            for drawing in page.get_drawings():
                rect = drawing.get("rect")
                if rect is None:
                    continue
                page_items.append(
                    {
                        "kind": "drawing",
                        "bbox": _rect_to_list(rect),
                        "width": _round(drawing.get("width", 0.0)),
                        "color": drawing.get("color"),
                        "fill": drawing.get("fill"),
                    }
                )

            page_items.sort(key=_sort_key)
            pages.append(
                {
                    "index": index,
                    "width_pt": _round(page.rect.width),
                    "height_pt": _round(page.rect.height),
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
