from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from forge_api.services.document_decoder import DocumentDecoder
from forge_api.services.storage import get_storage

logger = logging.getLogger("forge_api.forge_manifest")


def _manifest_key(doc_id: str) -> str:
    return f"docs/{doc_id}/forge/manifest.json"


def load_forge_manifest(doc_id: str) -> dict[str, Any] | None:
    storage = get_storage()
    key = _manifest_key(doc_id)
    if not storage.exists(key):
        return None
    return json.loads(storage.get_bytes(key).decode("utf-8"))


def build_forge_manifest(doc_id: str) -> dict[str, Any]:
    """Build manifest using universal decoder."""
    storage = get_storage()

    existing = load_forge_manifest(doc_id)
    if existing:
        return existing

    pdf_key = f"documents/{doc_id}/original.pdf"
    if not storage.exists(pdf_key):
        raise FileNotFoundError("Document PDF missing")

    pdf_bytes = storage.get_bytes(pdf_key)
    decoder = DocumentDecoder()
    try:
        decoded = decoder.decode_pdf(pdf_bytes)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to decode PDF doc_id=%s error=%s", doc_id, exc)
        raise

    for page_data in decoded["pages"]:
        png_key = f"docs/{doc_id}/pages/{page_data['page_index']}.png"
        storage.put_bytes(
            png_key,
            page_data["background_png_bytes"],
            content_type="image/png",
        )
        del page_data["background_png_bytes"]
        page_data["image_path"] = (
            f"/v1/documents/{doc_id}/forge/pages/{page_data['page_index']}.png"
        )

    manifest = {
        "doc_id": doc_id,
        "page_count": decoded["page_count"],
        "pages": decoded["pages"],
        "generated_at_iso": datetime.now(timezone.utc).isoformat(),
    }

    storage.put_bytes(
        _manifest_key(doc_id),
        json.dumps(manifest, ensure_ascii=False).encode("utf-8"),
    )

    logger.info(
        "forge manifest built doc_id=%s pages=%s elements=%s",
        doc_id,
        len(decoded["pages"]),
        sum(len(page["elements"]) for page in decoded["pages"]),
    )

    return manifest
