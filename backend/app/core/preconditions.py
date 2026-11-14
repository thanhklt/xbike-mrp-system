"""Strong resource validators; callers compare under their transaction locks."""

import hashlib
import json
from typing import Any

from app.core.errors import PreconditionFailedException, PreconditionRequiredException


def make_etag(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return '"' + hashlib.sha256(canonical.encode("utf-8")).hexdigest() + '"'


def verify_if_match(value: str | None, expected: str) -> None:
    if value is None or not value.strip():
        raise PreconditionRequiredException()
    if value.strip() != expected:
        raise PreconditionFailedException()
