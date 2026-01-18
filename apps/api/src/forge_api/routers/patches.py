from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from forge_api.core.patch.apply import apply_ops_to_page
from forge_api.core.patch.validate import validate_patch_ops
from forge_api.schemas.ir import IRPage
from forge_api.schemas.patch import PatchCommitRequest, PatchCommitResponse, PatchsetListResponse
from forge_api.services.ir_pdf import get_base_ir_page
from forge_api.services.patch_store import append_patchset, load_patch_log, revert_last_patchset

router = APIRouter(prefix="/v1", tags=["patches"])


@router.post("/patch/commit", response_model=PatchCommitResponse)
def commit_patch(payload: PatchCommitRequest) -> PatchCommitResponse:
    patchset = payload.patchset
    if not patchset.ops:
        raise HTTPException(status_code=400, detail="Patchset is empty")

    base_page = get_base_ir_page(payload.doc_id, patchset.page_index)
    validation = validate_patch_ops(base_page, patchset.ops, patchset.selected_ids)
    if not validation.ok:
        raise HTTPException(status_code=400, detail=validation.errors)

    _, results = apply_ops_to_page(base_page, patchset.ops)
    record = append_patchset(
        payload.doc_id,
        patchset.ops,
        patchset.page_index,
        patchset.rationale_short,
        patchset.selected_ids,
        validation.diff_summary,
        results,
    )
    patch_log = load_patch_log(payload.doc_id)
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
