from math import ceil
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    search: Optional[str] = Field(default=None, description="Search term across textual columns")
    sort_by: Optional[str] = Field(default="created_at", description="Field to sort by")
    sort_order: Optional[str] = Field(
        default="desc", pattern="^(asc|desc)$", description="Sort order"
    )


class PaginationMetadata(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: List[T]
    pagination: PaginationMetadata
    message: str = "Items retrieved successfully"


def create_paginated_response(
    items: List[T],
    total_items: int,
    page: int,
    page_size: int,
    message: str = "Items retrieved successfully",
) -> PaginatedResponse[T]:
    total_pages = ceil(total_items / page_size) if page_size > 0 else 1
    return PaginatedResponse(
        success=True,
        data=items,
        pagination=PaginationMetadata(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
        message=message,
    )
