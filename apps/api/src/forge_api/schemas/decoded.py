from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DecodedStats(BaseModel):
    text_runs: int
    paths: int
    images: int
    unknown: int

    model_config = ConfigDict(extra="forbid")


class DecodedElementBase(BaseModel):
    id: str
    kind: Literal["text_run", "path", "image", "unknown"]
    bbox_norm: tuple[float, float, float, float]
    source: Literal["pdf"]

    model_config = ConfigDict(extra="forbid")

    @field_validator("bbox_norm")
    @classmethod
    def clamp_bbox_norm(cls, value: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        if len(value) != 4:
            raise ValueError("bbox_norm must have 4 values")
        x0, y0, x1, y1 = (float(item) for item in value)
        x_min, x_max = sorted((x0, x1))
        y_min, y_max = sorted((y0, y1))

        def _clamp(item: float) -> float:
            return max(0.0, min(1.0, item))

        return (
            _clamp(x_min),
            _clamp(y_min),
            _clamp(x_max),
            _clamp(y_max),
        )


class TextRunElement(DecodedElementBase):
    kind: Literal["text_run"]
    text: str
    font_name: str | None = None
    font_size_pt: float | None = None
    color: str | None = None
    rotation: float | None = None
    baseline_norm: tuple[float, float] | None = None


class PathElement(DecodedElementBase):
    kind: Literal["path"]
    stroke_color: str | None = None
    stroke_width_pt: float | None = None
    fill_color: str | None = None
    commands: list[dict]
    is_closed: bool | None = None


class ImageElement(DecodedElementBase):
    kind: Literal["image"]
    name: str | None = None
    width_pt: float | None = None
    height_pt: float | None = None


class UnknownElement(DecodedElementBase):
    kind: Literal["unknown"]
    note: str


DecodedElement = Annotated[
    TextRunElement | PathElement | ImageElement | UnknownElement,
    Field(discriminator="kind"),
]


class DecodedPage(BaseModel):
    page_index: int
    width_pt: float
    height_pt: float
    elements: list[DecodedElement]
    stats: DecodedStats
    needs_ocr_fallback: bool = False

    model_config = ConfigDict(extra="forbid")


class DecodedDocument(BaseModel):
    doc_id: str
    type: Literal["pdf"]
    version: Literal["v1"]
    page_count: int
    pages: list[DecodedPage]
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
