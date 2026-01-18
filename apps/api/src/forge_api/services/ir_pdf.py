from __future__ import annotations

import json
from pathlib import Path

import fitz

from forge_api.core.ir.normalize import normalize_page
from forge_api.schemas.ir import IRPage, IRPrimitive
from forge_api.services.storage import get_storage


def _cache_key(doc_id: str, page_index: int) -> str:
    return f"documents/{doc_id}/ir/page_{page_index}.json"


def _serialize_ir_page(ir_page: IRPage) -> bytes:
    payload = ir_page.model_dump()
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _deserialize_ir_page(data: str) -> IRPage:
    payload = json.loads(data)
    return IRPage.model_validate(payload)


def _page_to_schema(page_ir) -> IRPage:
    primitives: list[IRPrimitive] = []
    for primitive in page_ir.primitives:
        style = (
            {
                "font": primitive.style.font,
                "size": primitive.style.size,
                "color": primitive.style.color,
            }
            if primitive.kind == "text"
            else {
                "stroke_color": primitive.style.stroke_color,
                "fill_color": primitive.style.fill_color,
                "stroke_width": primitive.style.stroke_width,
            }
        )
        primitives.append(
            IRPrimitive(
                id=primitive.id,
                kind=primitive.kind,
                bbox=list(primitive.bbox),
                z_index=primitive.z_index,
                style=style,
                signature_fields=primitive.signature_fields,
                text=getattr(primitive, "text", None),
            )
        )

    return IRPage(
        doc_id=page_ir.doc_id,
        page_index=page_ir.page_index,
        width_pt=page_ir.width_pt,
        height_pt=page_ir.height_pt,
        rotation=page_ir.rotation,
        primitives=primitives,
    )


def get_page_ir(doc_id: str, page_index: int) -> IRPage:
    storage = get_storage()
    cache_key = _cache_key(doc_id, page_index)
    if storage.exists(cache_key):
        return _deserialize_ir_page(Path(storage.get_path(cache_key)).read_text())

    pdf_path = storage.get_path(f"documents/{doc_id}/original.pdf")
    if not Path(pdf_path).exists():
        raise FileNotFoundError("Document PDF missing")

    doc = fitz.open(pdf_path)
    try:
        if page_index < 0 or page_index >= len(doc):
            raise IndexError("Page index out of range")
        page = doc[page_index]
        page_ir = normalize_page(doc_id, page_index, page)
        schema_page = _page_to_schema(page_ir)
        storage.put_bytes(cache_key, _serialize_ir_page(schema_page))
        return schema_page
    finally:
        doc.close()
