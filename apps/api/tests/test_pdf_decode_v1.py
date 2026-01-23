from __future__ import annotations

import fitz

from forge_api.services.pdf_decode_v1 import decode_pdf_to_decoded_document
from tests.pdf_factory import make_contract_pdf_bytes, make_drawing_pdf_bytes


def test_decode_text_pdf_has_text_runs() -> None:
    pdf_bytes = make_contract_pdf_bytes()
    decoded = decode_pdf_to_decoded_document("doc-text", pdf_bytes)

    assert decoded.version == "v1"
    assert decoded.page_count == 1

    page = decoded.pages[0]
    assert page.stats.text_runs > 0
    assert page.needs_ocr_fallback is False

    for element in page.elements:
        for value in element.bbox_norm:
            assert 0.0 <= value <= 1.0
        assert element.content_hash


def test_decode_shape_pdf_paths_or_safe() -> None:
    pdf_bytes = make_drawing_pdf_bytes()
    decoded = decode_pdf_to_decoded_document("doc-shape", pdf_bytes)

    page = decoded.pages[0]
    path_elements = [element for element in page.elements if element.kind == "path"]
    if path_elements:
        assert page.stats.paths > 0
    else:
        assert page.stats.paths == 0


def test_decode_blank_pdf_triggers_ocr_fallback() -> None:
    doc = fitz.open()
    doc.new_page(width=300, height=400)
    pdf_bytes = doc.tobytes()
    doc.close()

    decoded = decode_pdf_to_decoded_document("doc-blank", pdf_bytes)

    page = decoded.pages[0]
    assert page.stats.text_runs == 0
    assert page.needs_ocr_fallback is True
    assert "page_0_needs_ocr_fallback" in decoded.warnings


def test_decode_ids_are_stable() -> None:
    pdf_bytes = make_contract_pdf_bytes()
    first = decode_pdf_to_decoded_document("doc-stable", pdf_bytes)
    second = decode_pdf_to_decoded_document("doc-stable", pdf_bytes)

    first_ids = [element.id for element in first.pages[0].elements][:5]
    second_ids = [element.id for element in second.pages[0].elements][:5]
    assert first_ids == second_ids
    first_hashes = [element.content_hash for element in first.pages[0].elements][:5]
    second_hashes = [element.content_hash for element in second.pages[0].elements][:5]
    assert first_hashes == second_hashes
