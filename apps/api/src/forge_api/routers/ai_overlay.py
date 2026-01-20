from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from forge_api.core.errors import APIError, AIError
from forge_api.schemas.patch import OverlayPatchPlan, OverlayPatchPlanRequest
from forge_api.services.forge_manifest import build_forge_manifest
from forge_api.services.openai_client import OpenAIClient

router = APIRouter(prefix="/v1/ai", tags=["ai"])
logger = logging.getLogger("forge_api.ai_overlay")


SYSTEM_PROMPT = """You are ForgePatchPlanner. You edit document elements while preserving visual design.

CRITICAL RULES:
1. Output ONLY valid JSON. No markdown, no explanations.
2. Only modify elements in the selection. Never invent new element IDs.
3. PRESERVE LAYOUT by default:
   - Keep text length similar unless user explicitly requests longer/shorter text
   - Maintain font size, color, style unless user asks to change them
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

    user_prompt = build_user_prompt(
        [item.model_dump(mode="json") for item in payload.selection],
        payload.user_prompt,
        page_context,
    )

    client = OpenAIClient()
    for attempt in range(2):
        try:
            data = client.response_json(SYSTEM_PROMPT, user_prompt)
            plan = _validate_plan(payload, data)
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
