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
    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            pix = page.get_pixmap(alpha=False)
            storage.put_bytes(
                _page_png_key(doc_id, page_index),
                pix.tobytes("png"),
                content_type="image/png",
            )

            spans: list[dict[str, Any]] = []
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = _normalize_text(span.get("text", ""))
                        if not text:
                            continue
                        bbox = _normalize_bbox(span.get("bbox") or [0.0, 0.0, 0.0, 0.0])
                        spans.append(
                            {
                                "text": text,
                                "bbox": bbox,
                                "font": span.get("font") or "",
                                "size": _round(span.get("size") or 0.0),
                                "color": _color_to_hex(span.get("color")),
                            }
                        )

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
                items.append(
                    {
                        "forge_id": forge_id,
                        "text": span["text"],
                        "bbox": span["bbox"],
                        "font": span["font"],
                        "size": span["size"],
                        "color": span["color"],
                        "content_hash": content_hash,
                    }
                )

            pages.append(
                {
                    "index": page_index,
                    "width_pt": _round(page.rect.width),
                    "height_pt": _round(page.rect.height),
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
