from __future__ import annotations

import hashlib


def compute_content_hash(text: str | None) -> str:
    value = text or ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def bbox_within_drift(source: list[float], target: list[float], tolerance: float = 5.0) -> bool:
    if len(source) < 4 or len(target) < 4:
        return False
    return all(abs(a - b) <= tolerance for a, b in zip(source, target))
