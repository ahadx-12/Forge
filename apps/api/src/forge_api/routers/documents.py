from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from forge_api.schemas.api import DocumentMeta, UploadResponse
from forge_api.services.storage import get_storage_driver


logger = logging.getLogger("forge_api.documents")

router = APIRouter(prefix="/v1/documents", tags=["documents"])


def _document_dir(doc_id: str) -> str:
    return f"documents/{doc_id}"


def _meta_key(doc_id: str) -> str:
    return f"{_document_dir(doc_id)}/meta.json"


def _pdf_key(doc_id: str) -> str:
    return f"{_document_dir(doc_id)}/original.pdf"


def _load_meta(doc_id: str) -> DocumentMeta:
    storage = get_storage_driver()
    meta_key = _meta_key(doc_id)
    if not storage.exists(meta_key):
        raise HTTPException(status_code=404, detail="Document not found")
    meta_path = storage.get_path(meta_key)
    meta_data = json.loads(meta_path.read_text())
    return DocumentMeta(**meta_data)


def _write_meta(doc_id: str, meta: DocumentMeta) -> None:
    storage = get_storage_driver()
    storage.put_bytes(_meta_key(doc_id), meta.model_dump_json().encode("utf-8"), "application/json")


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")
    doc_id = uuid4().hex
    content = await file.read()
    size_bytes = len(content)

    storage = get_storage_driver()
    storage.put_bytes(_pdf_key(doc_id), content, file.content_type)

    meta = DocumentMeta(
        doc_id=doc_id,
        filename=file.filename or "document.pdf",
        size_bytes=size_bytes,
        created_at=datetime.now(timezone.utc),
    )
    _write_meta(doc_id, meta)
    logger.info("Uploaded document %s (%s bytes)", doc_id, size_bytes)
    return UploadResponse(**meta.model_dump())


@router.get("/{doc_id}", response_model=DocumentMeta)
def get_document(doc_id: str) -> DocumentMeta:
    return _load_meta(doc_id)


@router.get("/{doc_id}/download")
def download_document(doc_id: str) -> FileResponse:
    meta = _load_meta(doc_id)
    storage = get_storage_driver()
    pdf_path = storage.get_path(_pdf_key(doc_id))
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=meta.filename,
    )
