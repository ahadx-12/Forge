from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse, Response

from forge_api.schemas.api import DocumentMeta, UploadResponse
from forge_api.settings import get_settings
from forge_api.services.storage import get_storage

router = APIRouter(prefix="/v1/documents", tags=["documents"])


def _document_dir(doc_id: str) -> str:
    return f"documents/{doc_id}"


def _meta_path(doc_id: str) -> str:
    return f"{_document_dir(doc_id)}/meta.json"


def _pdf_path(doc_id: str) -> str:
    return f"{_document_dir(doc_id)}/original.pdf"


def _load_meta(doc_id: str) -> DocumentMeta:
    storage = get_storage()
    meta_key = _meta_path(doc_id)
    if not storage.exists(meta_key):
        raise HTTPException(status_code=404, detail="Document not found")
    meta_bytes = storage.get_bytes(meta_key)
    payload = json.loads(meta_bytes.decode("utf-8"))
    return DocumentMeta(**payload)


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    if file.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    content = await file.read()
    settings = get_settings()
    max_bytes = settings.FORGE_MAX_UPLOAD_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="File exceeds upload limit")
    doc_id = str(uuid4())
    storage = get_storage()
    storage.put_bytes(_pdf_path(doc_id), content, content_type=file.content_type)
    meta = DocumentMeta(
        doc_id=doc_id,
        filename=file.filename or "uploaded.pdf",
        size_bytes=len(content),
        created_at_iso=datetime.now(timezone.utc),
    )
    storage.put_bytes(_meta_path(doc_id), meta.model_dump_json().encode("utf-8"))
    return UploadResponse(document=meta)


@router.get("/{doc_id}", response_model=DocumentMeta)
def get_document(doc_id: str) -> DocumentMeta:
    return _load_meta(doc_id)


@router.get("/{doc_id}/download")
def download_document(doc_id: str) -> Response:
    storage = get_storage()
    pdf_key = _pdf_path(doc_id)
    if not storage.exists(pdf_key):
        raise HTTPException(status_code=404, detail="Document not found")
    if hasattr(storage, "get_path"):
        path = storage.get_path(pdf_key)
        return FileResponse(path, media_type="application/pdf", filename=f"{doc_id}.pdf")
    pdf_bytes = storage.get_bytes(pdf_key)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc_id}.pdf"'},
    )
