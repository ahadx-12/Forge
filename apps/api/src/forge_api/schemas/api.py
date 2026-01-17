from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentMeta(BaseModel):
    doc_id: str
    filename: str
    size_bytes: int = Field(..., ge=0)
    created_at: datetime


class UploadResponse(DocumentMeta):
    pass


class ErrorResponse(BaseModel):
    detail: str
