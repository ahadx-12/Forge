from __future__ import annotations

from uuid import uuid4

from fastapi import Request


def get_request_id(request: Request | None) -> str:
    if request is not None:
        for header in ("x-request-id", "x-correlation-id"):
            value = request.headers.get(header)
            if value:
                return value
    return str(uuid4())
