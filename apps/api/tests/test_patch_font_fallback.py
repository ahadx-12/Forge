from __future__ import annotations

from forge_api.core.patch.apply import _measure_text_width


def test_measure_text_width_falls_back() -> None:
    width = _measure_text_width("Hello", "calibri-bold", 12, "doc-1", 0, "prim-1")
    assert width > 0
