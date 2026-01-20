from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import ConfigDict

from pydantic import BaseModel, Field, model_validator


class SelectionFingerprint(BaseModel):
    element_id: str
    page_index: int
    content_hash: str
    bbox: list[float]
    parent_id: str | None = None


class SelectionSnapshot(BaseModel):
    element_id: str
    page_index: int
    bbox: list[float]
    text: str | None = None
    font_name: str | None = None
    font_size: float | None = None
    parent_id: str | None = None
    content_hash: str | None = None


class PatchOpBase(BaseModel):
    op: str
    target_id: str


class PatchSetStyle(PatchOpBase):
    op: Literal["set_style"]
    stroke_color: list[float] | int | None = None
    stroke_width_pt: float | None = None
    fill_color: list[float] | int | None = None
    opacity: float | None = None

    @model_validator(mode="after")
    def validate_fields(self) -> "PatchSetStyle":
        if (
            self.stroke_color is None
            and self.stroke_width_pt is None
            and self.fill_color is None
            and self.opacity is None
        ):
            raise ValueError("set_style requires at least one style field")
        if self.stroke_width_pt is not None and self.stroke_width_pt < 0:
            raise ValueError("stroke_width_pt must be non-negative")
        if self.opacity is not None and (self.opacity < 0 or self.opacity > 1):
            raise ValueError("opacity must be between 0 and 1")
        return self


class PatchReplaceText(PatchOpBase):
    op: Literal["replace_text"]
    new_text: str
    policy: Literal["FIT_IN_BOX", "OVERFLOW_NOTICE"]
    old_text: str | None = None


PatchOp = PatchSetStyle | PatchReplaceText


class PatchsetInput(BaseModel):
    ops: list[PatchOp]
    page_index: int
    selected_ids: list[str] | None = None
    rationale_short: str | None = None


class PatchDiffEntry(BaseModel):
    target_id: str
    changed_fields: list[str]
    geometry_changed: bool = False


class PatchOpResult(BaseModel):
    target_id: str
    ok: bool = True
    code: str | None = None
    details: dict[str, object] | None = None
    applied_font_size_pt: float | None = None
    overflow: bool | None = None
    did_not_fit: bool | None = None
    font_adjusted: bool | None = None
    bbox_adjusted: bool | None = None
    warnings: list[dict[str, object]] = Field(default_factory=list)


class PatchsetRecord(BaseModel):
    patchset_id: str
    created_at_iso: datetime
    ops: list[PatchOp]
    page_index: int
    rationale_short: str | None = None
    selected_ids: list[str] | None = None
    diff_summary: list[PatchDiffEntry] = Field(default_factory=list)
    results: list[PatchOpResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PatchsetListResponse(BaseModel):
    doc_id: str
    patchsets: list[PatchsetRecord]


class PatchCommitRequest(BaseModel):
    doc_id: str
    patchset: PatchsetInput
    allowed_targets: list[SelectionFingerprint] | None = None
    base_ir_version: str | None = None


class PatchCommitResponse(BaseModel):
    patchset: PatchsetRecord
    patch_log: list[PatchsetRecord]
    applied_ops: list[PatchOpResult] | None = None
    rejected_ops: list[PatchOpResult] | None = None


class PatchPlanRequest(BaseModel):
    doc_id: str
    page_index: int
    selected_ids: list[str] | None = None
    user_instruction: str
    candidates: list[str] | None = None
    selected_primitives: list[dict[str, object]] | None = None
    selection: SelectionSnapshot | None = None


class PatchProposal(BaseModel):
    schema_version: str = "v1"
    patchset_id: str
    ops: list[PatchOp]
    rationale_short: str
    page_index: int


class PatchPlanResponse(BaseModel):
    proposed_patchset: PatchProposal


class OverlaySelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    forge_id: str
    text: str
    content_hash: str
    bbox: list[float]


class OverlayPatchOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["replace_overlay_text"]
    page_index: int
    forge_id: str
    old_hash: str
    new_text: str


class OverlayPatchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    ops: list[OverlayPatchOp]


class OverlayPatchPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    page_index: int
    selection: list[OverlaySelection]
    user_prompt: str


class OverlayPatchCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    page_index: int
    selection: list[OverlaySelection]
    ops: list[OverlayPatchOp]


class OverlayPatchRecord(BaseModel):
    patch_id: str
    created_at_iso: datetime
    ops: list[OverlayPatchOp]


class OverlayEntry(BaseModel):
    forge_id: str
    text: str
    content_hash: str


class OverlayPatchCommitResponse(BaseModel):
    patchset: OverlayPatchRecord
    overlay: list[OverlayEntry]
