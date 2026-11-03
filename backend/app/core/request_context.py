"""Request correlation identifiers shared by HTTP responses and error handling."""

from typing import Annotated
from uuid import uuid4

from fastapi import Header, Request
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


def reject_repeated_query(request: Request) -> None:
    repeated = [key for key in request.query_params if len(request.query_params.getlist(key)) > 1]
    if repeated:
        raise RequestValidationError(
            [
                {
                    "loc": ("query", key),
                    "msg": "Query parameter must appear once",
                    "type": "value_error",
                }
                for key in repeated
            ]
        )


def get_if_match(
    request: Request,
    if_match: Annotated[
        str | None,
        Header(description="Strong ETag from GET detail; required at runtime (428 if missing)"),
    ] = None,
) -> str | None:
    if len(request.headers.getlist("if-match")) > 1:
        raise RequestValidationError(
            [
                {
                    "loc": ("header", "If-Match"),
                    "msg": "If-Match must appear once",
                    "type": "value_error",
                }
            ]
        )
    return if_match
