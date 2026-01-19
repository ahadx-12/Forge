from __future__ import annotations

import logging

from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import ValidationError

from forge_api.core.patch.apply import apply_ops_to_page
from forge_api.core.patch.validate import validate_patch_ops
from forge_api.core.errors import APIError, StorageError
from forge_api.core.request_context import get_request_id
from forge_api.schemas.ir import IRPage
from forge_api.schemas.patch import PatchCommitRequest, PatchCommitResponse, PatchsetListResponse
from forge_api.services.ir_pdf import get_base_ir_page
from forge_api.services.patch_store import append_patchset, load_patch_log, revert_last_patchset

router = APIRouter(prefix="/v1", tags=["patches"])
logger = logging.getLogger("forge_api")


@router.post("/patch/commit", response_model=PatchCommitResponse)
def commit_patch(payload: dict, request: Request) -> PatchCommitResponse:
    request_id = get_request_id(request)
    try:
        parsed = PatchCommitRequest.model_validate(payload)
    except ValidationError as exc:
        raise APIError(
            status_code=400,
            code="invalid_patch_payload",
            message="Invalid patch payload",
            details={"errors": exc.errors()},
        ) from exc

    patchset = parsed.patchset
    if not patchset.ops:
        raise APIError(
            status_code=400,
            code="empty_patchset",
            message="Patchset is empty",
            details={"doc_id": parsed.doc_id},
        )

    logger.info(
        "Patch commit request_id=%s doc_id=%s page_index=%s stage=commit",
        request_id,
        parsed.doc_id,
        patchset.page_index,
    )

    try:
        base_page = get_base_ir_page(parsed.doc_id, patchset.page_index)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    except IndexError as exc:
        raise HTTPException(status_code=404, detail="Page not found") from exc

    validation = validate_patch_ops(base_page, patchset.ops, patchset.selected_ids)
    if not validation.ok:
        missing_targets = [error for error in validation.errors if error.startswith("Unknown target id")]
        if missing_targets:
            raise APIError(
                status_code=409,
                code="patch_target_not_found",
                message="Patch target not found",
                details={"errors": validation.errors},
            )
        raise APIError(
            status_code=400,
            code="invalid_patch_ops",
            message="Patch validation failed",
            details={"errors": validation.errors},
        )

    _, results = apply_ops_to_page(base_page, patchset.ops)
    try:
        record = append_patchset(
            parsed.doc_id,
            patchset.ops,
            patchset.page_index,
            patchset.rationale_short,
            patchset.selected_ids,
            validation.diff_summary,
            results,
        )
        patch_log = load_patch_log(parsed.doc_id)
    except (ClientError, OSError, ValueError) as exc:
        logger.warning(
            "Patch commit storage failure request_id=%s doc_id=%s page_index=%s stage=commit error=%s",
            request_id,
            parsed.doc_id,
            patchset.page_index,
            exc.__class__.__name__,
        )
        raise StorageError(
            status_code=502,
            code="storage_error",
            message="Storage operation failed while committing patch",
            details={"doc_id": parsed.doc_id},
        ) from exc
    return PatchCommitResponse(patchset=record, patch_log=patch_log)


@router.get("/patches/{doc_id}", response_model=PatchsetListResponse)
def list_patchsets(doc_id: str) -> PatchsetListResponse:
    return PatchsetListResponse(doc_id=doc_id, patchsets=load_patch_log(doc_id))


@router.post("/patch/revert_last", response_model=PatchsetListResponse)
def revert_last(doc_id: str = Query(...)) -> PatchsetListResponse:
    patchsets = revert_last_patchset(doc_id)
    return PatchsetListResponse(doc_id=doc_id, patchsets=patchsets)


@router.get("/composite/ir/{doc_id}", response_model=IRPage)
def get_composite_ir(doc_id: str, page: int = Query(..., ge=0)) -> IRPage:
    base_page = get_base_ir_page(doc_id, page)
    patchsets = load_patch_log(doc_id)
    ops = []
    for patchset in patchsets:
        if patchset.page_index == page:
            ops.extend(patchset.ops)
    composite, _ = apply_ops_to_page(base_page, ops)
    return composite
