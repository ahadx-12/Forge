from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import fitz


logger = logging.getLogger("forge_api.decode")


def _round(value: float | int | None, precision: int = 3) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    return round(float(value), precision)


def _round_bbox(bbox: list[float]) -> list[float]:
    return [_round(coord) for coord in bbox]


def _normalize_color(color: Any) -> Any:
    if color is None:
        return None
    if isinstance(color, int):
        return color
    if isinstance(color, (list, tuple)) and len(color) == 3:
        r, g, b = color
        r = int(round(float(r) * 255)) if isinstance(r, float) and r <= 1 else int(round(float(r)))
        g = int(round(float(g) * 255)) if isinstance(g, float) and g <= 1 else int(round(float(g)))
        b = int(round(float(b) * 255)) if isinstance(b, float) and b <= 1 else int(round(float(b)))
        return f"#{r:02x}{g:02x}{b:02x}"
    return color


def _extract_text_items(page: fitz.Page) -> list[dict[str, Any]]:
    text_dict = page.get_text("dict")
    items: list[dict[str, Any]] = []
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text.strip():
                    continue
                bbox = span.get("bbox") or block.get("bbox") or [0, 0, 0, 0]
                items.append(
                    {
                        "kind": "text",
                        "bbox": _round_bbox(list(bbox)),
                        "text": text,
                        "font": span.get("font"),
                        "size": _round(span.get("size")),
                        "color": _normalize_color(span.get("color")),
                    }
                )
    return items


def _extract_drawing_items(page: fitz.Page) -> list[dict[str, Any]]:
    drawings = page.get_drawings()
    items: list[dict[str, Any]] = []
    for drawing in drawings:
        rect = drawing.get("rect")
        bbox = [rect.x0, rect.y0, rect.x1, rect.y1] if rect else [0, 0, 0, 0]
        items.append(
            {
                "kind": "path",
                "bbox": _round_bbox(bbox),
                "stroke_width": _round(drawing.get("width")),
                "stroke_color": _normalize_color(drawing.get("color")),
                "fill_color": _normalize_color(drawing.get("fill")),
            }
        )
    return items


def decode_pdf(doc_id: str, pdf_path: Path, cache_path: Path) -> dict[str, Any]:
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    document = fitz.open(pdf_path)
    try:
        pages: list[dict[str, Any]] = []
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            items = _extract_text_items(page) + _extract_drawing_items(page)
            items_sorted = sorted(
                enumerate(items),
                key=lambda entry: (
                    entry[1].get("kind"),
                    *(entry[1].get("bbox") or [0, 0, 0, 0]),
                    entry[1].get("text") or "",
                    entry[0],
                ),
            )
            ordered_items = [item for _, item in items_sorted]
            pages.append(
                {
                    "page_index": page_index,
                    "width_pt": _round(page.rect.width),
                    "height_pt": _round(page.rect.height),
                    "rotation": page.rotation,
                    "items": ordered_items,
                }
            )

        payload = {
            "doc_id": doc_id,
            "page_count": document.page_count,
            "pages": pages,
        }
    finally:
        document.close()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload, indent=2))
    return payload
