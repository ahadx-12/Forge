from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from pydantic import TypeAdapter

from forge_api.core.errors import AIError
from forge_api.core.patch.selection import compute_content_hash
from forge_api.schemas.patch import PatchOp, PatchPlanRequest, PatchProposal
from forge_api.services.openai_client import OpenAIClient


SYSTEM_PROMPT = """You are a patch planner for Forge. Output JSON only.
Rules:
- Only target selection.element_id. Do not use any other IDs.
- Never invent new IDs or geometry.
- Only output ops with op=\"set_style\" or op=\"replace_text\".
- For set_style, you may set stroke_color, stroke_width_pt, fill_color, opacity.
- For replace_text, you must include new_text, policy (FIT_IN_BOX or OVERFLOW_NOTICE),
  and old_text exactly as provided in selection.text.
- Output must be strict JSON of the form: {\"ops\":[...],\"rationale_short\":\"...\"}.
"""


STRICT_RETRY_PROMPT = """Your previous output was invalid. Output ONLY valid JSON.
Do not include markdown, comments, or extra keys.
Ensure the ID is selection.element_id and old_text matches selection.text.
"""


def _validate_ops(payload: dict[str, Any], selection_id: str, selection_text: str | None, page_index: int) -> PatchProposal:
    if "ops" not in payload or "rationale_short" not in payload:
        raise ValueError("Missing keys")
    adapter = TypeAdapter(PatchOp)
    ops = [adapter.validate_python(item) for item in payload["ops"]]
    for op in ops:
        if op.target_id != selection_id:
            raise AIError(
                status_code=400,
                code="AI_OUT_OF_SCOPE",
                message="AI proposed an out-of-scope patch",
                details={"target_id": op.target_id, "selection_id": selection_id},
            )
        if op.op == "replace_text":
            if selection_text is None:
                raise AIError(
                    status_code=400,
                    code="AI_OUT_OF_SCOPE",
                    message="AI proposed text replacement for non-text selection",
                    details={"selection_id": selection_id},
                )
            if op.old_text is None or op.old_text != selection_text:
                raise AIError(
                    status_code=400,
                    code="AI_OUT_OF_SCOPE",
                    message="AI old_text mismatch",
                    details={
                        "selection_id": selection_id,
                        "content_hash": compute_content_hash(selection_text),
                    },
                )
    return PatchProposal(
        patchset_id=str(uuid4()),
        ops=ops,
        rationale_short=str(payload["rationale_short"]),
        page_index=page_index,
    )


def plan_patch(request: PatchPlanRequest, primitives: list[dict[str, Any]]) -> PatchProposal:
    if request.selection is None:
        raise AIError(
            status_code=400,
            code="MISSING_SELECTION",
            message="Selection is required for AI patch planning",
            details={"doc_id": request.doc_id, "page_index": request.page_index},
        )

    selection_id = request.selection.element_id
    selection_text = request.selection.text
    if request.selected_ids is not None and selection_id not in request.selected_ids:
        raise AIError(
            status_code=400,
            code="AI_OUT_OF_SCOPE",
            message="Selection does not match allowed targets",
            details={"selection_id": selection_id, "selected_ids": request.selected_ids},
        )

    if request.selected_primitives:
        selection_context = request.selected_primitives
    else:
        selection_context = [
            {
                "id": primitive["id"],
                "kind": primitive["kind"],
                "bbox": primitive["bbox"],
                "text": primitive.get("text"),
                "style": primitive.get("style"),
            }
            for primitive in primitives
            if primitive["id"] == selection_id
        ]

    prompt = {
        "doc_id": request.doc_id,
        "page_index": request.page_index,
        "instruction": request.user_instruction,
        "selection": request.selection.model_dump(),
        "selection_context": selection_context,
    }

    client = OpenAIClient()
    response_payload = client.response_json(
        system=SYSTEM_PROMPT,
        user=json.dumps(prompt, ensure_ascii=False),
    )

    try:
        return _validate_ops(response_payload, selection_id, selection_text, request.page_index)
    except AIError:
        raise
    except Exception as exc:
        retry_payload = client.response_json(
            system=SYSTEM_PROMPT + "\n" + STRICT_RETRY_PROMPT,
            user=json.dumps(prompt, ensure_ascii=False),
        )
        try:
            return _validate_ops(retry_payload, selection_id, selection_text, request.page_index)
        except AIError:
            raise
        except Exception as retry_exc:
            raise AIError(
                status_code=400,
                code="ai_invalid_output",
                message="AI returned an invalid patch plan",
                details={"error": str(exc), "retry_error": str(retry_exc)},
            ) from retry_exc
