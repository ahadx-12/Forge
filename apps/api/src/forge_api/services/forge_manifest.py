from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

import fitz

from forge_api.services.storage import get_storage

logger = logging.getLogger("forge_api.forge_manifest")


def _round(value: float) -> float:
    return round(float(value), 3)


def _normalize_text(text: str) -> str:
    return text.strip()


def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_bbox(bbox: list[float]) -> list[float]:
    if len(bbox) < 4:
        return [0.0, 0.0, 0.0, 0.0]
    return [_round(bbox[0]), _round(bbox[1]), _round(bbox[2]), _round(bbox[3])]


def _rotated_dimensions(width_pt: float, height_pt: float, rotation: int) -> tuple[float, float]:
    normalized = rotation % 360
    if normalized in (90, 270):
        return height_pt, width_pt
    return width_pt, height_pt


def _rotate_point(x: float, y: float, width_pt: float, height_pt: float, rotation: int) -> tuple[float, float]:
    normalized = rotation % 360
    if normalized == 90:
        return y, width_pt - x
    if normalized == 180:
        return width_pt - x, height_pt - y
    if normalized == 270:
        return height_pt - y, x
    return x, y


def _bbox_pt_to_px(
    bbox_pt: list[float],
    scale_x: float,
    scale_y: float,
    page_width_pt: float,
    page_height_pt: float,
    rotation: int = 0,
) -> list[float]:
    """Convert PDF point bbox (bottom-left origin) into PNG pixel bbox (top-left origin)."""
    if len(bbox_pt) < 4:
        return [0.0, 0.0, 0.0, 0.0]
    x0_pt, y0_pt, x1_pt, y1_pt = bbox_pt
    corners = [
        (x0_pt, y0_pt),
        (x1_pt, y0_pt),
        (x1_pt, y1_pt),
        (x0_pt, y1_pt),
    ]
    rotated = [_rotate_point(x, y, page_width_pt, page_height_pt, rotation) for x, y in corners]
    rotated_x = [point[0] for point in rotated]
    rotated_y = [point[1] for point in rotated]
    x0_rot, x1_rot = min(rotated_x), max(rotated_x)
    y0_rot, y1_rot = min(rotated_y), max(rotated_y)
    rotated_width_pt, rotated_height_pt = _rotated_dimensions(page_width_pt, page_height_pt, rotation)
    x0_px = x0_rot * scale_x
    x1_px = x1_rot * scale_x
    y0_px = (rotated_height_pt - y1_rot) * scale_y
    y1_px = (rotated_height_pt - y0_rot) * scale_y
    return [_round(x0_px), _round(y0_px), _round(x1_px), _round(y1_px)]


