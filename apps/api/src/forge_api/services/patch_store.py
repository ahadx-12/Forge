from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from forge_api.schemas.patch import PatchDiffEntry, PatchOpResult, PatchsetRecord
from forge_api.services.storage import get_storage


def _patch_log_key(doc_id: str) -> str:
    return f"documents/{doc_id}/patches.json"


def load_patch_log(doc_id: str) -> list[PatchsetRecord]:
    storage = get_storage()
    key = _patch_log_key(doc_id)
    if not storage.exists(key):
        return []
    payload = json.loads(Path(storage.get_path(key)).read_text())
    return [PatchsetRecord.model_validate(item) for item in payload]


def save_patch_log(doc_id: str, patchsets: list[PatchsetRecord]) -> None:
    storage = get_storage()
    key = _patch_log_key(doc_id)
    payload = [record.model_dump(mode="json") for record in patchsets]
    storage.put_bytes(key, json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def append_patchset(
    doc_id: str,
    ops,
    page_index: int,
    rationale_short: str | None,
    selected_ids: list[str] | None,
    diff_summary: list[PatchDiffEntry],
    results: list[PatchOpResult],
) -> PatchsetRecord:
    patchsets = load_patch_log(doc_id)
    record = PatchsetRecord(
        patchset_id=str(uuid4()),
        created_at_iso=datetime.now(timezone.utc),
        ops=ops,
        page_index=page_index,
        rationale_short=rationale_short,
        selected_ids=selected_ids,
        diff_summary=diff_summary,
        results=results,
    )
    patchsets.append(record)
    save_patch_log(doc_id, patchsets)
    return record


def revert_last_patchset(doc_id: str) -> list[PatchsetRecord]:
    patchsets = load_patch_log(doc_id)
    if patchsets:
        patchsets.pop()
        save_patch_log(doc_id, patchsets)
    return patchsets
