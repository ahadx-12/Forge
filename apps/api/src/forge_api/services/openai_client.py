from __future__ import annotations

import json
import time
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)

from forge_api.core.errors import AIError, UpstreamAIError
from forge_api.settings import get_settings


class OpenAIClient:
    def __init__(self) -> None:
        settings = get_settings()
        model = settings.FORGE_OPENAI_MODEL or settings.OPENAI_MODEL
        if not settings.OPENAI_API_KEY or not model:
            raise AIError(
                status_code=400,
                code="ai_not_configured",
                message="AI not configured",
                details={
                    "hint": "Set OPENAI_API_KEY and OPENAI_MODEL (or FORGE_OPENAI_MODEL) on the API service."
                },
            )
        self.model = model
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.timeout_s = 20.0

    def response_json(self, system: str, user: str) -> dict[str, Any]:
        max_retries = 2
        backoff_s = 0.5
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format={"type": "json_object"},
                    timeout=self.timeout_s,
                )
                raw_text = response.choices[0].message.content if response.choices else ""
                if not raw_text:
                    raise UpstreamAIError(
                        status_code=502,
                        code="ai_upstream_error",
                        message="Upstream AI returned no output text",
                    )
                try:
                    return json.loads(raw_text)
                except json.JSONDecodeError as exc:
                    raise AIError(
                        status_code=502,
                        code="ai_invalid_json",
                        message="Upstream AI returned invalid JSON",
                        details={"response": raw_text},
                    ) from exc
            except (AuthenticationError, PermissionDeniedError) as exc:
                raise UpstreamAIError(
                    status_code=502,
                    code="ai_upstream_error",
                    message="Upstream AI authentication failed",
                    details={"status_code": getattr(exc, "status_code", None)},
                ) from exc
            except (BadRequestError, NotFoundError, UnprocessableEntityError) as exc:
                raise UpstreamAIError(
                    status_code=502,
                    code="ai_upstream_error",
                    message="Upstream AI rejected the request",
                    details={"status_code": getattr(exc, "status_code", None)},
                ) from exc
            except (RateLimitError, APITimeoutError, APIConnectionError, APIStatusError) as exc:
                if isinstance(exc, APIStatusError):
                    status_code = getattr(exc, "status_code", None)
                    if status_code is not None and status_code >= 500 and attempt < max_retries:
                        time.sleep(backoff_s * (2**attempt))
                        continue
                    details = {"status_code": status_code, "error": exc.__class__.__name__}
                else:
                    if attempt < max_retries:
                        time.sleep(backoff_s * (2**attempt))
                        continue
                    details = {"status_code": getattr(exc, "status_code", None)}
                raise UpstreamAIError(
                    status_code=502,
                    code="ai_upstream_error",
                    message="Upstream AI request failed",
                    details=details,
                ) from exc