def _merge_line_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge adjacent character-level spans into word-level spans with strict validation."""
    if not spans:
        return []
    spans = sorted(spans, key=lambda item: item["bbox"][0])
    merged: list[dict[str, Any]] = []
    for span in spans:
        if not merged:
            merged.append(span)
            continue
        current = merged[-1]
        if (
            span["font"] != current["font"]
            or span["size"] != current["size"]
            or span["color"] != current["color"]
        ):
            merged.append(span)
            continue
        current_bbox = current["bbox"]
        span_bbox = span["bbox"]
        overlap = min(current_bbox[3], span_bbox[3]) - max(current_bbox[1], span_bbox[1])
        box_height = current_bbox[3] - current_bbox[1]
        if box_height <= 0 or overlap < box_height * 0.7:
            merged.append(span)
            continue
        gap = span_bbox[0] - current_bbox[2]
        max_gap = current["size"] * 0.5
        space_gap = current["size"] * 0.2
        should_merge = gap < 0 or gap <= space_gap
        if gap > max_gap:
            should_merge = False
        if should_merge:
            current["text"] = f"{current['text']}{span['text']}"
            current["bbox"] = [
                min(current_bbox[0], span_bbox[0]),
                min(current_bbox[1], span_bbox[1]),
                max(current_bbox[2], span_bbox[2]),
                max(current_bbox[3], span_bbox[3]),
            ]
        else:
            merged.append(span)
    return merged


def _color_to_hex(value: Any) -> str:
    if isinstance(value, int):
        r = (value >> 16) & 0xFF
        g = (value >> 8) & 0xFF
        b = value & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"
    return "#000000"


def _manifest_key(doc_id: str) -> str:
    return f"docs/{doc_id}/forge/manifest.json"


def _page_png_key(doc_id: str, page_index: int) -> str:
    return f"docs/{doc_id}/pages/{page_index}.png"


def load_forge_manifest(doc_id: str) -> dict[str, Any] | None:
    storage = get_storage()
    key = _manifest_key(doc_id)
    if not storage.exists(key):
        return None
    return json.loads(storage.get_bytes(key).decode("utf-8"))


def build_forge_manifest(doc_id: str) -> dict[str, Any]:
    storage = get_storage()
    existing = load_forge_manifest(doc_id)
    if existing:
        return existing

    pdf_key = f"documents/{doc_id}/original.pdf"
    if not storage.exists(pdf_key):
        raise FileNotFoundError("Document PDF missing")

    pdf_bytes = storage.get_bytes(pdf_key)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[dict[str, Any]] = []
    debug_logged = False
    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            zoom = 2.0
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            scale_x = pix.width / page.rect.width if page.rect.width else 1.0
            scale_y = pix.height / page.rect.height if page.rect.height else 1.0
            png_bytes = pix.tobytes("png")
            storage.put_bytes(
                _page_png_key(doc_id, page_index),
                png_bytes,
                content_type="image/png",
            )

            spans: list[dict[str, Any]] = []
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                for line in block.get("lines", []):
                    line_spans: list[dict[str, Any]] = []
                    for span in line.get("spans", []):
                        text = _normalize_text(span.get("text", ""))
                        if not text:
                            continue
                        bbox = _normalize_bbox(span.get("bbox") or [0.0, 0.0, 0.0, 0.0])
                        line_spans.append(
                            {
                                "text": text,
                                "bbox": bbox,
                                "font": span.get("font") or "",
                                "size": _round(span.get("size") or 0.0),
                                "color": _color_to_hex(span.get("color")),
                            }
                        )
                    spans.extend(_merge_line_spans(line_spans))

            spans.sort(
                key=lambda item: (
                    _round(item["bbox"][1]),
                    _round(item["bbox"][0]),
                    _round(item["bbox"][3]),
                    _round(item["bbox"][2]),
                    item["text"],
                )
            )

            items: list[dict[str, Any]] = []
            for idx, span in enumerate(spans):
                forge_id = f"p{page_index}_t{idx}"
                content_hash = _compute_hash(span["text"])
                bbox_pt = span["bbox"]
                bbox_px = _bbox_pt_to_px(
                    bbox_pt,
                    scale_x,
                    scale_y,
                    page.rect.width,
                    page.rect.height,
                    page.rotation,
                )
                items.append(
                    {
                        "forge_id": forge_id,
                        "text": span["text"],
                        # bbox is in PNG pixel units with a top-left origin.
                        "bbox": bbox_px,
                        # bbox_pt is in PDF points with a bottom-left origin (for export).
                        "bbox_pt": bbox_pt,
                        "font": span["font"],
                        "size": _round(span["size"] * scale_x),
                        "size_pt": span["size"],
                        "color": span["color"],
                        "content_hash": content_hash,
                    }
                )

            if items and not debug_logged:
                preview_items = [
                    {
                        "forge_id": item["forge_id"],
                        "bbox_pdf": item["bbox_pt"],
                        "bbox_px": item["bbox"],
                        "text": item["text"],
                    }
                    for item in items[:3]
                ]
                png_kb = round(len(png_bytes) / 1024, 1)
                logger.info(
                    "forge manifest overlay debug doc_id=%s pdf_box={w_pt:%s,h_pt:%s,rotation:%s,box_type:%s} "
                    "png={w_px:%s,h_px:%s,size_kb:%s} primitives=%s expected_scale={scale_x:%s,scale_y:%s} "
                    "preview=%s",
                    doc_id,
                    _round(page.rect.width),
                    _round(page.rect.height),
                    page.rotation,
                    "cropbox",
                    pix.width,
                    pix.height,
                    png_kb,
                    len(items),
                    _round(scale_x),
                    _round(scale_y),
                    preview_items,
                )
                debug_logged = True

            pages.append(
                {
                    "index": page_index,
                    "width_pt": _round(page.rect.width),
                    "height_pt": _round(page.rect.height),
                    "width_px": pix.width,
                    "height_px": pix.height,
                    "scale": _round(scale_x),
                    "rotation": page.rotation,
                    "image_path": f"/v1/documents/{doc_id}/forge/pages/{page_index}.png",
                    "items": items,
                }
            )
    finally:
        doc.close()

    payload = {
        "doc_id": doc_id,
        "page_count": len(pages),
        "pages": pages,
        "generated_at_iso": datetime.now(timezone.utc).isoformat(),
    }
    storage.put_bytes(_manifest_key(doc_id), json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    logger.info("forge manifest built doc_id=%s pages=%s", doc_id, len(pages))
    return payload
