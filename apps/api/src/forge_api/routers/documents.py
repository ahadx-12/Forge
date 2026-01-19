from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
import logging
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse, Response

from forge_api.schemas.api import DocumentMeta, UploadResponse
from forge_api.settings import get_settings
from forge_api.services.storage import get_storage

router = APIRouter(prefix="/v1/documents", tags=["documents"])
logger = logging.getLogger(__name__)


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


def _parse_range_header(range_header: str, size: int) -> tuple[int, int] | None:
    if not range_header:
        return None
    if not range_header.startswith("bytes="):
        return None
    range_spec = range_header.replace("bytes=", "", 1).strip()
    if not range_spec:
        return None
    if "," in range_spec:
        range_spec = range_spec.split(",", 1)[0]
    start_str, end_str = range_spec.split("-", 1)
    try:
        if start_str == "":
            suffix = int(end_str)
            if suffix <= 0:
                return None
            start = max(size - suffix, 0)
            end = size - 1
        else:
            start = int(start_str)
            end = int(end_str) if end_str else size - 1
    except ValueError:
        return None
    if start < 0 or end < 0:
        return None
    if start >= size:
        return None
    if end >= size:
        end = size - 1
    if start > end:
        return None
    return start, end


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
def download_document(doc_id: str, request: Request) -> Response:
    storage = get_storage()
    pdf_key = _pdf_path(doc_id)
    filename = f"{doc_id}.pdf"
    try:
        meta = _load_meta(doc_id)
        if meta.filename:
            filename = meta.filename
    except HTTPException:
        pass

    try:
        size = storage.get_size(pdf_key)
    except FileNotFoundError as exc:
        logger.warning("Document download missing", extra={"doc_id": doc_id, "key": pdf_key, "error": str(exc)})
        raise HTTPException(status_code=404, detail="Document not found") from exc
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Document download failed", extra={"doc_id": doc_id, "key": pdf_key})
        raise HTTPException(status_code=500, detail="Failed to fetch document") from exc

    range_header = request.headers.get("range")
    if range_header:
        byte_range = _parse_range_header(range_header, size)
        if not byte_range:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
        start, end = byte_range
        try:
            pdf_bytes = storage.get_bytes_range(pdf_key, start, end)
        except FileNotFoundError as exc:
            logger.warning("Document download missing", extra={"doc_id": doc_id, "key": pdf_key, "error": str(exc)})
            raise HTTPException(status_code=404, detail="Document not found") from exc
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Document download failed", extra={"doc_id": doc_id, "key": pdf_key})
            raise HTTPException(status_code=500, detail="Failed to fetch document") from exc
        return Response(
            content=pdf_bytes,
            status_code=206,
            media_type="application/pdf",
            headers={
                "Content-Range": f"bytes {start}-{end}/{size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(end - start + 1),
                "Content-Disposition": f'inline; filename="{filename}"',
            },
        )

    try:
        pdf_bytes = storage.get_bytes(pdf_key)
    except FileNotFoundError as exc:
        logger.warning("Document download missing", extra={"doc_id": doc_id, "key": pdf_key, "error": str(exc)})
        raise HTTPException(status_code=404, detail="Document not found") from exc
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Document download failed", extra={"doc_id": doc_id, "key": pdf_key})
        raise HTTPException(status_code=500, detail="Failed to fetch document") from exc
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
            "Accept-Ranges": "bytes",
        },
    )
