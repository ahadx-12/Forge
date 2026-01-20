from __future__ import annotations

from forge_api.services.forge_manifest import _bbox_pt_to_px


def test_bbox_pt_to_px_y_flip():
    bbox_pt = [10, 20, 30, 40]
    result = _bbox_pt_to_px(
        bbox_pt,
        scale_x=2,
        scale_y=2,
        page_width_pt=200,
        page_height_pt=100,
        rotation=0,
    )
    assert result == [20.0, 120.0, 60.0, 160.0]


def test_bbox_pt_to_px_rotation_90():
    bbox_pt = [10, 20, 30, 40]
    result = _bbox_pt_to_px(
        bbox_pt,
        scale_x=2,
        scale_y=2,
        page_width_pt=200,
        page_height_pt=100,
        rotation=90,
    )
    assert result == [40.0, 20.0, 80.0, 60.0]
