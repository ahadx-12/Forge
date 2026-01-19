from __future__ import annotations

import logging

import fitz


logger = logging.getLogger("forge_api")

DEFAULT_FONT = "helv"
BASE_FONT_MAP = {
    "calibri": "helv",
    "arial": "helv",
    "arialmt": "helv",
    "helvetica": "helv",
    "times": "times",
    "timesnewroman": "times",
    "timesnewromanpsmt": "times",
    "courier": "cour",
}


def normalize_font_name(font_name: str | None) -> str | None:
    if not font_name:
        return None
    cleaned = font_name.strip().lower()
    if not cleaned:
        return None
    normalized = cleaned.replace(",", "-").replace(" ", "-")
    tokens = [token for token in normalized.split("-") if token]
    base = tokens[0] if tokens else normalized

    is_bold = any("bold" in token for token in tokens)
    is_italic = any(token in {"italic", "oblique"} or "italic" in token for token in tokens)

    base = BASE_FONT_MAP.get(base, base)
    if base not in {"helv", "times", "cour"}:
        base = DEFAULT_FONT

    if is_bold and is_italic:
        return f"{base}BI"
    if is_bold:
        return f"{base}B"
    if is_italic:
        return f"{base}I"
    return base


def safe_get_text_length(
    text: str,
    font_name: str | None,
    font_size: float,
    *,
    doc_id: str | None = None,
    page_index: int | None = None,
    primitive_id: str | None = None,
) -> float:
    resolved_font = normalize_font_name(font_name) or DEFAULT_FONT
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
