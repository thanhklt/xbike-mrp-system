"""UC-43 / AC service tests: specs/use_cases/audit/UC-43.md."""

from dataclasses import replace
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.core.errors import ForbiddenException, NotFoundException
from app.modules.audit.schemas import AuditListQuery, AuditRecord, CreationAudit
from app.modules.audit.service import AuditService
from app.shared.records import RecordPage


def record(**changes):
    return replace(
        AuditRecord(
            id=1,
            nhan_vien_id=2,
            loai_doi_tuong="yeu_cau_san_xuat",
            doi_tuong_id=10,
            thao_tac="kiem_tra",
            trang_thai_truoc="da_gui",
            trang_thai_sau="cho_bo_sung_linh_kien",
            du_lieu_truoc=None,
            du_lieu_sau={"danh_sach_thieu": [{"mat_hang_id": 5, "so_luong_thieu": 10}]},
            ly_do=None,
            created_at=datetime(2026, 11, 14, tzinfo=timezone.utc),
        ),
        **changes,
    )


@pytest.mark.parametrize("roles", [[], ["nhan_vien"], ["unknown"], None, "quan_ly"])
async def test_uc43_ac03_ac08_service_denies_before_reading_repository(roles):
    repo = AsyncMock()
    service = AuditService(repo)
    actor = {"sub": "3", "roles": roles}
    with pytest.raises(ForbiddenException):
        await service.list_entries(AuditListQuery(), actor)
    with pytest.raises(ForbiddenException):
        await service.get_entry(1, actor)
    repo.list_entries.assert_not_awaited()
    repo.get_entry.assert_not_awaited()


@pytest.mark.parametrize("role", ["quan_tri_vien", "quan_ly"])
async def test_uc43_ac01_ac07_ac14_snapshot_is_preserved_for_both_roles(role):
    saved = record()
    repo = AsyncMock()
    repo.list_entries.return_value = RecordPage([saved], 1)
    repo.get_entry.return_value = saved
    service = AuditService(repo)
    actor = {"sub": "1", "roles": [role]}
    response = await service.list_entries(AuditListQuery(), actor)
    detail = await service.get_entry(1, actor)
    assert response.data[0] == detail.data
    assert detail.data.du_lieu_sau == saved.du_lieu_sau
    assert detail.data.du_lieu_truoc is None
    assert detail.data.trang_thai_sau == "cho_bo_sung_linh_kien"
    repo.append.assert_not_awaited()


async def test_uc43_ac04_ac15_redaction_is_recursive_without_mutating_evidence():
    snapshot = {
        "mat_khau": "plaintext-secret",
        "PasswordHash": "hash-secret",
        "items": [{"accessToken": "token-secret", "quantity": 10, "inner": {"pwdv": "secret"}}],
        "da_doi_mat_khau": True,
        "so_luong": 0,
        "active": False,
        "empty": None,
    }
    repo = AsyncMock()
    repo.get_entry.return_value = record(du_lieu_truoc=snapshot, du_lieu_sau=snapshot)
    repo.list_entries.return_value = RecordPage([repo.get_entry.return_value], 1)
    service = AuditService(repo)
    actor = {"roles": ["quan_ly"]}
    expected = {
        "items": [{"quantity": 10, "inner": {}}],
        "da_doi_mat_khau": True,
        "so_luong": 0,
        "active": False,
        "empty": None,
    }
    detail = await service.get_entry(1, actor)
    listing = await service.list_entries(AuditListQuery(), actor)
    for result in (detail.data, listing.data[0]):
        assert result.du_lieu_truoc == expected
        assert result.du_lieu_sau == expected
    assert snapshot["mat_khau"] == "plaintext-secret"
    assert snapshot["items"][0]["accessToken"] == "token-secret"
    detail.data.du_lieu_sau["items"][0]["quantity"] = 99
    assert snapshot["items"][0]["quantity"] == 10


@pytest.mark.parametrize(
    "key",
    [
        "hash",
        "password",
        "password_hash",
        "matKhauHash",
        "old-password",
        "newPassword",
        "current_password",
        "mat_khau_cu",
        "mat_khau_moi",
        "token",
        "access_token",
        "refreshToken",
        "id_token",
        "authorization",
        "cookie",
        "secret",
        "secret_key",
        "credentialVersion",
        "pwdv",
    ],
)
async def test_uc43_ac15_sensitive_key_variants_are_removed(key):
    repo = AsyncMock()
    repo.get_entry.return_value = record(du_lieu_sau={"nested": [{key: "hidden", "safe": 1}]})
    result = await AuditService(repo).get_entry(1, {"roles": ["quan_tri_vien"]})
    assert result.data.du_lieu_sau == {"nested": [{"safe": 1}]}


