from __future__ import annotations

from forge_api.services.export_html_pdf import resolve_chromium_executable


def test_resolve_chromium_executable_uses_env_override(monkeypatch) -> None:
    monkeypatch.setenv("CHROMIUM_PATH", "/fake/chromium")
    assert resolve_chromium_executable() == "/fake/chromium"
