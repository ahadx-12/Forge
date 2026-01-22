from __future__ import annotations

from io import BytesIO
import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from forge_api.services.export_pdf import export_pdf_with_overlays
from forge_api.services.storage import get_storage
from forge_api.settings import get_settings

router = APIRouter(prefix="/v1", tags=["export"])

def _load_filename(doc_id: str) -> str:
    storage = get_storage()
    meta_key = f"documents/{doc_id}/meta.json"
    if storage.exists(meta_key):
        try:
            payload = storage.get_bytes(meta_key).decode("utf-8")
            if payload:
                filename = json.loads(payload).get("filename")
                if filename:
                    return filename
        except Exception:
            pass
    return f"{doc_id}.pdf"


def _build_response(doc_id: str, mask_mode: str | None, disposition: str) -> Response:
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
    headers["Content-Disposition"] = disposition
    return StreamingResponse(BytesIO(result.payload), media_type="application/pdf", headers=headers)


@router.post("/export/{doc_id}")
def export_pdf(
    doc_id: str,
    mask_mode: str | None = Query(default=None, description="SOLID or AUTO_BG"),
) -> Response:
    filename = _load_filename(doc_id)
    return _build_response(doc_id, mask_mode, f'inline; filename="{filename}"')


@router.get("/export/{doc_id}")
def export_pdf_get(
    doc_id: str,
    mask_mode: str | None = Query(default=None, description="SOLID or AUTO_BG"),
) -> Response:
    return _build_response(doc_id, mask_mode, f'attachment; filename="{doc_id}.pdf"')
