from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from forge_api.schemas.decoded import DecodedDocument
from forge_api.services.pdf_decode_v1 import decode_pdf_to_decoded_document
from forge_api.services.storage import get_storage

router = APIRouter(prefix="/v1/documents", tags=["decoded"])
logger = logging.getLogger(__name__)


def _pdf_path(doc_id: str) -> str:
    return f"documents/{doc_id}/original.pdf"


def _decoded_path(doc_id: str) -> str:
    return f"documents/{doc_id}/decoded/v1.json"


@router.get("/{doc_id}/decoded", response_model=DecodedDocument)
def get_decoded_document(doc_id: str, v: int = 1) -> DecodedDocument:
    if v != 1:
        raise HTTPException(status_code=400, detail="Unsupported decoded version")

    storage = get_storage()
    decoded_key = _decoded_path(doc_id)
    if storage.exists(decoded_key):
        payload = json.loads(storage.get_bytes(decoded_key).decode("utf-8"))
        try:
            return DecodedDocument(**payload)
        except ValidationError as exc:
            logger.warning("Cached decoded payload invalid for doc_id=%s error=%s", doc_id, exc)

    pdf_key = _pdf_path(doc_id)
    if not storage.exists(pdf_key):
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        pdf_bytes = storage.get_bytes(pdf_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Failed to read PDF for doc_id=%s", doc_id)
        raise HTTPException(status_code=500, detail="Failed to read document") from exc

    try:
        decoded = decode_pdf_to_decoded_document(doc_id, pdf_bytes)
    except Exception as exc:
        logger.exception("Decode failed for doc_id=%s", doc_id)
        raise HTTPException(status_code=422, detail=f"Decode failed for document {doc_id}: {exc}") from exc

    storage.put_bytes(
        decoded_key,
        decoded.model_dump_json().encode("utf-8"),
        content_type="application/json",
    )
    return decoded
