"""Request correlation identifiers shared by HTTP responses and error handling."""

from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError


def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    request.state.request_id = request_id
    return request_id


def reject_query(request: Request) -> None:
    if request.query_params:
        raise RequestValidationError(
            [
                {
                    "loc": ("query", key),
                    "msg": "Extra inputs are not permitted",
                    "type": "extra_forbidden",
                }
                for key in request.query_params
            ]
        )
