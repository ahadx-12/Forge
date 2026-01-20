from __future__ import annotations

import fitz

from forge_api.services.document_decoder import DocumentDecoder


def _make_test_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 72), "Test Heading", fontsize=20)
    page.insert_text((72, 120), "This is a paragraph with multiple words.", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_pdf_decoded_to_blocks_not_characters():
    pdf_bytes = _make_test_pdf()

    decoder = DocumentDecoder()
    decoded = decoder.decode_pdf(pdf_bytes)

    page = decoded["pages"][0]
    elements = page["elements"]

    assert len(elements) < 10, f"Too many elements: {len(elements)}"

    heading = elements[0]
    assert heading["element_type"] == "heading"
    assert "Test Heading" in heading["text"]

    paragraph = elements[1]
    assert "paragraph with multiple words" in paragraph["text"]
