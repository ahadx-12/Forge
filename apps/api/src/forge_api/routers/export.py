from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from forge_api.services.export_pdf import export_pdf_with_overlays
from forge_api.settings import get_settings

router = APIRouter(prefix="/v1", tags=["export"])


@router.post("/export/{doc_id}")
def export_pdf(
    doc_id: str,
    mask_mode: str | None = Query(default=None, description="SOLID or AUTO_BG"),
) -> Response:
    try:
        settings = get_settings()
        mode = (mask_mode or settings.FORGE_EXPORT_MASK_MODE).upper()
        if mode not in {"SOLID", "AUTO_BG"}:
            raise HTTPException(status_code=400, detail="Invalid mask_mode")
        result = export_pdf_with_overlays(doc_id, mask_mode=mode)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    headers = {"X-Forge-Mask-Mode": result.mask_mode}
    if result.warning:
        headers["X-Forge-Mask-Warning"] = result.warning
    return Response(content=result.payload, media_type="application/pdf", headers=headers)
