from __future__ import annotations

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
        if not settings.OPENAI_API_KEY:
            raise AIError(
                status_code=503,
                code="ai_not_configured",
                message="AI not configured",
                details={"hint": "Set OPENAI_API_KEY on the API service."},
            )
        self.model = settings.OPENAI_MODEL or "gpt-5.2"
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.timeout_s = 20.0

    def response_json(self, system: str, user: str) -> str:
        max_retries = 2
        backoff_s = 0.5
        for attempt in range(max_retries + 1):
            try:
                response = self.client.responses.create(
                    model=self.model,
                    input=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format={"type": "json_object"},
                    timeout=self.timeout_s,
                )
                for output in response.output:
                    if output.type == "message":
                        for part in output.content:
                            if part.type == "output_text":
                                return part.text
                raise UpstreamAIError(
                    status_code=502,
                    code="ai_empty_response",
                    message="Upstream AI returned no output text",
                )
            except (BadRequestError, NotFoundError, UnprocessableEntityError) as exc:
                raise AIError(
                    status_code=400,
                    code="invalid_model",
                    message=f"Invalid OpenAI model: {self.model}. Set OPENAI_MODEL to a valid model.",
                    details={"model": self.model},
                ) from exc
            except (AuthenticationError, PermissionDeniedError) as exc:
                raise UpstreamAIError(
                    status_code=502,
                    code="ai_upstream_auth",
                    message="Upstream AI authentication failed",
                    details={"status_code": getattr(exc, "status_code", None)},
                ) from exc
            except RateLimitError as exc:
                if attempt < max_retries:
                    time.sleep(backoff_s * (2**attempt))
                    continue
                raise UpstreamAIError(
                    status_code=502,
                    code="ai_rate_limited",
                    message="Upstream AI rate limit exceeded",
                    details={"status_code": getattr(exc, "status_code", None)},
                ) from exc
            except APITimeoutError as exc:
                if attempt < max_retries:
                    time.sleep(backoff_s * (2**attempt))
                    continue
                raise UpstreamAIError(
                    status_code=502,
                    code="ai_timeout",
                    message="Upstream AI request timed out",
                    details={"status_code": getattr(exc, "status_code", None)},
                ) from exc
            except APIConnectionError as exc:
                if attempt < max_retries:
                    time.sleep(backoff_s * (2**attempt))
                    continue
                raise UpstreamAIError(
                    status_code=502,
                    code="ai_connection_error",
                    message="Upstream AI connection failed",
                    details={"status_code": getattr(exc, "status_code", None)},
                ) from exc
            except APIStatusError as exc:
                status_code = getattr(exc, "status_code", None)
                if status_code is not None and status_code >= 500 and attempt < max_retries:
                    time.sleep(backoff_s * (2**attempt))
                    continue
                raise UpstreamAIError(
                    status_code=502,
                    code="ai_upstream_error",
                    message="Upstream AI request failed",
                    details={"status_code": status_code, "error": exc.__class__.__name__},
                ) from exc
