from __future__ import annotations

import stat
import sys
import types

from forge_api.services import chromium_runtime
from forge_api.settings import Settings


def test_resolve_chromium_executable_env(monkeypatch, tmp_path):
    chromium = tmp_path / "chromium"
    chromium.write_text("#!/bin/sh\necho chromium\n")
    chromium.chmod(stat.S_IRWXU)
    monkeypatch.setenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE", str(chromium))

    assert chromium_runtime.resolve_chromium_executable() == str(chromium)


def test_startup_check_does_not_raise_in_production(monkeypatch):
    monkeypatch.delenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE", raising=False)
    monkeypatch.setattr(chromium_runtime, "resolve_chromium_executable", lambda: None)

    settings = Settings(FORGE_ENV="production")

    assert chromium_runtime.log_chromium_startup_status(settings, chromium_runtime.logging.getLogger("test")) is None


def test_startup_check_does_not_touch_playwright_sync(monkeypatch, tmp_path):
    chromium = tmp_path / "chromium"
    chromium.write_text("#!/bin/sh\necho chromium\n")
    chromium.chmod(stat.S_IRWXU)
    monkeypatch.setenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE", str(chromium))

    fake_playwright = types.ModuleType("playwright.sync_api")

    def _raise(*_args, **_kwargs):
        raise AssertionError("playwright sync API should not be called")

    fake_playwright.sync_playwright = _raise  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_playwright)
    monkeypatch.setattr(chromium_runtime.subprocess, "run", lambda *_args, **_kwargs: types.SimpleNamespace(returncode=0, stdout="ok", stderr=""))

    settings = Settings(FORGE_ENV="production")
    assert chromium_runtime.log_chromium_startup_status(settings, chromium_runtime.logging.getLogger("test")) == str(chromium)


def test_resolve_chromium_executable_missing(monkeypatch):
    monkeypatch.delenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_CHROMIUM_PATH", raising=False)
    monkeypatch.delenv("CHROMIUM_PATH", raising=False)
    monkeypatch.setattr(chromium_runtime.shutil, "which", lambda _: None)
    monkeypatch.setattr(chromium_runtime.os.path, "exists", lambda _: False)
    monkeypatch.setattr(chromium_runtime.os, "access", lambda *_: False)

    assert chromium_runtime.resolve_chromium_executable() is None
