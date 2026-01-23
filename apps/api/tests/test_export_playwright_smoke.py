from __future__ import annotations

import stat

from forge_api.services.chromium_runtime import resolve_chromium_executable


def test_resolve_chromium_executable_uses_env_override(monkeypatch, tmp_path) -> None:
    chromium_path = tmp_path / "chromium"
    chromium_path.write_text("#!/bin/sh\necho chromium\n")
    chromium_path.chmod(stat.S_IRWXU)
    monkeypatch.setenv("CHROMIUM_PATH", str(chromium_path))
    assert resolve_chromium_executable() == str(chromium_path)
