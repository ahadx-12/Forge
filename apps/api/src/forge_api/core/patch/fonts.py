from __future__ import annotations

import logging

import fitz

from forge_api.core.fonts.resolve import resolve_builtin_font


logger = logging.getLogger("forge_api")

DEFAULT_FONT = "helv"


def normalize_font_name(font_name: str | None) -> str | None:
    if font_name is None:
        return None
    return resolve_builtin_font(font_name)[0]


def safe_get_text_length(
    text: str,
    font_name: str | None,
    font_size: float,
    *,
    doc_id: str | None = None,
    page_index: int | None = None,
    primitive_id: str | None = None,
) -> float:
    resolved_font, _, _ = resolve_builtin_font(font_name)
    try:
        return fitz.get_text_length(text, fontname=resolved_font, fontsize=font_size)
    except (RuntimeError, ValueError) as exc:
        logger.warning(
            "Unsupported font fallback doc_id=%s page_index=%s primitive_id=%s font=%s error=%s",
            doc_id,
            page_index,
            primitive_id,
            font_name,
            exc.__class__.__name__,
        )
        return fitz.get_text_length(text, fontname=DEFAULT_FONT, fontsize=font_size)
