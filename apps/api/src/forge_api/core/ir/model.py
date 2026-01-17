from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class TextStyle:
    font: str | None
    size: float
    color: int | None


@dataclass(frozen=True)
class PathStyle:
    stroke_color: Any
    fill_color: Any
    stroke_width: float


@dataclass(frozen=True)
class PrimitiveBase:
    id: str
    kind: Literal["text", "path"]
    bbox: BBox
    z_index: int
    style: Any
    signature_fields: dict[str, Any]


@dataclass(frozen=True)
class TextRun(PrimitiveBase):
    kind: Literal["text"]
    text: str
    style: TextStyle


@dataclass(frozen=True)
class PathPrimitive(PrimitiveBase):
    kind: Literal["path"]
    style: PathStyle


Primitive = TextRun | PathPrimitive


@dataclass(frozen=True)
class PageIR:
    doc_id: str
    page_index: int
    width_pt: float
    height_pt: float
    rotation: int
    primitives: list[Primitive]
