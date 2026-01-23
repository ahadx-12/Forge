from __future__ import annotations

from dataclasses import dataclass
from html import escape
import os
import shutil
from typing import Any

from forge_api.services.forge_manifest import build_forge_manifest
from forge_api.services.forge_overlay import build_overlay_state, load_overlay_custom_entries, load_overlay_patch_log


@dataclass(frozen=True)
class HtmlExportResult:
    payload: bytes


def _font_family(pdf_font: str | None) -> str:
    if not pdf_font:
        return "Helvetica, Arial, sans-serif"
    lower = pdf_font.lower()
    if "times" in lower or "serif" in lower:
        return '"Times New Roman", Times, serif'
    if "courier" in lower or "mono" in lower:
        return '"Courier New", Courier, monospace'
    return "Helvetica, Arial, sans-serif"


def _page_dimensions_px(page: dict[str, Any]) -> tuple[float, float]:
    width_pt = float(page.get("width_pt") or 0)
    height_pt = float(page.get("height_pt") or 0)
    return width_pt * (96 / 72), height_pt * (96 / 72)


def _render_page(page: dict[str, Any], overlay_state: dict[str, Any]) -> str:
    page_width_px, page_height_px = _page_dimensions_px(page)
    page_width_pt = float(page.get("width_pt") or 1)
    elements_html: list[str] = []
    primitives = overlay_state.get("primitives", {})

    for element in page.get("elements", []):
        bbox = element.get("bbox") or [0.0, 0.0, 0.0, 0.0]
        x0, y0, x1, y1 = bbox
        left = x0 * 100
        top = y0 * 100
        width = max(0.0, (x1 - x0) * 100)
        height = max(0.0, (y1 - y0) * 100)

        overlay_entry = primitives.get(element.get("element_id"), {})
        style = overlay_entry.get("style") or element.get("style") or {}
        font_size_pt = float(style.get("font_size_pt") or 12)
        font_size_px = font_size_pt / page_width_pt * page_width_px
        line_height = style.get("line_height")
        if line_height:
            line_height_px = float(line_height) / page_width_pt * page_width_px
        else:
            line_count = max(1, len(element.get("lines") or []) or 1)
            line_height_px = (height / 100) * page_height_px / line_count

        wrap_policy = style.get("wrap_policy") or (
            "auto" if element.get("element_type") == "text" else "nowrap"
        )
        white_space = "pre-wrap" if wrap_policy != "nowrap" else "nowrap"
        overflow = "hidden"
        text_overflow = "ellipsis" if wrap_policy == "nowrap" else "clip"

        text = overlay_entry.get("text") or element.get("text") or ""
        elements_html.append(
            (
                "<div style=\"position:absolute;"
                f"left:{left:.4f}%;top:{top:.4f}%;"
                f"width:{width:.4f}%;height:{height:.4f}%;"
                f"font-size:{font_size_px:.2f}px;"
                f"line-height:{line_height_px:.2f}px;"
                f"font-family:{_font_family(style.get('font_family'))};"
                f"font-weight:{'bold' if style.get('is_bold') else 'normal'};"
                f"font-style:{'italic' if style.get('is_italic') else 'normal'};"
                f"color:{style.get('color') or '#000'};"
                f"white-space:{white_space};overflow:{overflow};text-overflow:{text_overflow};"
                "padding:0;\">"
                f"{escape(text)}"
                "</div>"
            )
        )

    return (
        "<div class=\"page\" style=\""
        f"width:{page_width_px:.2f}px;height:{page_height_px:.2f}px;\">"
        + "".join(elements_html)
        + "</div>"
    )


def export_pdf_from_html(doc_id: str) -> HtmlExportResult:
    manifest = build_forge_manifest(doc_id)
    pages = manifest.get("pages") or []
    if not pages:
        raise FileNotFoundError("Document not found")

    overlay_state = build_overlay_state(
        manifest,
        load_overlay_patch_log(doc_id),
        custom_entries=load_overlay_custom_entries(doc_id),
    )
    first_page = pages[0]
    width_in = float(first_page.get("width_pt") or 0) / 72
    height_in = float(first_page.get("height_pt") or 0) / 72

    pages_html = [
        _render_page(page, overlay_state.get(page.get("page_index"), {})) for page in pages
    ]

    html = (
        "<!doctype html><html><head><meta charset=\"utf-8\"/>"
        "<style>"
        "html,body{margin:0;padding:0;background:#fff;}"
        "@page{"
        f"size:{width_in:.4f}in {height_in:.4f}in;margin:0;}}"
        ".page{position:relative;page-break-after:always;}"
        ".page:last-child{page-break-after:auto;}"
        "</style></head><body>"
        + "".join(pages_html)
        + "</body></html>"
    )

    from playwright.sync_api import sync_playwright

    chromium_path = resolve_chromium_executable()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chromium_path)
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        pdf_bytes = page.pdf(prefer_css_page_size=True, print_background=True)
        browser.close()

    return HtmlExportResult(payload=pdf_bytes)


def resolve_chromium_executable() -> str:
    env_candidates = [
        os.getenv("PLAYWRIGHT_CHROMIUM_PATH"),
        os.getenv("CHROMIUM_PATH"),
    ]
    for candidate in env_candidates:
        if candidate:
            return candidate

    which_candidate = shutil.which("chromium")
    candidates = [
        which_candidate,
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/chrome",
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate

    raise RuntimeError(
        "Chromium executable not found. Set PLAYWRIGHT_CHROMIUM_PATH or CHROMIUM_PATH to a valid path."
    )
