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
    page_index: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "element_id": self.element_id,
            "element_type": self.element_type,
            "text": self.text,
            "bbox": self.bbox,
            "style": self.style,
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

    y0_top = rotated_height_pt - y1_rot
    y1_top = rotated_height_pt - y0_rot

    x0_norm = x0_rot / rotated_width_pt if rotated_width_pt else 0.0
    x1_norm = x1_rot / rotated_width_pt if rotated_width_pt else 0.0
    y0_norm = y0_top / rotated_height_pt if rotated_height_pt else 0.0
    y1_norm = y1_top / rotated_height_pt if rotated_height_pt else 0.0

    return (x0_norm, y0_norm, x1_norm, y1_norm)


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
                elements = []

                for block_idx, block in enumerate(blocks):
                    if block.get("type") != 0:
                        continue

                    block_text = ""
                    block_bbox = block["bbox"]

                    font_size_pt = 12.0
                    is_bold = False
                    color = "#000000"
                    font_family = "Helvetica"

                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            if not block_text:
                                font_size_pt = float(span.get("size", 12.0))
                                font = span.get("font", "")
                                font_lower = font.lower()
                                is_bold = "bold" in font_lower
                                font_family = font or font_family
                                color_int = span.get("color", 0)
                                r = (color_int >> 16) & 0xFF
                                g = (color_int >> 8) & 0xFF
                                b = color_int & 0xFF
                                color = f"#{r:02x}{g:02x}{b:02x}"

                            block_text += span.get("text", "")
                        block_text += "\n"

                    block_text = block_text.strip()
                    if not block_text:
                        continue

                    bbox_norm = _normalize_bbox(block_bbox, page_width_pt, page_height_pt, rotation)

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
                            "color": color,
                            "font_family": font_family,
                        },
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
