from __future__ import annotations

from typing import Any

from openai import OpenAI

from forge_api.settings import get_settings


class OpenAIClient:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not configured")
        self.model = settings.OPENAI_MODEL or "gpt-5.2"
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def response_json(self, system: str, user: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        for output in response.output:
            if output.type == "message":
                for part in output.content:
                    if part.type == "output_text":
                        return part.text
        raise RuntimeError("No output text from OpenAI response")
