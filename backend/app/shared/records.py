"""Plain results crossing the persistence/application boundary."""

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RecordPage(Generic[T]):
    items: list[T]
    total: int


@dataclass(frozen=True)
class CreatedRecord(Generic[T]):
    record: T
    snapshot: dict[str, Any]
