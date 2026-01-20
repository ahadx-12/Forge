from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from forge_api.schemas.patch import OverlayPatchOp, OverlayPatchRecord
from forge_api.services.storage import get_patch_storage


def _overlay_log_key(doc_id: str) -> str:
    return f"docs/{doc_id}/forge/overlay_patches.json"


def load_overlay_patch_log(doc_id: str) -> list[OverlayPatchRecord]:
    storage = get_patch_storage()
    key = _overlay_log_key(doc_id)
    if not storage.exists(key):
        return []
    payload = json.loads(storage.get_bytes(key).decode("utf-8"))
    return [OverlayPatchRecord.model_validate(item) for item in payload]


def append_overlay_patchset(doc_id: str, ops: list[OverlayPatchOp]) -> OverlayPatchRecord:
    storage = get_patch_storage()
    patchsets = load_overlay_patch_log(doc_id)
    record = OverlayPatchRecord(
        patch_id=str(uuid4()),
        created_at_iso=datetime.now(timezone.utc),
        ops=ops,
    )
    patchsets.append(record)
    payload = [item.model_dump(mode="json") for item in patchsets]
    storage.put_bytes(
        _overlay_log_key(doc_id),
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8"),
    )
    return record


def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_overlay_state(
    manifest: dict[str, Any],
    patchsets: list[OverlayPatchRecord],
) -> dict[int, dict[str, Any]]:
    overlay: dict[int, dict[str, Any]] = {}
    masks_by_page: dict[int, dict[str, dict[str, Any]]] = {}
    for page in manifest.get("pages", []):
        page_index = page.get("index")
        items: dict[str, dict[str, Any]] = {}
        for item in page.get("items", []):
            forge_id = item.get("forge_id")
            text = item.get("text", "")
            if not forge_id:
                continue
            items[forge_id] = {
                "text": text,
                "content_hash": _compute_hash(text),
                "bbox": item.get("bbox") or [0.0, 0.0, 0.0, 0.0],
                "font_size": item.get("size") or 0.0,
                "base_text": text,
            }
        if page_index is not None:
            overlay[int(page_index)] = {"primitives": items, "masks": []}
            masks_by_page[int(page_index)] = {}

    for patchset in patchsets:
        for op in patchset.ops:
            page_entry = overlay.get(op.page_index)
            if page_entry is None:
                continue
            page_map = page_entry.get("primitives", {})
            if op.forge_id not in page_map:
                continue
            current = page_map[op.forge_id]
            current["text"] = op.new_text
            current["content_hash"] = _compute_hash(op.new_text)
            base_text = current.get("base_text") or ""
            if op.new_text != base_text:
                mask = _build_overlay_mask(current)
                masks_by_page[op.page_index][op.forge_id] = mask

    for page_index, masks in masks_by_page.items():
        if page_index in overlay:
            overlay[page_index]["masks"] = list(masks.values())

    return overlay


def _round(value: float) -> float:
    return round(float(value), 3)


def _build_overlay_mask(item: dict[str, Any], padding_px: float = 2.0) -> dict[str, Any]:
    bbox = item.get("bbox") or [0.0, 0.0, 0.0, 0.0]
    if len(bbox) < 4:
        bbox = [0.0, 0.0, 0.0, 0.0]
    x0, y0, x1, y1 = [float(value) for value in bbox]
    height = max(0.0, y1 - y0)
    font_size = float(item.get("font_size") or 0.0)
    extra_vertical = height * 0.1 if font_size and height > font_size * 2.5 else 0.0
    x0 -= padding_px
    x1 += padding_px
    y0 -= padding_px + (extra_vertical / 2)
    y1 += padding_px + (extra_vertical / 2)
    return {
        "bbox_px": [_round(x0), _round(y0), _round(x1), _round(y1)],
        "color": "#ffffff",
    }
