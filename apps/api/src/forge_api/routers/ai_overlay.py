from __future__ import annotations

import logging
import json
from typing import Any

from fastapi import APIRouter

from forge_api.core.errors import APIError, AIError
from forge_api.schemas.patch import DecodedSelection, OverlayPatchPlan, OverlayPatchPlanRequest
from forge_api.services.forge_manifest import build_forge_manifest
from forge_api.services.openai_client import OpenAIClient
from forge_api.services.storage import get_storage

router = APIRouter(prefix="/v1/ai", tags=["ai"])
logger = logging.getLogger("forge_api.ai_overlay")


SYSTEM_PROMPT = """You are ForgePatchPlanner. You edit document elements while preserving visual design.

CRITICAL RULES:
1. Output ONLY valid JSON. No markdown, no explanations.
2. Only modify elements in the selection. Never invent new element IDs.
3. PRESERVE LAYOUT by default:
   - Keep text length similar unless user explicitly requests longer/shorter text
   - Maintain font size, color, style unless user asks to change them
   - Only provide style overrides if the user explicitly requests them
   - If new text is much longer, intelligently abbreviate or suggest line breaks
4. Consider document context:
   - If editing a heading, keep it concise and bold
   - If editing body text, maintain paragraph flow
   - If editing a list item, keep bullet point format
5. Think about visual harmony:
   - New text should "fit" in the original space
   - Don't break the document's visual rhythm
   - Preserve professional appearance

OUTPUT SCHEMA:
{
  "schema_version": 2,
  "ops": [
    {
      "type": "replace_element",
      "element_id": "p0_e5",
      "old_text": "...",
      "new_text": "...",
      "style_changes": {"font_size_pt": 14.0}
    }
  ],
  "warnings": ["Text may overflow original space"]
}
"""


def build_user_prompt(selection: list[dict[str, Any]], user_request: str, page_context: dict[str, Any]) -> str:
    """Build context-aware prompt for AI."""
    prompt_parts = [
        "DOCUMENT CONTEXT:",
        f"Page dimensions: {page_context['width_pt']}pt × {page_context['height_pt']}pt",
        "",
        "SELECTED ELEMENTS:",
    ]

    for sel in selection:
        bbox_width = (sel["bbox"][2] - sel["bbox"][0]) * page_context["width_pt"]
        bbox_height = (sel["bbox"][3] - sel["bbox"][1]) * page_context["height_pt"]

        prompt_parts.append(
            "\n".join(
                [
                    f"Element ID: {sel['element_id']}",
                    f"Type: {sel.get('element_type', 'text')}",
                    f"Current text: \"{sel['text']}\"",
                    f"Bounding box: {bbox_width:.1f}pt wide × {bbox_height:.1f}pt tall",
                    f"Font size: {sel.get('style', {}).get('font_size_pt', 12)}pt",
                    f"Characters: {len(sel['text'])}",
                ]
            )
        )

    prompt_parts.extend(
        [
            "",
            f"USER REQUEST: {user_request}",
            "",
            "TASK: Modify the selected element(s) according to the user's request.",
            "Keep changes minimal and preserve visual layout unless explicitly asked otherwise.",
            "If text length would increase significantly, intelligently condense or suggest alternatives.",
        ]
    )

    return "\n".join(prompt_parts)


def _decoded_prompt_element(element: dict[str, Any]) -> list[str]:
    style = element.get("style") or {}
    return [
        f"Element ID: {element.get('id')}",
        f"Kind: {element.get('kind')}",
        f"Text: \"{element.get('text', '')}\"",
        f"BBox (norm): {element.get('bbox_norm')}",
        f"Font: {style.get('font_name')}",
        f"Font size: {style.get('font_size_pt')}pt",
        f"Color: {style.get('color')}",
    ]


def _expand_bbox(region: list[float], padding: float = 0.02) -> list[float]:
    if len(region) < 4:
        return [0.0, 0.0, 0.0, 0.0]
    x0, y0, x1, y1 = [float(value) for value in region[:4]]
    return [
        max(0.0, x0 - padding),
        max(0.0, y0 - padding),
        min(1.0, x1 + padding),
        min(1.0, y1 + padding),
    ]


def _intersects_bbox(a: list[float], b: list[float]) -> bool:
    if len(a) < 4 or len(b) < 4:
        return False
    ax0, ay0, ax1, ay1 = [float(value) for value in a[:4]]
    bx0, by0, bx1, by1 = [float(value) for value in b[:4]]
    return max(ax0, bx0) < min(ax1, bx1) and max(ay0, by0) < min(ay1, by1)


