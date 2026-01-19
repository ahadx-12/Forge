from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from forge_api.services.decode_pdf import decode_document

router = APIRouter(prefix="/v1/decode", tags=["decode"])
logger = logging.getLogger("forge_api.decode")


@router.get("/{doc_id}")
def decode(doc_id: str) -> dict:
    try:
        return decode_document(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    except ValueError as exc:
        logger.error("Decode failed for doc_id=%s: %s", doc_id, exc)
        raise HTTPException(status_code=500, detail=f"Decode failed for document {doc_id}: {exc}") from exc
