from __future__ import annotations

from dataclasses import dataclass

from forge_api.schemas.ir import IRPage
from forge_api.schemas.patch import PatchDiffEntry, PatchOp, PatchReplaceText, PatchSetStyle


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str]
    diff_summary: list[PatchDiffEntry]


def _validate_color(value: list[float] | int | None) -> bool:
    if value is None:
        return True
    if isinstance(value, int):
        return value >= 0
    if not isinstance(value, list):
        return False
    if len(value) not in (3, 4):
        return False
    for channel in value:
        if not isinstance(channel, (int, float)):
            return False
        if channel < 0 or channel > 1:
            return False
    return True


def validate_patch_ops(page: IRPage, ops: list[PatchOp], selected_ids: list[str] | None) -> ValidationResult:
    errors: list[str] = []
    diff_summary: list[PatchDiffEntry] = []
    valid_ids = {primitive.id: primitive for primitive in page.primitives}
    allowed_ids = set(selected_ids) if selected_ids is not None else {op.target_id for op in ops if op.target_id}

    for op in ops:
        if not op.target_id or not op.target_id.strip():
            errors.append("Missing target id")
            continue
        if op.target_id not in valid_ids:
            errors.append(f"Unknown target id {op.target_id}")
            continue
        if selected_ids is not None and op.target_id not in allowed_ids:
            errors.append(f"Target id {op.target_id} not in selection")
            continue

        primitive = valid_ids[op.target_id]
        if op.op == "set_style":
            if primitive.kind != "path":
                errors.append(f"set_style not allowed for kind {primitive.kind} on {op.target_id}")
                continue
            if not _validate_color(op.stroke_color):
                errors.append(f"Invalid stroke_color for {op.target_id}")
                continue
            if not _validate_color(op.fill_color):
                errors.append(f"Invalid fill_color for {op.target_id}")
                continue
            if op.stroke_width_pt is not None and op.stroke_width_pt < 0:
                errors.append(f"stroke_width_pt must be non-negative for {op.target_id}")
                continue
            if op.opacity is not None and (op.opacity < 0 or op.opacity > 1):
                errors.append(f"opacity out of range for {op.target_id}")
                continue
            changed_fields = [
                name
                for name, value in {
                    "stroke_color": op.stroke_color,
                    "stroke_width_pt": op.stroke_width_pt,
                    "fill_color": op.fill_color,
                    "opacity": op.opacity,
                }.items()
                if value is not None
            ]
            diff_summary.append(PatchDiffEntry(target_id=op.target_id, changed_fields=changed_fields))
        elif op.op == "replace_text":
            if primitive.kind != "text":
                errors.append(f"replace_text not allowed for kind {primitive.kind} on {op.target_id}")
                continue
            changed_fields = ["text", "policy"]
            diff_summary.append(PatchDiffEntry(target_id=op.target_id, changed_fields=changed_fields))
        else:
            errors.append(f"Unsupported op {op.op}")

    return ValidationResult(ok=not errors, errors=errors, diff_summary=diff_summary)
