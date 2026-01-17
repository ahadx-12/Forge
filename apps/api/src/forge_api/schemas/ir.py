from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class IRPrimitive(BaseModel):
    id: str
    kind: Literal["text", "path"]
    bbox: list[float]
    z_index: int
    style: dict[str, Any]
    signature_fields: dict[str, Any]
    text: str | None = None


class IRPage(BaseModel):
    doc_id: str
    page_index: int
    width_pt: float
    height_pt: float
    rotation: int
    primitives: list[IRPrimitive]


class HitTestPoint(BaseModel):
    x: float
    y: float


class HitTestRect(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class HitTestRequest(BaseModel):
    point: HitTestPoint | None = None
    rect: HitTestRect | None = None

    @model_validator(mode="after")
    def validate_choice(self) -> "HitTestRequest":
        if (self.point is None and self.rect is None) or (self.point is not None and self.rect is not None):
            raise ValueError("Provide exactly one of point or rect")
        return self


class HitTestCandidate(BaseModel):
    id: str
    score: float
    bbox: list[float]
    kind: Literal["text", "path"]


class HitTestResponse(BaseModel):
    doc_id: str
    page_index: int
    candidates: list[HitTestCandidate] = Field(default_factory=list)
