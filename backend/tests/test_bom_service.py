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


async def test_bom_ac04_mutation_scope_commits_before_cache_publish(monkeypatch):
    """T04: the shared scope must support async with and publish only after commit."""
    from app.modules.mat_hang.cache import MatHangCache
    from app.modules.mat_hang.mutation import MatHangMutation
    from app.modules.mat_hang.schemas import MatHangRead

    events = []

    class Transaction:
        async def __aenter__(self):
            events.append("begin")
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            events.append("commit" if exc is None else "rollback")

    cache = MatHangCache()
    cache.replace([])
    item = MatHangRead(
        id=1,
        ma_mat_hang="MH-000001",
        ten_mat_hang="Frame",
        sku="frame",
        loai_mat_hang="linh_kien",
        don_vi_tinh="chiec",
        mau_sac=None,
        mo_ta=None,
        don_gia=100,
        is_active=True,
        so_luong_ton=0,
        so_luong_dang_giu=0,
        so_luong_con_dung=0,
        ton_kho_updated_at=None,
    )
    original = cache.publish

    def publish(snapshot):
        events.append("publish")
        original(snapshot)

    monkeypatch.setattr(cache, "publish", publish)
    mutation = MatHangMutation(Transaction(), cache)
    async with mutation.scope() as changes:
        mutation.require_active()
        changes.append(item)
        events.append("body")

    assert events == ["begin", "body", "commit", "publish"]
    assert cache.snapshot().by_id[item.id] == item
    with pytest.raises(RuntimeError, match="Caller must own"):
        mutation.require_active()


async def test_bom_ac04_nested_scope_rejected_across_instances():
    """A second MatHangMutation must not open its own transaction inside another scope."""
    from app.modules.mat_hang.cache import MatHangCache
    from app.modules.mat_hang.mutation import MatHangMutation

    class Transaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

    cache = MatHangCache()
    cache.replace([])
    outer, other = MatHangMutation(Transaction(), cache), MatHangMutation(Transaction(), cache)
    async with outer.scope():
        outer.require_active()
        with pytest.raises(RuntimeError, match="Caller must own"):
            other.require_active()
        with pytest.raises(RuntimeError, match="Nested catalog mutation"):
            async with other.scope():
                pass
    async with other.scope():
        other.require_active()
