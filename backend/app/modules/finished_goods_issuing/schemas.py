"""Both issue flows use the same document shape."""

from app.modules.material_issuing.schemas import (
    MaterialIssueItemCreate as DispatchItemCreate,
)
from app.modules.material_issuing.schemas import (
    MaterialIssueItemResponse as DispatchItemResponse,
)
from app.modules.material_issuing.schemas import (
    MaterialIssueRequestCreate as FinishedGoodsDispatchCreate,
)
from app.modules.material_issuing.schemas import (
    MaterialIssueRequestResponse as FinishedGoodsDispatchResponse,
)

__all__ = [
    "DispatchItemCreate",
    "DispatchItemResponse",
    "FinishedGoodsDispatchCreate",
    "FinishedGoodsDispatchResponse",
]
