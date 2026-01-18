from __future__ import annotations

import fitz


def _new_doc() -> fitz.Document:
    return fitz.open()


def make_drawing_pdf_bytes() -> bytes:
    doc = _new_doc()
    page1 = doc.new_page(width=595, height=842)
    page1.draw_line((72, 72), (300, 72), color=(0, 0, 0), width=1)
    page1.draw_rect(fitz.Rect(100, 120, 260, 200), color=(0, 0.4, 1), width=2)
    page1.insert_text((72, 300), "Forge Drawing Sheet", fontsize=16)
    page1.insert_text((72, 330), "Vector + Text", fontsize=12)
    page1.draw_line((72, 360), (300, 360), color=(0.2, 0.2, 0.2), width=1)
    page1.draw_rect(fitz.Rect(320, 120, 460, 200), color=(0.1, 0.7, 0.3), width=1.5)
    page1.insert_text((72, 380), "Deterministic Sample", fontsize=10)

    page2 = doc.new_page(width=595, height=842)
    page2.draw_line((72, 72), (500, 72), color=(1, 0.2, 0.2), width=1.5)
    page2.draw_rect(fitz.Rect(80, 140, 280, 240), color=(0.2, 1, 0.2), width=1)
    page2.insert_text((72, 260), "Page Two", fontsize=14)
    page2.insert_text((72, 290), "More vectors and labels", fontsize=11)
    page2.draw_rect(fitz.Rect(320, 140, 460, 240), color=(0.7, 0.1, 0.1), width=1)
    page2.insert_text((72, 320), "Fixed coords", fontsize=10)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def make_contract_pdf_bytes() -> bytes:
    doc = _new_doc()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "Forge Contract", fontsize=18)
    page.insert_text((72, 140), "This agreement outlines the Week 1 scope.", fontsize=12)
    page.insert_text((72, 170), "- Uploads are stored ephemerally.", fontsize=11)
    page.insert_text((72, 200), "- Decode output is deterministic.", fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def make_overlap_pdf_bytes() -> bytes:
    doc = _new_doc()
    page = doc.new_page(width=400, height=400)
    rect_a = fitz.Rect(100, 100, 200, 200)
    rect_b = fitz.Rect(150, 150, 250, 250)
    page.draw_rect(rect_a, color=(0.1, 0.2, 0.8), width=2)
    page.draw_rect(rect_b, color=(0.8, 0.2, 0.1), width=2)
    page.insert_text((110, 110), "Overlap", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def make_colored_bg_pdf_bytes() -> bytes:
    doc = _new_doc()
    page = doc.new_page(width=400, height=400)
    background = fitz.Rect(50, 50, 350, 200)
    page.draw_rect(background, color=(0.2, 0.4, 0.6), fill=(0.2, 0.4, 0.6))
    page.insert_text((70, 120), "Background Sample", fontsize=14, color=(1, 1, 1))
    page.insert_text((70, 150), "Edit me", fontsize=12, color=(1, 1, 1))
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
