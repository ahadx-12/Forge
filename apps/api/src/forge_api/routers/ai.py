from __future__ import annotations

from fastapi import APIRouter, HTTPException

from forge_api.schemas.patch import PatchPlanRequest, PatchPlanResponse
from forge_api.services.ai_patch_planner import plan_patch
from forge_api.services.ir_pdf import get_base_ir_page

router = APIRouter(prefix="/v1/ai", tags=["ai"])


@router.post("/plan_patch", response_model=PatchPlanResponse)
def plan_patch_route(payload: PatchPlanRequest) -> PatchPlanResponse:
    try:
        page_ir = get_base_ir_page(payload.doc_id, payload.page_index)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    except IndexError as exc:
        raise HTTPException(status_code=404, detail="Page not found") from exc

    primitives = [primitive.model_dump() for primitive in page_ir.primitives]
    try:
        proposal = plan_patch(payload, primitives)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="AI planning failed") from exc

    return PatchPlanResponse(proposed_patchset=proposal)
