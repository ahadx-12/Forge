from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from forge_api.core.errors import AIError
from forge_api.core.request_context import get_request_id
from forge_api.schemas.patch import PatchPlanRequest, PatchPlanResponse
from forge_api.services.ai_patch_planner import plan_patch
from forge_api.services.ir_pdf import get_base_ir_page

router = APIRouter(prefix="/v1/ai", tags=["ai"])
logger = logging.getLogger("forge_api")


@router.post("/plan_patch", response_model=PatchPlanResponse)
def plan_patch_route(payload: PatchPlanRequest, request: Request) -> PatchPlanResponse:
    request_id = get_request_id(request)
    if payload.selection is None:
        raise AIError(
            status_code=400,
            code="MISSING_SELECTION",
            message="Selection is required for AI patch planning",
            details={"doc_id": payload.doc_id, "page_index": payload.page_index},
        )
    try:
        page_ir = get_base_ir_page(payload.doc_id, payload.page_index)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    except IndexError as exc:
        raise HTTPException(status_code=404, detail="Page not found") from exc

    primitives = [primitive.model_dump() for primitive in page_ir.primitives]
    try:
        logger.info(
            "AI plan_patch request_id=%s doc_id=%s page_index=%s stage=planning",
            request_id,
            payload.doc_id,
            payload.page_index,
        )
        proposal = plan_patch(payload, primitives)
    except AIError as exc:
        logger.warning(
            "AI plan_patch failed request_id=%s doc_id=%s page_index=%s stage=planning code=%s",
            request_id,
            payload.doc_id,
            payload.page_index,
            exc.code,
        )
        raise
    except Exception as exc:
        raise AIError(
            status_code=500,
            code="ai_planning_failed",
            message="AI planning failed",
            details={"doc_id": payload.doc_id, "page_index": payload.page_index},
        ) from exc

    return PatchPlanResponse(proposed_patchset=proposal)