@pytest.mark.parametrize("entry_id", [1, 2**31, 10**50])
async def test_uc43_ac13_missing_or_out_of_integer_range_returns_not_found(entry_id):
    repo = AsyncMock()
    repo.get_entry.return_value = None
    with pytest.raises(NotFoundException):
        await AuditService(repo).get_entry(entry_id, {"roles": ["quan_ly"]})
    if entry_id > 2**31 - 1:
        repo.get_entry.assert_not_awaited()


async def test_uc43_ac13_nullable_states_and_snapshots_remain_null():
    repo = AsyncMock()
    repo.get_entry.return_value = record(
        trang_thai_truoc=None, trang_thai_sau=None, du_lieu_sau=None
    )
    result = await AuditService(repo).get_entry(1, {"roles": ["quan_ly"]})
    assert result.data.trang_thai_truoc is result.data.trang_thai_sau is None
    assert result.data.du_lieu_truoc is result.data.du_lieu_sau is None
    assert result.data.ly_do is None


@pytest.mark.parametrize(
    "filters,expected_from,expected_before",
    [
        (
            {"tu_ngay": "2026-11-14", "den_ngay": "2026-11-14"},
            datetime(2026, 11, 13, 17, tzinfo=timezone.utc),
            datetime(2026, 11, 14, 17, tzinfo=timezone.utc),
        ),
        ({"tu_ngay": "2026-11-14"}, datetime(2026, 11, 13, 17, tzinfo=timezone.utc), None),
        ({"den_ngay": "2026-11-14"}, None, datetime(2026, 11, 14, 17, tzinfo=timezone.utc)),
        ({}, None, None),
    ],
)
async def test_uc43_ac06_ac11_service_converts_inclusive_local_days_to_utc(
    filters, expected_from, expected_before
):
    repo = AsyncMock()
    repo.list_entries.return_value = RecordPage([], 0)
    params = AuditListQuery(**filters)
    result = await AuditService(repo).list_entries(params, {"roles": ["quan_ly"]})
    repo.list_entries.assert_awaited_once_with(
        params, created_from=expected_from, created_before=expected_before
    )
    assert result.data == [] and result.pagination.total_items == 0


@pytest.mark.parametrize(
    "values",
    [
        {"page": 0},
        {"page_size": 101},
        {"nhan_vien_id": 0},
        {"doi_tuong_id": 2**31},
        {"sort_by": "du_lieu_sau"},
        {"sort_order": "sideways"},
        {"thao_tac": "ve_nhap"},
        {"loai_doi_tuong": "lenh_san_xuat"},
        {"tu_ngay": "20261114"},
        {"tu_ngay": "2026-11-14T00:00:00Z"},
        {"tu_ngay": 20261114},
        {"tu_ngay": datetime(2026, 11, 14)},
        {"den_ngay": "9999-12-31"},
        {"tu_ngay": "0001-01-01"},
        {"tu_ngay": "2026-11-15", "den_ngay": "2026-11-14"},
        {"unknown": 1},
    ],
)
def test_uc43_ac11_ac12_query_rejects_invalid_values(values):
    with pytest.raises(ValidationError):
        AuditListQuery(**values)


def test_uc43_ac11_query_allows_dates_and_legacy_exclusion_without_legacy_actions():
    query = AuditListQuery(tu_ngay=date(2026, 11, 14), bo_thao_tac="thu_hoi_quyen", search="  ")
    assert query.search is None
    assert query.bo_thao_tac == "thu_hoi_quyen"


async def test_uc43_ac17_internal_append_still_defers_commit_to_caller():
    repo = AsyncMock()
    entry = CreationAudit(
        nhan_vien_id=1, loai_doi_tuong="nhan_vien", doi_tuong_id=1, du_lieu_sau=None
    )
    await AuditService(repo).append(entry)
    repo.append.assert_awaited_once_with(entry)


async def test_uc43_ac18_repository_failure_is_not_an_empty_success():
    repo = AsyncMock()
    repo.list_entries.side_effect = RuntimeError("database failure")
    with pytest.raises(RuntimeError, match="database failure"):
        await AuditService(repo).list_entries(AuditListQuery(), {"roles": ["quan_ly"]})
