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
    except Exception as exc:
        logger.error("Failed to decode PDF doc_id=%s error=%s", doc_id, exc)
        raise HTTPException(
            status_code=422,
            detail={
                "code": "decode_failed",
                "message": "This PDF could not be decoded. It may be corrupted or encrypted.",
                "suggestion": "Try re-saving the PDF or removing password protection.",
            },
        ) from exc


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
    except Exception as exc:
        logger.error("Failed to decode PDF doc_id=%s error=%s", doc_id, exc)
        raise HTTPException(
            status_code=422,
            detail={
                "code": "decode_failed",
                "message": "This PDF could not be decoded. It may be corrupted or encrypted.",
                "suggestion": "Try re-saving the PDF or removing password protection.",
            },
        ) from exc
    patchsets = load_overlay_patch_log(doc_id)
    overlay_state = build_overlay_state(manifest, patchsets)
    page_overlay = overlay_state.get(page_index, {})
    page_primitives = page_overlay.get("primitives", {})
    entries = [
        {
            "element_id": element_id,
            "text": data["text"],
            "content_hash": data["content_hash"],
        }
        for element_id, data in page_primitives.items()
    ]
    manifest_pages = {page.get("page_index"): page for page in manifest.get("pages", [])}
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
    except Exception as exc:
        logger.error("Failed to decode PDF doc_id=%s error=%s", doc_id, exc)
        raise HTTPException(
            status_code=422,
            detail={
                "code": "decode_failed",
                "message": "This PDF could not be decoded. It may be corrupted or encrypted.",
                "suggestion": "Try re-saving the PDF or removing password protection.",
            },
        ) from exc

    selection_ids = {item.element_id for item in payload.selection}
    selection_hashes = {item.element_id: item.content_hash for item in payload.selection}

    manifest_pages = {page.get("page_index"): page for page in manifest.get("pages", [])}
    manifest_page = manifest_pages.get(payload.page_index)
    if manifest_page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    manifest_ids = {item.get("element_id") for item in manifest_page.get("elements", [])}

    overlay_state = build_overlay_state(manifest, load_overlay_patch_log(doc_id))
    page_primitives = overlay_state.get(payload.page_index, {}).get("primitives", {})

    for op in payload.ops:
        if op.element_id not in selection_ids:
            raise APIError(
                status_code=409,
                code="PATCH_OUT_OF_SCOPE",
                message="Overlay ops must target the selection",
                details={"element_id": op.element_id},
            )
        if op.element_id not in manifest_ids:
            raise APIError(
                status_code=409,
                code="patch_target_not_found",
                message="Overlay target not found",
                details={"element_id": op.element_id},
            )
        expected_hash = selection_hashes.get(op.element_id)
        current_hash = page_primitives.get(op.element_id, {}).get("content_hash")
        if expected_hash and current_hash and current_hash != expected_hash:
            raise APIError(
                status_code=409,
                code="PATCH_CONFLICT",
                message="Overlay target content has changed",
                details={"element_id": op.element_id},
            )

    record = append_overlay_patchset(doc_id, payload.ops)
    overlay_state = build_overlay_state(manifest, load_overlay_patch_log(doc_id))
    page_overlay = overlay_state.get(payload.page_index, {})
    page_primitives = page_overlay.get("primitives", {})
    entries = [
        {
            "element_id": element_id,
            "text": data["text"],
            "content_hash": data["content_hash"],
        }
        for element_id, data in page_primitives.items()
    ]
    return OverlayPatchCommitResponse(
        patchset=record,
        overlay=entries,
        masks=page_overlay.get("masks", []),
    )
