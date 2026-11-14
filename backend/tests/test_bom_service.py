"""UC-15–19: schema and precondition behavior, independent of HTTP/database."""

from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.core.errors import (
    ForbiddenException,
    PreconditionFailedException,
    PreconditionRequiredException,
)
from app.modules.bom.schemas import BomCreate


@pytest.mark.parametrize(
    "method,args",
    [
        ("create_version", (1, None, {"sub": "2", "roles": ["nhan_vien"]}, None, "test")),
        ("activate_bom", (1, {"sub": "2", "roles": ["nhan_vien"]}, None, "test")),
        ("delete_bom", (1, {"sub": "2", "roles": ["nhan_vien"]}, None)),
        ("get_bom", (1, {"sub": "3", "roles": ["quan_tri_vien"]}, "test")),
    ],
)
async def test_bom_ac01_public_service_denies_before_io(method, args):
    from app.modules.bom.service import BomService

    repository, mutation = AsyncMock(), AsyncMock()
    service = BomService(repository, AsyncMock(), mutation, AsyncMock())
    with pytest.raises(ForbiddenException):
        await getattr(service, method)(*args)
    assert not repository.mock_calls and not mutation.mock_calls


@pytest.mark.parametrize("amount", [True, False, 0, -1, 1.5, "2"])
def test_uc16_ac7_strict_positive_quantity(amount):
    with pytest.raises(ValidationError):
        BomCreate.model_validate(
            {"mat_hang_id": 1, "chi_tiet": [{"mat_hang_id": 2, "so_luong": amount}]}
        )


@pytest.mark.parametrize("value", [None, "", " "])
def test_bom_ac07_missing_precondition(value):
    from app.core.preconditions import verify_if_match

    with pytest.raises(PreconditionRequiredException):
        verify_if_match(value, '"abc"')


@pytest.mark.parametrize("value", ['W/"abc"', "*", "abc", '"old"', '"abc", "other"'])
def test_bom_ac07_reject_non_matching_strong_tag(value):
    from app.core.preconditions import verify_if_match

    with pytest.raises(PreconditionFailedException):
        verify_if_match(value, '"abc"')


@pytest.mark.parametrize("roles", [[], ["nhan_vien"], ["quan_tri_vien"], "quan_ly"])
async def test_bom_ac01_write_guard_precedes_repository(roles):
    from app.modules.bom.service import require_manager

    repo = AsyncMock()
    with pytest.raises(ForbiddenException):
        require_manager({"sub": "1", "roles": roles})
        await repo.add()
    repo.add.assert_not_called()
