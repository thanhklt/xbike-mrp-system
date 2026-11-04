"""Boundary checks for production completion documents, independent of a database."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.modules.san_xuat.schemas import HoanThanhCreate, HoanThanhPatch, HoanThanhQuery


@pytest.mark.parametrize("field", ["lenh_san_xuat_id", "so_luong_hoan_thanh"])
@pytest.mark.parametrize("value", [True, 1.5, "1", 0, -1, 2**31, None])
def test_completion_ids_and_quantity_are_positive_int32(field, value):
    payload = {
        "lenh_san_xuat_id": 1,
        "so_luong_hoan_thanh": 3,
        "finish_time": "2026-11-03T12:00:00+07:00",
        field: value,
    }
    with pytest.raises(ValidationError):
        HoanThanhCreate.model_validate(payload)


@pytest.mark.parametrize("value", [None, 1793696400, "2026-11-03T12:00:00"])
def test_completion_requires_aware_iso_time(value):
    with pytest.raises(ValidationError):
        HoanThanhCreate(lenh_san_xuat_id=1, so_luong_hoan_thanh=1, finish_time=value)


def test_completion_normalizes_time_to_utc():
    payload = HoanThanhCreate(
        lenh_san_xuat_id=1,
        so_luong_hoan_thanh=1,
        finish_time="2026-11-03T12:00:00+07:00",
    )
    assert payload.finish_time == datetime(2026, 11, 3, 5, tzinfo=timezone.utc)
    assert payload.finish_time.utcoffset().total_seconds() == 0


@pytest.mark.parametrize(
    "payload",
    [{}, {"finish_time": None}, {"so_luong_hoan_thanh": None}, {"trang_thai": "da_duyet"}],
)
def test_completion_patch_rejects_empty_null_and_server_fields(payload):
    with pytest.raises(ValidationError):
        HoanThanhPatch.model_validate(payload)


@pytest.mark.parametrize(
    "query",
    [
        {"tu_ngay": "2026-11-04", "den_ngay": "2026-11-03"},
        {"den_ngay": "9999-12-31"},
        {"sort": "created_at"},
        {"page_size": 101},
    ],
)
def test_completion_query_rejects_invalid_bounds(query):
    with pytest.raises(ValidationError):
        HoanThanhQuery.model_validate(query)
