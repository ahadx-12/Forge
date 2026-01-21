from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any
from uuid import uuid4

from forge_api.schemas.patch import OverlayPatchOp, OverlayPatchRecord
from forge_api.services.storage import get_patch_storage


def _overlay_log_key(doc_id: str) -> str:
    return f"docs/{doc_id}/forge/overlay_patches.json"


def _overlay_custom_key(doc_id: str) -> str:
    return f"docs/{doc_id}/forge/overlay_custom.json"


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


def load_overlay_custom_entries(doc_id: str) -> dict[str, dict[str, Any]]:
    storage = get_patch_storage()
    key = _overlay_custom_key(doc_id)
    if not storage.exists(key):
        return {}
    payload = json.loads(storage.get_bytes(key).decode("utf-8"))
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        return {item["element_id"]: item for item in payload if isinstance(item, dict) and item.get("element_id")}
    return {}


def upsert_overlay_custom_entries(doc_id: str, entries: list[dict[str, Any]]) -> None:
    if not entries:
        return
    storage = get_patch_storage()
    existing = load_overlay_custom_entries(doc_id)
    for entry in entries:
        element_id = entry.get("element_id")
        if not element_id:
            continue
        existing[element_id] = entry
    payload = list(existing.values())
    storage.put_bytes(
        _overlay_custom_key(doc_id),
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8"),
    )


def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _round(value: float) -> float:
    return round(float(value), 4)


def _bbox_iou(a: list[float], b: list[float]) -> float:
    if len(a) < 4 or len(b) < 4:
        return 0.0
    ax0, ay0, ax1, ay1 = [float(value) for value in a[:4]]
    bx0, by0, bx1, by1 = [float(value) for value in b[:4]]
    inter_x0 = max(ax0, bx0)
    inter_y0 = max(ay0, by0)
    inter_x1 = min(ax1, bx1)
    inter_y1 = min(ay1, by1)
    inter_w = max(0.0, inter_x1 - inter_x0)
    inter_h = max(0.0, inter_y1 - inter_y0)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    union = area_a + area_b - inter_area
    if union <= 0:
        return 0.0
    return inter_area / union


def _text_similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def resolve_overlay_selection(
    selection: list[dict[str, Any]],
    manifest_elements: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    resolved: dict[str, dict[str, Any]] = {}
    for item in selection:
        element_id = item.get("element_id")
        if not element_id:
            continue
        if any(element_id == candidate.get("element_id") for candidate in manifest_elements):
            resolved[element_id] = next(
                candidate for candidate in manifest_elements if candidate.get("element_id") == element_id
            )
            continue
        best_score = 0.0
        best_match: dict[str, Any] | None = None
        for candidate in manifest_elements:
            iou = _bbox_iou(item.get("bbox") or [], candidate.get("bbox") or [])
            similarity = _text_similarity(item.get("text", ""), candidate.get("text", ""))
            score = iou * 0.7 + similarity * 0.3
            if score > best_score:
                best_score = score
                best_match = candidate
        if best_match and best_score >= 0.25:
            resolved[element_id] = best_match
    return resolved


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
    custom_entries: dict[str, dict[str, Any]] | None = None,
) -> dict[int, dict[str, Any]]:
    overlay: dict[int, dict[str, Any]] = {}
    element_lookup: dict[str, dict[str, Any]] = {}

    if custom_entries is None:
        custom_entries = {}

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

    for element_id, entry in custom_entries.items():
        page_index = entry.get("page_index")
        if page_index is None:
            continue
        page_index = int(page_index)
        page_entry = overlay.setdefault(page_index, {"primitives": {}, "masks": []})
        base_text = entry.get("text", "")
        page_entry["primitives"][element_id] = {
            "text": base_text,
            "content_hash": _compute_hash(base_text),
            "bbox": entry.get("bbox") or [0.0, 0.0, 0.0, 0.0],
            "style": entry.get("style") or {},
            "element_type": entry.get("element_type") or "text",
            "base_text": base_text,
            "resolved_element_id": entry.get("resolved_element_id"),
        }
        element_lookup[element_id] = {
            "page_index": page_index,
            "bbox": entry.get("bbox") or [0.0, 0.0, 0.0, 0.0],
        }

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
