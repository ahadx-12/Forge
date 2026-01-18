from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from forge_api.core.ir.spatial_index import SpatialIndex, hit_test_point, hit_test_rect
from forge_api.schemas.ir import HitTestRequest, HitTestResponse, IRPage
from forge_api.services.ir_pdf import get_page_ir

router = APIRouter(prefix="/v1", tags=["ir"])


@router.get("/ir/{doc_id}", response_model=IRPage)
def get_ir(doc_id: str, page: int = Query(..., ge=0)) -> IRPage:
    try:
        return get_page_ir(doc_id, page)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    except IndexError as exc:
        raise HTTPException(status_code=404, detail="Page not found") from exc


@router.post("/hittest/{doc_id}", response_model=HitTestResponse)
def hit_test(doc_id: str, payload: HitTestRequest, page: int = Query(..., ge=0)) -> HitTestResponse:
    try:
        page_ir = get_page_ir(doc_id, page)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    except IndexError as exc:
        raise HTTPException(status_code=404, detail="Page not found") from exc

    index = SpatialIndex.build(page_ir)
    if payload.point:
        candidates = hit_test_point(page_ir, index, payload.point.x, payload.point.y)
    else:
        rect = payload.rect
        candidates = hit_test_rect(page_ir, index, rect.x0, rect.y0, rect.x1, rect.y1)

    return HitTestResponse(
        doc_id=doc_id,
        page_index=page,
        candidates=[
            {
                "id": candidate.id,
                "score": candidate.score,
                "bbox": list(candidate.bbox),
                "kind": candidate.kind,
            }
            for candidate in candidates
        ],
    )
