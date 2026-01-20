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
) -> dict[int, dict[str, dict[str, str]]]:
    overlay: dict[int, dict[str, dict[str, str]]] = {}
    for page in manifest.get("pages", []):
        page_index = page.get("index")
        items = {}
        for item in page.get("items", []):
            forge_id = item.get("forge_id")
            text = item.get("text", "")
            if not forge_id:
                continue
            items[forge_id] = {
                "text": text,
                "content_hash": _compute_hash(text),
            }
        if page_index is not None:
            overlay[int(page_index)] = items

    for patchset in patchsets:
        for op in patchset.ops:
            page_map = overlay.get(op.page_index)
            if page_map is None:
                continue
            if op.forge_id not in page_map:
                continue
            page_map[op.forge_id] = {
                "text": op.new_text,
                "content_hash": _compute_hash(op.new_text),
            }

    return overlay