def build_decoded_user_prompt(
    decoded_selection: DecodedSelection,
    user_request: str,
    page_context: dict[str, Any],
    decoded_doc: dict[str, Any] | None = None,
) -> str:
    primary_id = decoded_selection.primary_id
    selection_elements = [element.model_dump(mode="json") for element in decoded_selection.elements]
    if not primary_id and selection_elements:
        primary_id = selection_elements[0].get("id")

    primary_element = next(
        (element for element in selection_elements if element.get("id") == primary_id),
        selection_elements[0] if selection_elements else {},
    )
    other_elements = [
        element for element in selection_elements if element.get("id") != primary_element.get("id")
    ]

    prompt_parts = [
        "DOCUMENT CONTEXT:",
        f"Page dimensions: {page_context['width_pt']}pt × {page_context['height_pt']}pt",
        "",
        "PRIMARY ELEMENT:",
        "\n".join(_decoded_prompt_element(primary_element)),
    ]

    if other_elements:
        prompt_parts.append("")
        prompt_parts.append("OTHER SELECTED TEXT:")
        for element in other_elements:
            prompt_parts.append("\n".join(_decoded_prompt_element(element)))

    if decoded_doc and decoded_selection.region_bbox_norm:
        expanded = _expand_bbox(list(decoded_selection.region_bbox_norm))
        neighbors: list[dict[str, Any]] = []
        for page in decoded_doc.get("pages", []):
            if page.get("page_index") != decoded_selection.page_index:
                continue
            for element in page.get("elements", []):
                if element.get("kind") != "text_run":
                    continue
                if element.get("id") in {item.get("id") for item in selection_elements}:
                    continue
                if _intersects_bbox(element.get("bbox_norm") or [], expanded):
                    neighbors.append(element)
                if len(neighbors) >= 50:
                    break
            break
        if neighbors:
            prompt_parts.append("")
            prompt_parts.append("NEARBY CONTEXT:")
            for element in neighbors[:50]:
                prompt_parts.append("\n".join(_decoded_prompt_element(element)))

    prompt_parts.extend(
        [
            "",
            f"USER REQUEST: {user_request}",
            "",
            "TASK: Modify the primary element text first. Use other selected text as context.",
            "Keep changes minimal and preserve visual layout unless explicitly asked otherwise.",
        ]
    )

    return "\n".join(prompt_parts)


def _validate_plan(payload: OverlayPatchPlanRequest, data: dict[str, Any]) -> OverlayPatchPlan:
    plan = OverlayPatchPlan.model_validate(data)
    if plan.schema_version != 2:
        raise ValueError("schema_version must be 2")
    selection_ids = {item.element_id for item in payload.selection}
    selection_text = {item.element_id: item.text for item in payload.selection}
    selection_types = {item.element_id: item.element_type for item in payload.selection}

    for op in plan.ops:
        if op.element_id not in selection_ids:
            raise ValueError("op targets outside selection")
        if op.old_text and op.old_text != selection_text.get(op.element_id):
            raise ValueError("op old_text mismatch")
        if selection_types.get(op.element_id) == "list_item":
            if not op.new_text.startswith("•") and not op.new_text.startswith("-"):
                op.new_text = f"• {op.new_text}"

    return plan


def _estimate_overflow(op: Any, selection_item: dict[str, Any], page_context: dict[str, Any]) -> bool:
    bbox = selection_item.get("bbox") or [0.0, 0.0, 0.0, 0.0]
    if len(bbox) < 4:
        return False
    width_pt = max(0.0, (bbox[2] - bbox[0]) * page_context.get("width_pt", 0.0))
    height_pt = max(0.0, (bbox[3] - bbox[1]) * page_context.get("height_pt", 0.0))
    style = selection_item.get("style") or {}
    font_size = style.get("font_size_pt")
    if not font_size or width_pt <= 0 or height_pt <= 0:
        return False
    avg_char_width = float(font_size) * 0.6
    line_height = float(font_size) * 1.2
    if avg_char_width <= 0 or line_height <= 0:
        return False
    chars_per_line = max(1, int(width_pt / avg_char_width))
    lines = max(1, int(height_pt / line_height))
    capacity = chars_per_line * lines
    return len(op.new_text) > capacity


@router.post("/plan_overlay_patch")
def plan_overlay_patch(payload: OverlayPatchPlanRequest) -> dict[str, Any]:
    if not payload.selection:
        raise APIError(
            status_code=400,
            code="missing_selection",
            message="Selection is required",
            details={"doc_id": payload.doc_id},
        )

    page_context = {"width_pt": 0.0, "height_pt": 0.0}
    try:
        manifest = build_forge_manifest(payload.doc_id)
        page = next(
            (item for item in manifest.get("pages", []) if item.get("page_index") == payload.page_index),
            None,
        )
        if page:
            page_context = {"width_pt": page.get("width_pt", 0.0), "height_pt": page.get("height_pt", 0.0)}
    except FileNotFoundError:
        page_context = {"width_pt": 0.0, "height_pt": 0.0}

    selection_payload = [item.model_dump(mode="json") for item in payload.selection]
    decoded_doc: dict[str, Any] | None = None
    if payload.decoded_selection:
        try:
            storage = get_storage()
            decoded_key = f"documents/{payload.doc_id}/decoded/v1.json"
            if storage.exists(decoded_key):
                decoded_doc = json.loads(storage.get_bytes(decoded_key).decode("utf-8"))
        except Exception:
            decoded_doc = None

    user_prompt = (
        build_decoded_user_prompt(payload.decoded_selection, payload.user_prompt, page_context, decoded_doc)
        if payload.decoded_selection
        else build_user_prompt(selection_payload, payload.user_prompt, page_context)
    )

    client = OpenAIClient()
    for attempt in range(2):
        try:
            data = client.response_json(SYSTEM_PROMPT, user_prompt)
            plan = _validate_plan(payload, data)
            warnings = plan.warnings or []
            selection_map = {item["element_id"]: item for item in selection_payload}
            for op in plan.ops:
                selection_item = selection_map.get(op.element_id)
                if selection_item and _estimate_overflow(op, selection_item, page_context):
                    meta = op.meta or {}
                    meta["overflow"] = True
                    op.meta = meta
                    warnings.append(f"Text may overflow for element {op.element_id}")
            plan.warnings = warnings or None
            return plan.model_dump(mode="json")
        except ValueError as exc:
            if attempt == 0:
                user_prompt = f"{user_prompt}\n\nYou must output only JSON."
                continue
            logger.warning("AI overlay planning failed doc_id=%s error=%s", payload.doc_id, exc)
            raise APIError(
                status_code=422,
                code="ai_planning_failed",
                message="AI overlay planning failed",
                details={"error": str(exc)},
            ) from exc
        except AIError:
            raise
