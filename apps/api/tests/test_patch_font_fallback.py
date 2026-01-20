from __future__ import annotations

from forge_api.core.fonts.resolve import resolve_builtin_font
from forge_api.core.patch.fonts import safe_get_text_length


def test_measure_text_width_falls_back() -> None:
    builtin, fidelity, reason = resolve_builtin_font("calibri-bold")
    assert builtin.startswith("helv")
    assert fidelity > 0
    assert reason in {"family_map", "unknown_fallback", "missing_font", "builtin"}
    width = safe_get_text_length("Hello", "calibri-bold", 12, doc_id="doc-1", page_index=0, primitive_id="prim-1")
    assert width > 0
