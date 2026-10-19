"""MatHang router: thin controller delegating to MatHangService."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.dependencies import (
    get_current_user_payload,
    get_mat_hang_service,
    require_roles,
)
from app.modules.mat_hang.schemas import (
    MatHangCreate,
    MatHangListResponse,
    MatHangPatch,
    MatHangSingleResponse,
)
from app.modules.mat_hang.service import (
    MatHangService,
    generate_mat_hang_etag,
    verify_if_match,
)

__all__ = ["generate_mat_hang_etag", "router", "verify_if_match"]

router = APIRouter(
    prefix="/mat_hang",
    tags=["Mặt hàng"],
    dependencies=[Depends(get_current_user_payload)],
)


@router.get("", response_model=MatHangListResponse)
async def list_mat_hang(
    service: Annotated[MatHangService, Depends(get_mat_hang_service)],
    _: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly", "nhan_vien"]))],
    q: str | None = Query(None, description="Tìm theo mã, tên hoặc SKU"),
    loai_mat_hang: (
        Literal["nguyen_vat_lieu", "linh_kien", "ban_thanh_pham", "thanh_pham"] | None
    ) = Query(None),
    is_active: bool | None = Query(None),
    don_vi_tinh: str | None = Query(None),
    mau_sac: str | None = Query(None),
    don_gia_min: int | None = Query(None, ge=0),
    don_gia_max: int | None = Query(None, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query(
        "id",
        description="Sort field, prefix '-' for desc. Whitelist: id, ma_mat_hang, ten_mat_hang, don_gia",
    ),
):
    """Lấy danh sách mặt hàng hỗ trợ phân trang, lọc và sắp xếp."""
    return await service.list_mat_hang(
        q=q,
        loai_mat_hang=loai_mat_hang,
        is_active=is_active,
        don_vi_tinh=don_vi_tinh,
        mau_sac=mau_sac,
        don_gia_min=don_gia_min,
        don_gia_max=don_gia_max,
        page=page,
        page_size=page_size,
        sort=sort,
    )


@router.get("/{id}", response_model=MatHangSingleResponse)
async def get_mat_hang_detail(
    id: int,
    response: Response,
    service: Annotated[MatHangService, Depends(get_mat_hang_service)],
    _: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly", "nhan_vien"]))],
):
    """Lấy chi tiết mặt hàng theo ID và trả về header ETag."""
    data, etag = await service.get_mat_hang(id)
    response.headers["ETag"] = etag
    return MatHangSingleResponse(data=data)


@router.post("", response_model=MatHangSingleResponse, status_code=status.HTTP_201_CREATED)
async def create_mat_hang(
    payload: MatHangCreate,
    response: Response,
    service: Annotated[MatHangService, Depends(get_mat_hang_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    """Tạo mới một mặt hàng. Yêu cầu quyền quản lý hoặc quản trị."""
    data, etag = await service.create_mat_hang(payload, actor)
    response.headers["ETag"] = etag
    response.headers["Location"] = f"/api/v1/mat_hang/{data.id}"
    return MatHangSingleResponse(data=data)


@router.patch("/{id}", response_model=MatHangSingleResponse)
async def patch_mat_hang(
    id: int,
    payload: MatHangPatch,
    response: Response,
    service: Annotated[MatHangService, Depends(get_mat_hang_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
    if_match: str | None = Header(None, alias="If-Match"),
):
    """Cập nhật mặt hàng. Bắt buộc header If-Match. Chặn thay đổi các trường bất biến nếu đã có tham chiếu."""
    data, etag = await service.patch_mat_hang(id, payload, if_match, actor)
    response.headers["ETag"] = etag
    return MatHangSingleResponse(data=data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mat_hang(
    id: int,
    service: Annotated[MatHangService, Depends(get_mat_hang_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
    if_match: str | None = Header(None, alias="If-Match"),
):
    """Xóa mặt hàng. Bắt buộc If-Match. Chặn xóa nếu có dữ liệu tham chiếu hoặc tồn kho > 0."""
    await service.delete_mat_hang(id, if_match, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
