from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from forge_api.services.export_pdf import export_pdf_with_overlays

router = APIRouter(prefix="/v1", tags=["export"])


@router.post("/export/{doc_id}")
def export_pdf(doc_id: str) -> Response:
    try:
        payload = export_pdf_with_overlays(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    return Response(content=payload, media_type="application/pdf")
