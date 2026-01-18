from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


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
    applied_font_size_pt: float | None = None
    overflow: bool | None = None


class PatchsetRecord(BaseModel):
    patchset_id: str
    created_at_iso: datetime
    ops: list[PatchOp]
    page_index: int
    rationale_short: str | None = None
    selected_ids: list[str] | None = None
    diff_summary: list[PatchDiffEntry] = Field(default_factory=list)
    results: list[PatchOpResult] = Field(default_factory=list)


class PatchsetListResponse(BaseModel):
    doc_id: str
    patchsets: list[PatchsetRecord]


class PatchCommitRequest(BaseModel):
    doc_id: str
    patchset: PatchsetInput


class PatchCommitResponse(BaseModel):
    patchset: PatchsetRecord
    patch_log: list[PatchsetRecord]


class PatchPlanRequest(BaseModel):
    doc_id: str
    page_index: int
    selected_ids: list[str]
    user_instruction: str
    candidates: list[str] | None = None


class PatchProposal(BaseModel):
    patchset_id: str
    ops: list[PatchOp]
    rationale_short: str
    page_index: int


class PatchPlanResponse(BaseModel):
    proposed_patchset: PatchProposal
