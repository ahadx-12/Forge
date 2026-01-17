from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from forge_api.settings import get_settings


@dataclass
class OpenAIClient:
    api_key: Optional[str]

    @classmethod
    def from_settings(cls) -> "OpenAIClient":
        settings = get_settings()
        return cls(api_key=settings.openai_api_key)

    def is_configured(self) -> bool:
        return bool(self.api_key)
