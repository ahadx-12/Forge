from __future__ import annotations

import logging
from typing import Any, Iterable

import fitz

from forge_api.schemas.decoded import (
    DecodedDocument,
    DecodedPage,
    DecodedStats,
    ImageElement,
    PathElement,
    TextRunElement,
)
from forge_api.services.decoded_hash import stable_content_hash, stable_element_id

logger = logging.getLogger(__name__)


def _color_int_to_hex(color: int | None) -> str | None:
    if color is None:
        return None
    if isinstance(color, bool):
        return None
    if isinstance(color, int):
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"
    return None


def _color_tuple_to_hex(color: Iterable[float] | None) -> str | None:
    if color is None:
        return None
    try:
        values = list(color)
    except TypeError:
        return None
    if len(values) < 3:
        return None
    r, g, b = values[:3]
    return f"#{int(max(0, min(1, r)) * 255):02x}{int(max(0, min(1, g)) * 255):02x}{int(max(0, min(1, b)) * 255):02x}"


def _pdf_point_to_top_left(x: float, y: float, page_height_pt: float) -> tuple[float, float]:
    # PyMuPDF (fitz) text/drawing coordinates already use top-left origin.
    return x, y


def _normalize_bbox(
    bbox: Iterable[float],
    page_width_pt: float,
    page_height_pt: float,
) -> tuple[float, float, float, float]:
    # Normalized bboxes use a top-left origin (y grows downward) to align with DOM coordinates.
    items = list(bbox)
    if len(items) < 4 or page_width_pt <= 0 or page_height_pt <= 0:
        return (0.0, 0.0, 0.0, 0.0)
    x0, y0, x1, y1 = (float(item) for item in items[:4])
    x_min, x_max = sorted((x0, x1))
    y_min, y_max = sorted((y0, y1))
    x0_norm = x_min / page_width_pt
    x1_norm = x_max / page_width_pt
    y0_norm = y_min / page_height_pt
    y1_norm = y_max / page_height_pt

    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    return (
        _clamp(x0_norm),
        _clamp(y0_norm),
        _clamp(x1_norm),
        _clamp(y1_norm),
    )


def _commands_from_drawing(items: list[tuple[Any, ...]], page_height_pt: float) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    for item in items:
        if not item:
            continue
        op = item[0]
        if op == "m" and len(item) >= 2:
            x, y = _pdf_point_to_top_left(float(item[1][0]), float(item[1][1]), page_height_pt)
            commands.append({"op": "M", "x": x, "y": y})
        elif op == "l" and len(item) >= 3:
            x0, y0 = _pdf_point_to_top_left(float(item[1][0]), float(item[1][1]), page_height_pt)
            x1, y1 = _pdf_point_to_top_left(float(item[2][0]), float(item[2][1]), page_height_pt)
            commands.append({"op": "M", "x": x0, "y": y0})
            commands.append({"op": "L", "x": x1, "y": y1})
        elif op == "re" and len(item) >= 2:
            rect = item[1]
            if isinstance(rect, fitz.Rect):
                x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
            else:
                x0, y0, x1, y1 = rect[:4]
            x0_t, y0_t = _pdf_point_to_top_left(float(x0), float(y0), page_height_pt)
            x1_t, y1_t = _pdf_point_to_top_left(float(x1), float(y1), page_height_pt)
            commands.append({"op": "R", "x0": x0_t, "y0": y0_t, "x1": x1_t, "y1": y1_t})
        elif op == "c" and len(item) >= 4:
            p1, p2, p3 = item[1], item[2], item[3]
            x1, y1 = _pdf_point_to_top_left(float(p1[0]), float(p1[1]), page_height_pt)
            x2, y2 = _pdf_point_to_top_left(float(p2[0]), float(p2[1]), page_height_pt)
            x3, y3 = _pdf_point_to_top_left(float(p3[0]), float(p3[1]), page_height_pt)
            commands.append({
                "op": "C",
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "x3": x3,
                "y3": y3,
            })
    return commands


def _path_hint_from_commands(commands: list[dict[str, Any]], limit: int = 3) -> str | None:
    if not commands:
        return None
    parts: list[str] = []
    for command in commands[:limit]:
        op = command.get("op")
        if op == "M":
            parts.append(f"M{command.get('x'):.1f},{command.get('y'):.1f}")
        elif op == "L":
            parts.append(f"L{command.get('x'):.1f},{command.get('y'):.1f}")
        elif op == "R":
            parts.append(
                "R"
                f"{command.get('x0'):.1f},{command.get('y0'):.1f},"
                f"{command.get('x1'):.1f},{command.get('y1'):.1f}"
            )
        elif op == "C":
            parts.append(
                "C"
                f"{command.get('x1'):.1f},{command.get('y1'):.1f},"
                f"{command.get('x2'):.1f},{command.get('y2'):.1f},"
                f"{command.get('x3'):.1f},{command.get('y3'):.1f}"
            )
    return " ".join(parts) if parts else None


