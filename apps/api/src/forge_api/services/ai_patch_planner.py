from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from pydantic import TypeAdapter

from forge_api.core.errors import AIError, UpstreamAIError
from forge_api.schemas.patch import PatchOp, PatchPlanRequest, PatchProposal
from forge_api.services.openai_client import OpenAIClient


SYSTEM_PROMPT = """You are a patch planner for Forge. Output JSON only.
Rules:
- Only refer to IDs in selected_ids or candidates.
- Never invent new IDs or geometry.
- Only output ops with op=\"set_style\" or op=\"replace_text\".
- For set_style, you may set stroke_color, stroke_width_pt, fill_color, opacity.
- For replace_text, you must include new_text and policy (FIT_IN_BOX or OVERFLOW_NOTICE).
- Output must be strict JSON of the form: {\"ops\":[...],\"rationale_short\":\"...\"}.
"""


STRICT_RETRY_PROMPT = """Your previous output was invalid. Output ONLY valid JSON.
Do not include markdown, comments, or extra keys.
Ensure all IDs come from allowed lists.
"""


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("{"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    return text[start : end + 1]


def _validate_ops(payload: dict[str, Any], allowed_ids: set[str], page_index: int) -> PatchProposal:
    if "ops" not in payload or "rationale_short" not in payload:
        raise ValueError("Missing keys")
    adapter = TypeAdapter(PatchOp)
    ops = [adapter.validate_python(item) for item in payload["ops"]]
    for op in ops:
        if op.target_id not in allowed_ids:
            raise ValueError("Invalid target id")
    return PatchProposal(
        patchset_id=str(uuid4()),
        ops=ops,
        rationale_short=str(payload["rationale_short"]),
        page_index=page_index,
    )


def plan_patch(request: PatchPlanRequest, primitives: list[dict[str, Any]]) -> PatchProposal:
    allowed_ids = set(request.selected_ids)
    if request.candidates:
        allowed_ids.update(request.candidates)
    if not allowed_ids:
        raise AIError(
            status_code=400,
            code="missing_selection",
            message="Selection or candidates are required for AI patch planning",
            details={"doc_id": request.doc_id, "page_index": request.page_index},
        )

    selection_context = [
        {
            "id": primitive["id"],
            "kind": primitive["kind"],
            "bbox": primitive["bbox"],
            "text": primitive.get("text"),
            "style": primitive.get("style"),
        }
        for primitive in primitives
        if primitive["id"] in allowed_ids
    ]

    prompt = {
        "doc_id": request.doc_id,
        "page_index": request.page_index,
        "selected_ids": request.selected_ids,
        "candidates": request.candidates or [],
        "instruction": request.user_instruction,
        "primitives": selection_context,
    }

    client = OpenAIClient()
    response_text = client.response_json(
        system=SYSTEM_PROMPT,
        user=json.dumps(prompt, ensure_ascii=False),
    )

    try:
        payload = json.loads(_extract_json(response_text))
        return _validate_ops(payload, allowed_ids, request.page_index)
    except Exception as exc:
        retry_text = client.response_json(
            system=SYSTEM_PROMPT + "\n" + STRICT_RETRY_PROMPT,
            user=json.dumps(prompt, ensure_ascii=False),
        )
        try:
            payload = json.loads(_extract_json(retry_text))
            return _validate_ops(payload, allowed_ids, request.page_index)
        except Exception as retry_exc:
            raise UpstreamAIError(
                status_code=502,
                code="ai_invalid_response",
                message="AI returned an invalid patch plan",
                details={"error": str(exc), "retry_error": str(retry_exc)},
            ) from retry_exc
