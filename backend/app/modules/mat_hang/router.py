"""Six item endpoints; reads use the application snapshot."""

from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status

from app.core.request_context import get_request_id
from app.dependencies import (
    get_current_user_payload,
    get_mat_hang_reader,
    get_mat_hang_service,
    require_roles,
)
from app.modules.mat_hang.schemas import (
    DanhMucMatHangResponse,
    MatHangCreate,
    MatHangListResponse,
    MatHangPatch,
    MatHangSingleResponse,
    SingleMeta,
)
from app.modules.mat_hang.service import (
    MatHangReader,
    MatHangService,
    generate_mat_hang_etag,
    verify_if_match,
)

__all__ = ["generate_mat_hang_etag", "router", "verify_if_match"]

router = APIRouter(tags=["Mặt hàng"], dependencies=[Depends(get_current_user_payload)])
Reader = Annotated[MatHangReader, Depends(get_mat_hang_reader)]
Writer = Annotated[MatHangService, Depends(get_mat_hang_service)]
ReadRole = Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly", "nhan_vien"]))]
WriteRole = Annotated[dict, Depends(require_roles(["quan_ly"]))]


@router.get("/danh_muc_mat_hang/", response_model=DanhMucMatHangResponse)
async def get_danh_muc(request: Request, service: Reader, _: ReadRole):
    result = await service.danh_muc()
    result.meta.request_id = get_request_id(request)
    return result


@router.get("/mat_hang", response_model=MatHangListResponse)
async def list_mat_hang(
    request: Request,
    service: Reader,
    _: ReadRole,
    q: str | None = Query(None),
    loai_mat_hang: Literal["nguyen_vat_lieu", "linh_kien", "ban_thanh_pham", "thanh_pham"]
    | None = Query(None),
    is_active: bool | None = Query(None),
    don_vi_tinh: str | None = Query(None),
    mau_sac: str | None = Query(None),
    don_gia_min: Annotated[Decimal | None, Query(ge=0)] = None,
    don_gia_max: Annotated[Decimal | None, Query(ge=0)] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("id"),
):
    result = await service.list_mat_hang(
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
    result.meta.request_id = get_request_id(request)
    return result


@router.get("/mat_hang/{id}", response_model=MatHangSingleResponse)
async def get_mat_hang_detail(
    id: int, request: Request, response: Response, service: Reader, _: ReadRole
):
    record, etag = await service.get_mat_hang(id)
    response.headers["ETag"] = etag
    return MatHangSingleResponse(data=record, meta=SingleMeta(request_id=get_request_id(request)))


@router.post("/mat_hang", response_model=MatHangSingleResponse, status_code=status.HTTP_201_CREATED)
async def create_mat_hang(
    payload: MatHangCreate, request: Request, response: Response, service: Writer, actor: WriteRole
):
    record, etag = await service.create_mat_hang(payload, actor)
    response.headers["ETag"] = etag
    response.headers["Location"] = f"/api/v1/mat_hang/{record.id}"
    return MatHangSingleResponse(data=record, meta=SingleMeta(request_id=get_request_id(request)))


@router.patch("/mat_hang/{id}", response_model=MatHangSingleResponse)
async def patch_mat_hang(
    id: int,
    payload: MatHangPatch,
    request: Request,
    response: Response,
    service: Writer,
    actor: WriteRole,
    if_match: str | None = Header(None, alias="If-Match"),
):
    record, etag = await service.patch_mat_hang(id, payload, if_match, actor)
    response.headers["ETag"] = etag
    return MatHangSingleResponse(data=record, meta=SingleMeta(request_id=get_request_id(request)))


@router.delete("/mat_hang/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mat_hang(
    id: int,
    service: Writer,
    actor: WriteRole,
    if_match: str | None = Header(None, alias="If-Match"),
):
    await service.delete_mat_hang(id, if_match, actor)
    return Response(status_code=204)
