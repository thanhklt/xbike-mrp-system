"""Unit tests for mat_hang module (schemas, ETag, validation, RBAC, endpoints)."""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.modules.mat_hang.models import MatHang
from app.modules.mat_hang.schemas import MatHangCreate, MatHangPatch
from app.modules.mat_hang.router import (
    generate_mat_hang_etag,
    verify_if_match,
)


def test_mathang_create_valid():
    """Verify MatHangCreate accepts valid fields adhering to contract v2."""
    data = {
        "ma_mat_hang": "MH-000099",
        "sku": "khung_nhom_6061",
        "ten_mat_hang": "Khung nhôm 6061",
        "loai_mat_hang": "linh_kien",
        "don_vi_tinh": "chiec",
        "mau_sac": "den_nham",
        "mo_ta": "Khung xe leo núi",
        "don_gia": 1500000,
        "is_active": True,
    }
    obj = MatHangCreate(**data)
    assert obj.ma_mat_hang == "MH-000099"
    assert obj.loai_mat_hang == "linh_kien"


def test_mathang_create_rejects_ending_zeros():
    """Verify MH-000000 is rejected by validation."""
    with pytest.raises(ValidationError):
        MatHangCreate(
            ma_mat_hang="MH-000000",
            sku="khung_01",
            loai_mat_hang="linh_kien",
            don_vi_tinh="chiec",
        )


def test_mathang_create_rejects_invalid_code_format():
    """Verify irregular code patterns are rejected."""
    with pytest.raises(ValidationError):
        MatHangCreate(
            ma_mat_hang="PART-123456",
            sku="sku_test",
            loai_mat_hang="linh_kien",
            don_vi_tinh="chiec",
        )


def test_mathang_create_rejects_extra_fields():
    """Verify extra fields are forbidden."""
    with pytest.raises(ValidationError):
        MatHangCreate(
            ma_mat_hang="MH-000001",
            sku="sku_test",
            loai_mat_hang="linh_kien",
            don_vi_tinh="chiec",
            extra_field="not_allowed",
        )


def test_mathang_create_rejects_invalid_don_vi_tinh():
    """Verify non-snake_case unit names are rejected."""
    with pytest.raises(ValidationError):
        MatHangCreate(
            ma_mat_hang="MH-000001",
            sku="sku_test",
            loai_mat_hang="linh_kien",
            don_vi_tinh="Chiếc Xe",
        )


def test_mathang_patch_validation():
    """Verify MatHangPatch handles partial updates with strict field formats."""
    patch = MatHangPatch(ten_mat_hang="Tên mới", don_gia=2000000)
    assert patch.ten_mat_hang == "Tên mới"
    assert patch.don_gia == 2000000

    with pytest.raises(ValidationError):
        MatHangPatch(ma_mat_hang="MH-000000")


def test_etag_generation():
    """Verify ETag generation produces quoted, stable SHA256 string."""
    item = MatHang(
        id=1,
        ma_mat_hang="MH-000001",
        sku="xe_dap_leo_nui",
        ten_mat_hang="Xe đạp leo núi",
        loai_mat_hang="thanh_pham",
        don_vi_tinh="chiec",
        mau_sac="do",
        mo_ta=None,
        don_gia=5000000,
        is_active=True,
    )
    etag1 = generate_mat_hang_etag(item)
    etag2 = generate_mat_hang_etag(item)

    assert etag1.startswith('"') and etag1.endswith('"')
    assert etag1 == etag2

    # Change field, ETag must change
    item.don_gia = 5500000
    etag3 = generate_mat_hang_etag(item)
    assert etag3 != etag1


def test_verify_if_match_success():
    """Verify correct ETag passes If-Match check."""
    etag = '"abc123hash"'
    verify_if_match('"abc123hash"', etag)
    verify_if_match("abc123hash", etag)


def test_verify_if_match_missing_raises_428():
    """Verify missing If-Match header raises 428 Precondition Required."""
    with pytest.raises(HTTPException) as exc_info:
        verify_if_match(None, '"abc123hash"')
    assert exc_info.value.status_code == 428


def test_verify_if_match_mismatch_raises_412():
    """Verify mismatched ETag raises 412 Precondition Failed."""
    with pytest.raises(HTTPException) as exc_info:
        verify_if_match('"wrong_etag"', '"abc123hash"')
    assert exc_info.value.status_code == 412


@pytest.mark.asyncio
async def test_api_list_mat_hang_unauthorized(async_client):
    """Calling /api/v1/mat_hang without authorization header returns 401."""
    response = await async_client.get("/api/v1/mat_hang")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_create_mat_hang_forbidden_for_nhan_vien(async_client):
    """Nhan vien role (N) is forbidden from POST /api/v1/mat_hang (403)."""
    from app.dependencies import get_current_user_payload
    from app.main import app

    app.dependency_overrides[get_current_user_payload] = lambda: {
        "sub": "3",
        "roles": ["nhan_vien"],
    }
    try:
        response = await async_client.post(
            "/api/v1/mat_hang",
            json={
                "ma_mat_hang": "MH-000088",
                "sku": "sku_88",
                "ten_mat_hang": "Mặt hàng 88",
                "loai_mat_hang": "linh_kien",
                "don_vi_tinh": "cai",
            },
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_create_mat_hang_validation_error(async_client):
    """Invalid payload returns 422 Unprocessable Entity."""
    from app.dependencies import get_current_user_payload
    from app.main import app

    app.dependency_overrides[get_current_user_payload] = lambda: {
        "sub": "2",
        "roles": ["quan_ly"],
    }
    try:
        response = await async_client.post(
            "/api/v1/mat_hang",
            json={
                "ma_mat_hang": "MH-000000",  # invalid ending with 000000
                "sku": "sku_88",
                "loai_mat_hang": "linh_kien",
                "don_vi_tinh": "cai",
            },
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_openapi_schema_contains_mat_hang_endpoints():
    """Verify OpenAPI spec includes all 5 mat_hang endpoints."""
    from app.main import app

    schema = app.openapi()
    paths = schema.get("paths", {})
    assert "/api/v1/mat_hang" in paths
    assert "get" in paths["/api/v1/mat_hang"]
    assert "post" in paths["/api/v1/mat_hang"]
    assert "/api/v1/mat_hang/{id}" in paths
    assert "get" in paths["/api/v1/mat_hang/{id}"]
    assert "patch" in paths["/api/v1/mat_hang/{id}"]
    assert "delete" in paths["/api/v1/mat_hang/{id}"]


@pytest.mark.asyncio
async def test_api_list_mat_hang_reversed_price_range_422(async_client):
    """Passing don_gia_min > don_gia_max returns 422 Unprocessable Entity."""
    from app.dependencies import get_current_user_payload
    from app.main import app

    app.dependency_overrides[get_current_user_payload] = lambda: {
        "sub": "2",
        "roles": ["quan_ly"],
    }
    try:
        response = await async_client.get("/api/v1/mat_hang?don_gia_min=5000&don_gia_max=1000")
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
