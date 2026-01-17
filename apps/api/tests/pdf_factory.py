from __future__ import annotations

import fitz


def make_contract_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    paragraphs = [
        "This Agreement is entered into by and between Forge Labs and Example Corp.",
        "The parties agree to the terms and conditions outlined herein, including scope of work and fees.",
        "Payment is due within thirty (30) days of invoice receipt unless otherwise agreed.",
        "Confidential information disclosed under this Agreement shall remain protected.",
    ]
    y = 72
    for paragraph in paragraphs:
        page.insert_text((72, y), paragraph, fontsize=12)
        y += 28
    doc_bytes = doc.tobytes()
    doc.close()
    return doc_bytes


def make_drawing_pdf_bytes() -> bytes:
    doc = fitz.open()

    page_one = doc.new_page(width=595, height=842)
    page_one.insert_text((72, 72), "Drawing Sheet A", fontsize=14)
    page_one.draw_rect(fitz.Rect(100, 130, 260, 230), color=(0.2, 0.6, 0.9), width=2)
    page_one.draw_line(
        fitz.Point(100, 260),
        fitz.Point(260, 260),
        color=(0.8, 0.2, 0.2),
        width=1.5,
    )
    page_one.insert_text((110, 150), "Viewport", fontsize=10)

    page_two = doc.new_page(width=595, height=842)
    page_two.insert_text((72, 72), "Drawing Sheet B", fontsize=14)
    page_two.draw_rect(fitz.Rect(140, 200, 320, 320), color=(0.1, 0.8, 0.4), width=2)
    page_two.draw_line(
        fitz.Point(140, 340),
        fitz.Point(320, 340),
        color=(0.4, 0.4, 0.9),
        width=1.2,
    )
    page_two.insert_text((150, 220), "Anchor", fontsize=10)

    doc_bytes = doc.tobytes()
    doc.close()
    return doc_bytes
