from __future__ import annotations

import re


BUILTIN_FONTS = {
    "helv",
    "helvb",
    "helvi",
    "helvbi",
    "tiro",
    "tirob",
    "tiroi",
    "tirobi",
    "cour",
    "courb",
    "couri",
    "courbi",
}


def normalize_pdf_font_name(raw: str | None) -> str:
    if not raw:
        return ""
    cleaned = raw.strip()
    if not cleaned:
        return ""
    if "+" in cleaned:
        prefix, remainder = cleaned.split("+", 1)
        if len(prefix) == 6 and prefix.replace(" ", "").isalnum():
            cleaned = remainder
    normalized = re.sub(r"[,_\s]+", "-", cleaned.lower())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized


def _detect_family(tokens: list[str], normalized: str) -> tuple[str, str]:
    family_tokens = tokens + [normalized.replace("-", "")]
    if any(token in {"calibri", "arial", "arialmt", "helvetica", "sans", "sansserif"} for token in family_tokens):
        return "helv", "family_map"
    if any(token in {"times", "timesnewroman", "timesnewromanpsmt", "serif"} for token in family_tokens):
        return "tiro", "family_map"
    if any(token in {"courier", "mono", "monospace"} for token in family_tokens):
        return "cour", "family_map"
    if normalized in BUILTIN_FONTS:
        return normalized, "builtin"
    return "helv", "unknown_fallback"


def resolve_builtin_font(raw: str | None) -> tuple[str, float, str]:
    normalized = normalize_pdf_font_name(raw)
    if not normalized:
        return "helv", 0.7, "missing_font"
    tokens = [token for token in re.split(r"[-]+", normalized) if token]

    family, reason = _detect_family(tokens, normalized)
    is_bold = any("bold" in token for token in tokens)
    is_italic = any(token in {"italic", "oblique"} or "italic" in token for token in tokens)

    base = family
    if family in {"helv", "tiro", "cour"}:
        if is_bold and is_italic:
            base = f"{family}bi"
        elif is_bold:
            base = f"{family}b"
        elif is_italic:
            base = f"{family}i"

    if base not in BUILTIN_FONTS:
        return "helv", 0.7, "unknown_fallback"
    if reason == "builtin":
        return base, 1.0, reason
    if reason == "family_map":
        return base, 0.9, reason
    if reason == "missing_font":
        return base, 0.7, reason
    return base, 0.7, reason
