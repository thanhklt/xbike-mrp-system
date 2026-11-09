"""Count /api/v1 requests except CORS preflight, including failed ones."""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.config.settings import settings


def should_count(request: Request) -> bool:
    prefix = settings.api_v1_str.rstrip("/")
    path = request.url.path
    return request.method != "OPTIONS" and (path == prefix or path.startswith(prefix + "/"))


async def dem_luu_luong(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    if not should_count(request):
        return await call_next(request)
    try:
        return await call_next(request)
    finally:
        # Set only in the app lifespan; tests without lifespan never touch the app database.
        recorder = getattr(request.app.state, "luu_luong_recorder", None)
        if recorder is not None:
            await recorder.record()
