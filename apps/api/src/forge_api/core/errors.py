from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class APIError(Exception):
    status_code: int
    code: str
    message: str
    details: dict[str, Any] | None = None


class AIError(APIError):
    pass


class UpstreamAIError(AIError):
    pass


class StorageError(APIError):
    pass
