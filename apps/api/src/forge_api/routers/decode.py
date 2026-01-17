from __future__ import annotations

from fastapi import APIRouter, HTTPException

from forge_api.services.decode_pdf import decode_document

router = APIRouter(prefix="/v1/decode", tags=["decode"])


@router.get("/{doc_id}")
def decode(doc_id: str) -> dict:
    try:
        return decode_document(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
