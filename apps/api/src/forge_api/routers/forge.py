from __future__ import annotations

import logging
from io import BytesIO

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from forge_api.core.errors import APIError
from forge_api.schemas.patch import OverlayPatchCommitRequest, OverlayPatchCommitResponse
from forge_api.services.forge_manifest import build_forge_manifest
from forge_api.services.forge_overlay import (
    append_overlay_patchset,
    build_overlay_state,
    load_overlay_patch_log,
)
from forge_api.services.storage import get_storage

router = APIRouter(prefix="/v1/documents", tags=["forge"])
logger = logging.getLogger("forge_api.forge")


@router.get("/{doc_id}/forge/manifest")
def get_forge_manifest(doc_id: str) -> dict:
    try:
        return build_forge_manifest(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc


@router.get("/{doc_id}/forge/pages/{page_index}.png")
def get_forge_page(doc_id: str, page_index: int) -> StreamingResponse:
    try:
        manifest = build_forge_manifest(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    if page_index < 0 or page_index >= manifest.get("page_count", 0):
        raise HTTPException(status_code=404, detail="Page not found")
    storage = get_storage()
    key = f"docs/{doc_id}/pages/{page_index}.png"
    if not storage.exists(key):
        raise HTTPException(status_code=404, detail="Page image not found")
    return StreamingResponse(BytesIO(storage.get_bytes(key)), media_type="image/png")


@router.get("/{doc_id}/forge/overlay")
def get_forge_overlay(doc_id: str, page_index: int = Query(..., ge=0)) -> dict:
    try:
        manifest = build_forge_manifest(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    patchsets = load_overlay_patch_log(doc_id)
    overlay_state = build_overlay_state(manifest, patchsets)
    page_overlay = overlay_state.get(page_index, {})
    page_primitives = page_overlay.get("primitives", {})
    entries = [
        {
            "forge_id": forge_id,
            "text": data["text"],
            "content_hash": data["content_hash"],
            "bbox_px": data.get("bbox") or [0.0, 0.0, 0.0, 0.0],
        }
        for forge_id, data in page_primitives.items()
    ]
    manifest_pages = {page.get("index"): page for page in manifest.get("pages", [])}
    manifest_page = manifest_pages.get(page_index, {})
    return {
        "doc_id": doc_id,
        "page_index": page_index,
        "overlay": entries,
        "masks": page_overlay.get("masks", []),
        "page_image_width_px": manifest_page.get("width_px"),
        "page_image_height_px": manifest_page.get("height_px"),
        "pdf_box_width_pt": manifest_page.get("width_pt"),
        "pdf_box_height_pt": manifest_page.get("height_pt"),
        "rotation": manifest_page.get("rotation"),
        "used_box": "cropbox",
    }


@router.post("/{doc_id}/forge/overlay/commit", response_model=OverlayPatchCommitResponse)
def commit_forge_overlay(doc_id: str, payload: OverlayPatchCommitRequest) -> OverlayPatchCommitResponse:
    if payload.doc_id != doc_id:
        raise APIError(
            status_code=409,
            code="DOC_ID_MISMATCH",
            message="Document ID mismatch",
            details={"path_doc_id": doc_id, "payload_doc_id": payload.doc_id},
        )
    if not payload.selection:
        raise APIError(
            status_code=400,
            code="missing_selection",
            message="Selection is required",
            details={"doc_id": doc_id},
        )
    if not payload.ops:
        raise APIError(
            status_code=400,
            code="empty_patchset",
            message="No overlay ops provided",
            details={"doc_id": doc_id},
        )

    try:
        manifest = build_forge_manifest(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc

    selection_ids = {item.forge_id for item in payload.selection}
    selection_hashes = {item.forge_id: item.content_hash for item in payload.selection}
    if any(item.page_index != payload.page_index for item in payload.ops):
        raise APIError(
            status_code=409,
            code="PATCH_OUT_OF_SCOPE",
            message="Overlay ops must target the requested page",
            details={"page_index": payload.page_index},
        )

    manifest_pages = {page.get("index"): page for page in manifest.get("pages", [])}
    manifest_page = manifest_pages.get(payload.page_index)
    if manifest_page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    manifest_ids = {item.get("forge_id") for item in manifest_page.get("items", [])}

    overlay_state = build_overlay_state(manifest, load_overlay_patch_log(doc_id))

    for op in payload.ops:
        if op.forge_id not in selection_ids:
            raise APIError(
                status_code=409,
                code="PATCH_OUT_OF_SCOPE",
                message="Overlay ops must target the selection",
                details={"forge_id": op.forge_id},
            )
        if op.forge_id not in manifest_ids:
            raise APIError(
                status_code=409,
                code="patch_target_not_found",
                message="Overlay target not found",
                details={"forge_id": op.forge_id},
            )
        expected_hash = selection_hashes.get(op.forge_id)
        if expected_hash and op.old_hash != expected_hash:
            raise APIError(
                status_code=409,
                code="PATCH_CONFLICT",
                message="Overlay op hash does not match selection",
                details={"forge_id": op.forge_id},
            )
        page_primitives = overlay_state.get(payload.page_index, {}).get("primitives", {})
        current_hash = page_primitives.get(op.forge_id, {}).get("content_hash")
        if current_hash and current_hash != op.old_hash:
            raise APIError(
                status_code=409,
                code="PATCH_CONFLICT",
                message="Overlay target content has changed",
                details={"forge_id": op.forge_id},
            )

    record = append_overlay_patchset(doc_id, payload.ops)
    overlay_state = build_overlay_state(manifest, load_overlay_patch_log(doc_id))
    page_overlay = overlay_state.get(payload.page_index, {})
    page_primitives = page_overlay.get("primitives", {})
    entries = [
        {
            "forge_id": forge_id,
            "text": data["text"],
            "content_hash": data["content_hash"],
            "bbox_px": data.get("bbox") or [0.0, 0.0, 0.0, 0.0],
        }
        for forge_id, data in page_primitives.items()
    ]
    return OverlayPatchCommitResponse(
        patchset=record,
        overlay=entries,
        masks=page_overlay.get("masks", []),
    )
