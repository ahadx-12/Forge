from __future__ import annotations

import pytest

from forge_api.core.errors import AIError
from forge_api.services import openai_client
from forge_api.services.openai_client import OpenAIClient
from forge_api.settings import get_settings


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content: str) -> None:
        self._content = content

    def create(self, **_: object) -> _FakeResponse:
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, content: str) -> None:
        self.completions = _FakeCompletions(content)


class _FakeOpenAI:
    def __init__(self, api_key: str, content: str) -> None:
        self.chat = _FakeChat(content)


def _patch_openai(monkeypatch, content: str) -> None:
    monkeypatch.setattr(
        openai_client,
        "OpenAI",
        lambda api_key: _FakeOpenAI(api_key=api_key, content=content),
    )


def test_openai_client_response_json_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    get_settings.cache_clear()
    _patch_openai(monkeypatch, '{"schema_version": 1, "ops": []}')

    client = OpenAIClient()
    payload = client.response_json("system", "user")

    assert payload["schema_version"] == 1


def test_openai_client_response_json_invalid(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    get_settings.cache_clear()
    _patch_openai(monkeypatch, "not-json")

    client = OpenAIClient()
    with pytest.raises(AIError) as excinfo:
        client.response_json("system", "user")

    assert excinfo.value.code == "ai_invalid_json"


def test_openai_client_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    get_settings.cache_clear()

    with pytest.raises(AIError) as excinfo:
        OpenAIClient()

    assert excinfo.value.code == "ai_not_configured"
