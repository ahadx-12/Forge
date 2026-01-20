from __future__ import annotations

import logging

from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import ValidationError

from forge_api.core.patch.apply import apply_ops_to_page
from forge_api.core.patch.selection import bbox_within_drift, compute_content_hash
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
    if patchset.selected_ids is not None and not patchset.selected_ids:
        raise APIError(
            status_code=400,
            code="missing_selection",
            message="selected_ids cannot be empty",
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

    patch_log = load_patch_log(parsed.doc_id)
    existing_ops = [op for record in patch_log if record.page_index == patchset.page_index for op in record.ops]
    composite_page, _ = apply_ops_to_page(base_page, existing_ops)

    allowed_ids = None
    if parsed.allowed_targets is not None:
        if not parsed.allowed_targets:
            raise APIError(
                status_code=400,
                code="missing_selection",
                message="allowed_targets cannot be empty",
                details={"doc_id": parsed.doc_id},
            )
        allowed_ids = {target.element_id for target in parsed.allowed_targets}
        for target in parsed.allowed_targets:
            if target.page_index != patchset.page_index:
                raise APIError(
                    status_code=409,
                    code="PATCH_OUT_OF_SCOPE",
                    message="Selection does not match page index",
                    details={"element_id": target.element_id, "page_index": target.page_index},
                )
        primitives_by_id = {primitive.id: primitive for primitive in composite_page.primitives}
        for target in parsed.allowed_targets:
            primitive = primitives_by_id.get(target.element_id)
            if primitive is None:
                raise APIError(
                    status_code=409,
                    code="TARGET_NOT_FOUND",
                    message="Target element no longer exists",
                    details={"element_id": target.element_id},
                )
            if not bbox_within_drift(target.bbox, primitive.bbox, tolerance=5.0):
                raise APIError(
                    status_code=409,
                    code="PATCH_DRIFT",
                    message="Target element bbox drifted",
                    details={"element_id": target.element_id},
                )
            if primitive.kind == "text":
                current_hash = compute_content_hash(primitive.text)
                if target.content_hash != current_hash:
                    raise APIError(
                        status_code=409,
                        code="PATCH_CONFLICT",
                        message="Target element content has changed",
                        details={"element_id": target.element_id},
                    )
            else:
                if target.content_hash not in {"", compute_content_hash("")}:
                    raise APIError(
                        status_code=409,
                        code="PATCH_CONFLICT",
                        message="Target element content hash mismatch",
                        details={"element_id": target.element_id},
                    )

        for op in patchset.ops:
            if op.target_id not in allowed_ids:
                raise APIError(
                    status_code=409,
                    code="PATCH_OUT_OF_SCOPE",
                    message="Patch targets outside selection",
                    details={"target_id": op.target_id},
                )

    validation_ids = list(allowed_ids) if allowed_ids is not None else patchset.selected_ids
    validation = validate_patch_ops(composite_page, patchset.ops, validation_ids)
    if not validation.ok:
        missing_targets = [error for error in validation.errors if error.startswith("Unknown target id")]
        out_of_scope = [error for error in validation.errors if error.endswith("not in selection")]
        if missing_targets:
            raise APIError(
                status_code=409,
                code="patch_target_not_found",
                message="Patch target not found",
                details={"errors": validation.errors},
            )
        if out_of_scope:
            raise APIError(
                status_code=400,
                code="patch_out_of_scope",
                message="Patch targets outside selection",
                details={"errors": validation.errors},
            )
        raise APIError(
            status_code=400,
            code="invalid_patch_ops",
            message="Patch validation failed",
            details={"errors": validation.errors},
        )

    _, results = apply_ops_to_page(composite_page, patchset.ops)
    warnings = [
        f"Text did not fit for {result.target_id}"
        for result in results
        if getattr(result, "did_not_fit", False)
    ]
    try:
        record = append_patchset(
            parsed.doc_id,
            patchset.ops,
            patchset.page_index,
            patchset.rationale_short,
            validation_ids,
            validation.diff_summary,
            results,
            warnings,
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
    applied_ops = [result for result in results if result.ok]
    rejected_ops = [result for result in results if not result.ok]
    return PatchCommitResponse(
        patchset=record,
        patch_log=patch_log,
        applied_ops=applied_ops,
        rejected_ops=rejected_ops,
    )


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
