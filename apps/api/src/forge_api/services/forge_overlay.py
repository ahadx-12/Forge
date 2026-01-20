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


def _round(value: float) -> float:
    return round(float(value), 4)


def _build_overlay_mask(
    element_id: str,
    bbox: list[float],
    padding: float = 0.01,
    color: str = "#ffffff",
) -> dict[str, Any]:
    if len(bbox) < 4:
        bbox = [0.0, 0.0, 0.0, 0.0]
    x0, y0, x1, y1 = [float(value) for value in bbox]
    return {
        "element_id": element_id,
        "bbox": [
            _round(max(0.0, x0 - padding)),
            _round(max(0.0, y0 - padding)),
            _round(min(1.0, x1 + padding)),
            _round(min(1.0, y1 + padding)),
        ],
        "color": color,
    }


def build_overlay_state(
    manifest: dict[str, Any],
    patchsets: list[OverlayPatchRecord],
) -> dict[int, dict[str, Any]]:
    overlay: dict[int, dict[str, Any]] = {}
    element_lookup: dict[str, dict[str, Any]] = {}

    for page in manifest.get("pages", []):
        page_index = page.get("page_index")
        elements: dict[str, dict[str, Any]] = {}
        for element in page.get("elements", []):
            element_id = element.get("element_id")
            text = element.get("text", "")
            if not element_id:
                continue
            elements[element_id] = {
                "text": text,
                "content_hash": _compute_hash(text),
                "bbox": element.get("bbox") or [0.0, 0.0, 0.0, 0.0],
                "style": element.get("style") or {},
                "element_type": element.get("element_type") or "text",
                "base_text": text,
            }
            element_lookup[element_id] = {
                "page_index": page_index,
                "bbox": element.get("bbox") or [0.0, 0.0, 0.0, 0.0],
            }
        if page_index is not None:
            overlay[int(page_index)] = {"primitives": elements, "masks": []}

    masks_by_page: dict[int, dict[str, dict[str, Any]]] = {}

    for patchset in patchsets:
        for op in patchset.ops:
            element_meta = element_lookup.get(op.element_id)
            if not element_meta:
                continue
            page_index = int(element_meta["page_index"])
            page_entry = overlay.get(page_index)
            if page_entry is None:
                continue
            page_map = page_entry.get("primitives", {})
            if op.element_id not in page_map:
                continue
            current = page_map[op.element_id]
            current["text"] = op.new_text
            current["content_hash"] = _compute_hash(op.new_text)
            base_text = current.get("base_text") or ""
            if op.new_text != base_text:
                masks_by_page.setdefault(page_index, {})[op.element_id] = _build_overlay_mask(
                    op.element_id,
                    element_meta["bbox"],
                )

    for page_index, masks in masks_by_page.items():
        if page_index in overlay:
            overlay[page_index]["masks"] = list(masks.values())

    return overlay
