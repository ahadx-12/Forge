"""Universal document decoder - converts any doc to structured HTML/JSON."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import fitz

ElementType = Literal["text", "heading", "list_item", "table_cell"]


@dataclass
class DocumentElement:
    """A single document element (text block, heading, etc.)."""

    element_id: str
    element_type: ElementType
    text: str
    bbox: tuple[float, float, float, float]
    style: dict[str, Any]
    lines: list[dict[str, Any]]
    page_index: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "element_id": self.element_id,
            "element_type": self.element_type,
            "text": self.text,
            "bbox": self.bbox,
            "style": self.style,
            "lines": self.lines,
            "page_index": self.page_index,
        }


def _rotated_dimensions(width_pt: float, height_pt: float, rotation: int) -> tuple[float, float]:
    normalized = rotation % 360
    if normalized in (90, 270):
        return height_pt, width_pt
    return width_pt, height_pt


def _rotate_point(x: float, y: float, width_pt: float, height_pt: float, rotation: int) -> tuple[float, float]:
    normalized = rotation % 360
    if normalized == 90:
        return y, width_pt - x
    if normalized == 180:
        return width_pt - x, height_pt - y
    if normalized == 270:
        return height_pt - y, x
    return x, y


def _normalize_bbox(
    bbox_pt: list[float] | tuple[float, float, float, float],
    page_width_pt: float,
    page_height_pt: float,
    rotation: int,
    flip_y: bool,
) -> tuple[float, float, float, float]:
    x0_pt, y0_pt, x1_pt, y1_pt = bbox_pt
    corners = [
        (x0_pt, y0_pt),
        (x1_pt, y0_pt),
        (x1_pt, y1_pt),
        (x0_pt, y1_pt),
    ]
    rotated = [_rotate_point(x, y, page_width_pt, page_height_pt, rotation) for x, y in corners]
    xs = [point[0] for point in rotated]
    ys = [point[1] for point in rotated]
    x0_rot, x1_rot = min(xs), max(xs)
    y0_rot, y1_rot = min(ys), max(ys)
    rotated_width_pt, rotated_height_pt = _rotated_dimensions(page_width_pt, page_height_pt, rotation)

    if flip_y:
        y0_top = rotated_height_pt - y1_rot
        y1_top = rotated_height_pt - y0_rot
    else:
        y0_top = y0_rot
        y1_top = y1_rot

    x0_norm = x0_rot / rotated_width_pt if rotated_width_pt else 0.0
    x1_norm = x1_rot / rotated_width_pt if rotated_width_pt else 0.0
    y0_norm = y0_top / rotated_height_pt if rotated_height_pt else 0.0
    y1_norm = y1_top / rotated_height_pt if rotated_height_pt else 0.0

    x_min, x_max = sorted((x0_norm, x1_norm))
    y_min, y_max = sorted((y0_norm, y1_norm))

    return (
        max(0.0, min(1.0, x_min)),
        max(0.0, min(1.0, y_min)),
        max(0.0, min(1.0, x_max)),
        max(0.0, min(1.0, y_max)),
    )


def _detect_y_origin(blocks: list[dict[str, Any]], page_height_pt: float) -> str:
    if page_height_pt <= 0:
        return "top-left"
    centers: list[float] = []
    min_y0 = page_height_pt
    for block in blocks:
        if block.get("type") != 0:
            continue
        bbox = block.get("bbox") or []
        if len(bbox) < 4:
            continue
        y0 = float(bbox[1])
        y1 = float(bbox[3])
        centers.append((y0 + y1) / 2)
        min_y0 = min(min_y0, y0)
        if len(centers) >= 12:
            break
    if not centers:
        return "top-left"
    avg_center = sum(centers) / len(centers)
    if avg_center > page_height_pt * 0.6 and min_y0 > page_height_pt * 0.4:
        return "bottom-left"
    return "top-left"


class DocumentDecoder:
    """Decode documents into structured elements."""

    def decode_pdf(self, pdf_bytes: bytes) -> dict[str, Any]:
        """
        Decode PDF into structured elements.

        Strategy:
        1. Render each page to high-res PNG (2x zoom = 144 DPI)
        2. Extract text blocks (not character-level)
        3. Normalize coordinates to 0-1 range (top-left origin)
        4. Detect element types (heading vs body text)
        5. Return structured JSON
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []

        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                rotation = page.rotation
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)

                page_width_pt = page.rect.width
                page_height_pt = page.rect.height
                rotated_width_pt, rotated_height_pt = _rotated_dimensions(
                    page_width_pt,
                    page_height_pt,
                    rotation,
                )

                blocks = page.get_text("dict")["blocks"]
                y_origin = _detect_y_origin(blocks, page_height_pt)
                flip_y = y_origin == "bottom-left"
                elements = []

                for block_idx, block in enumerate(blocks):
                    if block.get("type") != 0:
                        continue

                    block_text = ""
                    block_bbox = block["bbox"]
                    lines_payload = []

                    font_size_pt = 12.0
                    is_bold = False
                    is_italic = False
                    color = "#000000"
                    font_family = "Helvetica"
                    line_heights: list[float] = []

                    for line in block.get("lines", []):
                        line_text_parts = []
                        line_spans = []
                        line_bbox = line.get("bbox") or block_bbox
                        if len(line_bbox) >= 4:
                            line_heights.append(float(line_bbox[3] - line_bbox[1]))
                        for span in line.get("spans", []):
                            span_text = span.get("text", "")
                            if not block_text:
                                font_size_pt = float(span.get("size", 12.0))
                                font = span.get("font", "")
                                font_lower = font.lower()
                                is_bold = "bold" in font_lower
                                is_italic = "italic" in font_lower
                                font_family = font or font_family
                                color_int = span.get("color", 0)
                                r = (color_int >> 16) & 0xFF
                                g = (color_int >> 8) & 0xFF
                                b = color_int & 0xFF
                                color = f"#{r:02x}{g:02x}{b:02x}"
                            line_text_parts.append(span_text)
                            span_bbox = span.get("bbox") or line_bbox
                            span_bbox_norm = _normalize_bbox(
                                span_bbox,
                                page_width_pt,
                                page_height_pt,
                                rotation,
                                flip_y,
                            )
                            span_style = {
                                "font_size_pt": float(span.get("size", font_size_pt)),
                                "font_family": span.get("font", font_family),
                                "is_bold": "bold" in span.get("font", "").lower(),
                                "is_italic": "italic" in span.get("font", "").lower(),
                                "color": color,
                            }
                            line_spans.append(
                                {
                                    "text": span_text,
                                    "bbox": span_bbox_norm,
                                    "style": span_style,
                                }
                            )

                            block_text += span_text
                        block_text += "\n"
                        line_text = "".join(line_text_parts)
                        line_bbox_norm = _normalize_bbox(
                            line_bbox,
                            page_width_pt,
                            page_height_pt,
                            rotation,
                            flip_y,
                        )
                        lines_payload.append(
                            {
                                "text": line_text,
                                "bbox": line_bbox_norm,
                                "spans": line_spans,
                            }
                        )

                    block_text = block_text.strip()
                    if not block_text:
                        continue

                    bbox_norm = _normalize_bbox(
                        block_bbox,
                        page_width_pt,
                        page_height_pt,
                        rotation,
                        flip_y,
                    )
                    line_height_pt = sum(line_heights) / len(line_heights) if line_heights else None

                    element_type: ElementType = "text"
                    if font_size_pt > 16:
                        element_type = "heading"
                    elif block_text.startswith("•") or block_text.startswith("-"):
                        element_type = "list_item"

                    element = DocumentElement(
                        element_id=f"p{page_idx}_e{block_idx}",
                        element_type=element_type,
                        text=block_text,
                        bbox=bbox_norm,
                        style={
                            "font_size_pt": font_size_pt,
                            "is_bold": is_bold,
                            "is_italic": is_italic,
                            "color": color,
                            "font_family": font_family,
                            "line_height": line_height_pt,
                        },
                        lines=lines_payload,
                        page_index=page_idx,
                    )

                    elements.append(element.to_dict())

                pages.append(
                    {
                        "page_index": page_idx,
                        "width_pt": rotated_width_pt,
                        "height_pt": rotated_height_pt,
                        "width_px": pix.width,
                        "height_px": pix.height,
                        "rotation": rotation,
                        "background_png": f"page_{page_idx}.png",
                        "background_png_bytes": pix.tobytes("png"),
                        "elements": elements,
                    }
                )
        finally:
            doc.close()

        return {
            "format": "pdf",
            "page_count": len(pages),
            "pages": pages,
        }
