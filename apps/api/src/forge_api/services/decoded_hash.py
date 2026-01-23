from __future__ import annotations

import hashlib
import json
from typing import Any


def _normalize_for_hash(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, int):
        return value
    if isinstance(value, (list, tuple)):
        return [_normalize_for_hash(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_for_hash(value[key]) for key in sorted(value.keys())}
    return value


def stable_element_id(
    doc_id: str,
    page_index: int,
    kind: str,
    bbox_norm: tuple[float, float, float, float],
    payload_core_fields: dict[str, Any],
) -> str:
    payload = {
        "doc_id": doc_id,
        "page_index": page_index,
        "kind": kind,
        "bbox_norm": bbox_norm,
        "payload": payload_core_fields,
    }
    normalized = _normalize_for_hash(payload)
    serialized = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"{kind[:2]}_{digest[:10]}"


def stable_content_hash(
    kind: str,
    bbox_norm: tuple[float, float, float, float],
    payload_core_fields: dict[str, Any],
) -> str:
    payload = {
        "kind": kind,
        "bbox_norm": bbox_norm,
        "payload": payload_core_fields,
    }
    normalized = _normalize_for_hash(payload)
    serialized = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
