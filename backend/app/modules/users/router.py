from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status

from app.core.exceptions import NotFoundException
from app.core.security import require_roles
from app.modules.users.schemas import UserCreate, UserResponse, UserUpdate
from app.shared.enums import UserRole
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response, get_pagination_params

router = APIRouter(prefix="/users", tags=["Users"])

# Sample in-memory data for initial template execution
SAMPLE_USERS = [
    UserResponse(
        id=1,
        email="admin@xbike.local",
        full_name="System Admin",
        roles=[UserRole.ADMIN, UserRole.MANAGER],
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ),
    UserResponse(
        id=2,
        email="production.lead@xbike.local",
        full_name="Jane Doe (Shopfloor Lead)",
        roles=[UserRole.PRODUCTION],
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ),
]


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    params: PageParams = Depends(get_pagination_params),
    _=Depends(require_roles(["ADMIN", "MANAGER"])),
):
    """List system users with pagination."""
    return create_paginated_response(
        items=SAMPLE_USERS,
        total_items=len(SAMPLE_USERS),
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, _=Depends(require_roles(["ADMIN", "MANAGER"]))):
    """Get user by ID."""
    for user in SAMPLE_USERS:
        if user.id == user_id:
            return user
    raise NotFoundException(message=f"User with ID {user_id} not found")


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, _=Depends(require_roles(["ADMIN"]))):
    """Create a new user with assigned roles."""
    new_user = UserResponse(
        id=len(SAMPLE_USERS) + 1,
        email=payload.email,
        full_name=payload.full_name,
        roles=payload.roles,
        is_active=payload.is_active,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    SAMPLE_USERS.append(new_user)
    return new_user
