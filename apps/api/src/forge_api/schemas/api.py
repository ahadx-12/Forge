from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class DocumentMeta(BaseModel):
    doc_id: str
    filename: str
    size_bytes: int
    created_at_iso: datetime
    has_forge_manifest: bool = False
    forge_manifest_url: str | None = None


class UploadResponse(BaseModel):
    document: DocumentMeta
