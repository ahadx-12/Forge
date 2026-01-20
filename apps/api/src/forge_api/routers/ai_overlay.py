from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter

from forge_api.core.errors import APIError, AIError
from forge_api.schemas.patch import OverlayPatchPlan, OverlayPatchPlanRequest
from forge_api.services.openai_client import OpenAIClient

router = APIRouter(prefix="/v1/ai", tags=["ai"])
logger = logging.getLogger("forge_api.ai_overlay")


SYSTEM_PROMPT = "You are ForgePatchPlanner. You output only JSON. No markdown. No explanations."


def _build_user_prompt(payload: OverlayPatchPlanRequest) -> str:
    selection_lines = []
    for item in payload.selection:
        selection_lines.append(
            "\n".join(
                [
                    f"- forge_id: {item.forge_id}",
                    f'  text: "{item.text}"',
                    f'  old_hash: "{item.content_hash}"',
                    f"  bbox: {item.bbox}",
                ]
            )
        )
    selection_block = "\n".join(selection_lines)
    rules = "\n".join(
        [
            "RULES:",
            "- Output ONLY JSON.",
            f"- ops may only target forge_id in [{', '.join([item.forge_id for item in payload.selection])}]",
            "- Each op must include: type, page_index, forge_id, old_hash, new_text",
            "- Do not include any other IDs.",
            "- Do not change bbox.",
            "- Do not add new elements.",
        ]
    )
    return "\n".join(
        [
            "You will be given SELECTED ELEMENTS and a USER REQUEST.",
            "Return a JSON object:",
            "{",
            '  "schema_version": 1,',
            '  "ops": [...]',
            "}",
            "",
            "SELECTED ELEMENTS:",
            selection_block,
            "",
            "USER REQUEST:",
            f'"{payload.user_prompt}"',
            "",
            rules,
        ]
    )


def _parse_plan(raw_text: str) -> dict[str, Any]:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("AI response was not valid JSON") from exc


def _validate_plan(payload: OverlayPatchPlanRequest, data: dict[str, Any]) -> OverlayPatchPlan:
    plan = OverlayPatchPlan.model_validate(data)
    if plan.schema_version != 1:
        raise ValueError("schema_version must be 1")
    selection_ids = {item.forge_id for item in payload.selection}
    selection_hashes = {item.forge_id: item.content_hash for item in payload.selection}
    for op in plan.ops:
        if op.forge_id not in selection_ids:
            raise ValueError("op targets outside selection")
        if op.old_hash != selection_hashes.get(op.forge_id):
            raise ValueError("op old_hash mismatch")
        if op.page_index != payload.page_index:
            raise ValueError("op page_index mismatch")
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
    client = OpenAIClient()
    user_prompt = _build_user_prompt(payload)
    for attempt in range(2):
        try:
            raw = client.response_json(SYSTEM_PROMPT, user_prompt)
            data = _parse_plan(raw)
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
