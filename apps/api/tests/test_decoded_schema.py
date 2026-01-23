from __future__ import annotations

from forge_api.schemas.decoded import DecodedDocument, DecodedPage, DecodedStats, TextRunElement


def test_decoded_schema_clamps_bbox() -> None:
    element = TextRunElement(
        id="tr_test",
        kind="text_run",
        bbox_norm=(-0.5, 1.2, 0.2, 0.1),
        source="pdf",
        content_hash="hash",
        text="Sample",
        pdf_font_name="Helvetica",
        font_size_pt=11.5,
        rotation_deg=None,
        render_mode=None,
    )

    page = DecodedPage(
        page_index=0,
        width_pt=612.0,
        height_pt=792.0,
        elements=[element],
        stats=DecodedStats(text_runs=1, paths=0, images=0, unknown=0),
    )

    doc = DecodedDocument(
        doc_id="doc-123",
        type="pdf",
        version="v1",
        page_count=1,
        pages=[page],
    )

    bbox = doc.pages[0].elements[0].bbox_norm
    assert bbox == (0.0, 0.1, 0.2, 1.0)
    assert doc.warnings == []
