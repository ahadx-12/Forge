from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from forge_api.routers.documents import _meta_key
from forge_api.services.decode_pdf import decode_pdf
from forge_api.services.storage import get_storage_driver


logger = logging.getLogger("forge_api.decode")

router = APIRouter(prefix="/v1/decode", tags=["decode"])


def _pdf_key(doc_id: str) -> str:
    return f"documents/{doc_id}/original.pdf"


def _decode_key(doc_id: str) -> str:
    return f"documents/{doc_id}/decode.json"


@router.get("/{doc_id}")
def decode_document(doc_id: str) -> dict:
    storage = get_storage_driver()
    if not storage.exists(_meta_key(doc_id)):
        raise HTTPException(status_code=404, detail="Document not found")

    pdf_path = storage.get_path(_pdf_key(doc_id))
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    decode_path = storage.get_path(_decode_key(doc_id))
    return decode_pdf(doc_id, pdf_path, decode_path)