def decode_pdf_to_decoded_document(doc_id: str, pdf_bytes: bytes) -> DecodedDocument:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[DecodedPage] = []
    warnings: list[str] = []

    try:
        page_count = len(doc)
        for page_index in range(page_count):
            page = doc[page_index]
            width_pt = float(page.rect.width)
            height_pt = float(page.rect.height)
            stats = DecodedStats(text_runs=0, paths=0, images=0, unknown=0)
            elements: list[Any] = []

            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "")
                        if not text or text.isspace():
                            continue
                        bbox_norm = _normalize_bbox(span.get("bbox", [0, 0, 0, 0]), width_pt, height_pt)
                        font_name = span.get("font")
                        pdf_font_name = font_name if font_name else None
                        font_size_pt = float(span.get("size")) if span.get("size") is not None else None
                        color = _color_int_to_hex(span.get("color"))
                        payload_core = {
                            "text": text,
                            "font_name": font_name,
                            "font_size_pt": font_size_pt,
                            "color": color,
                        }
                        element_id = stable_element_id(
                            doc_id,
                            page_index,
                            "text_run",
                            bbox_norm,
                            payload_core,
                        )
                        content_hash = stable_content_hash("text_run", bbox_norm, payload_core)
                        elements.append(
                            TextRunElement(
                                id=element_id,
                                kind="text_run",
                                bbox_norm=bbox_norm,
                                source="pdf",
                                content_hash=content_hash,
                                text=text,
                                font_name=font_name,
                                pdf_font_name=pdf_font_name,
                                font_size_pt=font_size_pt,
                                color=color,
                                rotation_deg=None,
                                render_mode=None,
                            )
                        )
                        stats.text_runs += 1

            try:
                drawings = page.get_drawings()
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.warning("Failed to read drawings for doc_id=%s page=%s error=%s", doc_id, page_index, exc)
                drawings = []

            for drawing in drawings:
                rect = drawing.get("rect")
                if rect is None:
                    continue
                bbox_norm = _normalize_bbox((rect.x0, rect.y0, rect.x1, rect.y1), width_pt, height_pt)
                commands = _commands_from_drawing(drawing.get("items", []), height_pt)
                path_hint = _path_hint_from_commands(commands)
                stroke_color = _color_tuple_to_hex(drawing.get("color"))
                fill_color = _color_tuple_to_hex(drawing.get("fill"))
                stroke_width_pt = drawing.get("width")
                payload_core = {
                    "commands": commands,
                    "stroke_color": stroke_color,
                    "fill_color": fill_color,
                    "stroke_width_pt": stroke_width_pt,
                }
                element_id = stable_element_id(
                    doc_id,
                    page_index,
                    "path",
                    bbox_norm,
                    payload_core,
                )
                content_hash = stable_content_hash("path", bbox_norm, payload_core)
                elements.append(
                    PathElement(
                        id=element_id,
                        kind="path",
                        bbox_norm=bbox_norm,
                        source="pdf",
                        content_hash=content_hash,
                        stroke_color=stroke_color,
                        stroke_width_pt=float(stroke_width_pt) if stroke_width_pt is not None else None,
                        fill_color=fill_color,
                        path_hint=path_hint,
                        commands=commands,
                        is_closed=drawing.get("closePath"),
                    )
                )
                stats.paths += 1

            try:
                images = page.get_images(full=True)
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.warning("Failed to read images for doc_id=%s page=%s error=%s", doc_id, page_index, exc)
                images = []

            for image in images:
                xref = image[0]
                name = image[7] if len(image) > 7 else None
                rects = page.get_image_rects(xref)
                for rect in rects:
                    bbox_norm = _normalize_bbox((rect.x0, rect.y0, rect.x1, rect.y1), width_pt, height_pt)
                    payload_core = {
                        "name": name,
                        "width_pt": rect.width,
                        "height_pt": rect.height,
                    }
                    element_id = stable_element_id(
                        doc_id,
                        page_index,
                        "image",
                        bbox_norm,
                        payload_core,
                    )
                    content_hash = stable_content_hash("image", bbox_norm, payload_core)
                    elements.append(
                        ImageElement(
                            id=element_id,
                            kind="image",
                            bbox_norm=bbox_norm,
                            source="pdf",
                            content_hash=content_hash,
                            name=name,
                            width_pt=float(rect.width),
                            height_pt=float(rect.height),
                        )
                    )
                    stats.images += 1

            needs_ocr_fallback = False
            if stats.text_runs == 0 or (stats.text_runs < 10 and (stats.images > 0 or stats.paths > 0)):
                needs_ocr_fallback = True
                warnings.append(f"page_{page_index}_needs_ocr_fallback")

            pages.append(
                DecodedPage(
                    page_index=page_index,
                    width_pt=width_pt,
                    height_pt=height_pt,
                    elements=elements,
                    stats=stats,
                    needs_ocr_fallback=needs_ocr_fallback,
                )
            )
    finally:
        doc.close()

    return DecodedDocument(
        doc_id=doc_id,
        type="pdf",
        version="v1",
        page_count=len(pages),
        pages=pages,
        warnings=warnings,
    )
