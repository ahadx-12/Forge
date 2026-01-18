from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from forge_api.core.ir.model import PageIR


@dataclass(frozen=True)
class HitTestCandidate:
    id: str
    score: float
    bbox: tuple[float, float, float, float]
    kind: str


@dataclass(frozen=True)
class SpatialIndex:
    cell_size: float
    page_width: float
    page_height: float
    bins: dict[tuple[int, int], list[int]]

    @classmethod
    def build(cls, page: PageIR, cell_size: float = 96.0) -> "SpatialIndex":
        bins: dict[tuple[int, int], list[int]] = {}
        max_x = max(page.width_pt, 1.0)
        max_y = max(page.height_pt, 1.0)
        cols = max(1, math.ceil(max_x / cell_size))
        rows = max(1, math.ceil(max_y / cell_size))

        for idx, primitive in enumerate(page.primitives):
            x0, y0, x1, y1 = primitive.bbox
            start_x = max(0, min(int(x0 // cell_size), cols - 1))
            end_x = max(0, min(int(x1 // cell_size), cols - 1))
            start_y = max(0, min(int(y0 // cell_size), rows - 1))
            end_y = max(0, min(int(y1 // cell_size), rows - 1))
            for cx in range(start_x, end_x + 1):
                for cy in range(start_y, end_y + 1):
                    bins.setdefault((cx, cy), []).append(idx)

        return cls(cell_size=cell_size, page_width=page.width_pt, page_height=page.height_pt, bins=bins)

    def _cells_for_point(self, x: float, y: float) -> Iterable[tuple[int, int]]:
        cx = int(x // self.cell_size)
        cy = int(y // self.cell_size)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                yield (cx + dx, cy + dy)

    def _cells_for_rect(self, x0: float, y0: float, x1: float, y1: float) -> Iterable[tuple[int, int]]:
        start_x = int(min(x0, x1) // self.cell_size)
        end_x = int(max(x0, x1) // self.cell_size)
        start_y = int(min(y0, y1) // self.cell_size)
        end_y = int(max(y0, y1) // self.cell_size)
        for cx in range(start_x, end_x + 1):
            for cy in range(start_y, end_y + 1):
                yield (cx, cy)

    def candidate_indices_for_point(self, x: float, y: float) -> list[int]:
        ordered: dict[int, None] = {}
        for cell in self._cells_for_point(x, y):
            for idx in self.bins.get(cell, []):
                ordered.setdefault(idx, None)
        return list(ordered.keys())

    def candidate_indices_for_rect(self, x0: float, y0: float, x1: float, y1: float) -> list[int]:
        ordered: dict[int, None] = {}
        for cell in self._cells_for_rect(x0, y0, x1, y1):
            for idx in self.bins.get(cell, []):
                ordered.setdefault(idx, None)
        return list(ordered.keys())


def _bbox_center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    x0, y0, x1, y1 = bbox
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


def _intersection_area(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    x_left = max(ax0, bx0)
    y_top = max(ay0, by0)
    x_right = min(ax1, bx1)
    y_bottom = min(ay1, by1)
    if x_right <= x_left or y_bottom <= y_top:
        return 0.0
    return (x_right - x_left) * (y_bottom - y_top)


def hit_test_point(page: PageIR, index: SpatialIndex, x: float, y: float) -> list[HitTestCandidate]:
    z_index_by_id = {primitive.id: primitive.z_index for primitive in page.primitives}
    candidates: list[HitTestCandidate] = []
    for idx in index.candidate_indices_for_point(x, y):
        primitive = page.primitives[idx]
        cx, cy = _bbox_center(primitive.bbox)
        distance = (x - cx) ** 2 + (y - cy) ** 2
        candidates.append(
            HitTestCandidate(
                id=primitive.id,
                score=distance,
                bbox=primitive.bbox,
                kind=primitive.kind,
            )
        )

    candidates.sort(key=lambda item: (item.score, z_index_by_id.get(item.id, 0)))
    return candidates


def hit_test_rect(
    page: PageIR,
    index: SpatialIndex,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> list[HitTestCandidate]:
    z_index_by_id = {primitive.id: primitive.z_index for primitive in page.primitives}
    rect = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    candidates: list[HitTestCandidate] = []
    for idx in index.candidate_indices_for_rect(*rect):
        primitive = page.primitives[idx]
        area = _intersection_area(rect, primitive.bbox)
        if area <= 0:
            continue
        candidates.append(
            HitTestCandidate(
                id=primitive.id,
                score=area,
                bbox=primitive.bbox,
                kind=primitive.kind,
            )
        )

    candidates.sort(key=lambda item: (-item.score, z_index_by_id.get(item.id, 0)))
    return candidates
