"""Six item endpoints; reads use the application snapshot."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status

from app.core.request_context import (
    get_request_id,
    get_strong_if_match,
    reject_body,
    reject_query,
    reject_repeated_query,
)
from app.dependencies import (
    get_current_user_payload,
    get_mat_hang_reader,
    get_mat_hang_service,
    require_roles,
)
from app.modules.mat_hang.schemas import (
    DanhMucMatHangResponse,
    MatHangCreate,
    MatHangListQuery,
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


@router.get(
    "/danh_muc_mat_hang/",
    response_model=DanhMucMatHangResponse,
    dependencies=[Depends(reject_query), Depends(reject_body)],
)
async def get_danh_muc(request: Request, service: Reader, actor: ReadRole):
    """UC-09: specs/use_cases/catalog/UC-09.md, full read-only snapshot."""
    result = await service.danh_muc(actor)
    result.meta.request_id = get_request_id(request)
    return result


@router.get(
    "/mat_hang",
    response_model=MatHangListResponse,
    dependencies=[Depends(reject_repeated_query), Depends(reject_body)],
)
async def list_mat_hang(
    request: Request, service: Reader, actor: ReadRole, params: Annotated[MatHangListQuery, Query()]
):
    """UC-09: specs/use_cases/catalog/UC-09.md."""
    result = await service.list_mat_hang(params, actor)
    result.meta.request_id = get_request_id(request)
    return result


@router.get(
    "/mat_hang/{id}",
    response_model=MatHangSingleResponse,
    dependencies=[Depends(reject_query), Depends(reject_body)],
)
async def get_mat_hang_detail(
    id: Annotated[int, Path(gt=0)],
    request: Request,
    response: Response,
    service: Reader,
    actor: ReadRole,
):
    """UC-09: specs/use_cases/catalog/UC-09.md, item/BOM context strong ETag."""
    record, etag = await service.get_mat_hang(id, actor)
    response.headers["ETag"] = etag
    return MatHangSingleResponse(data=record, meta=SingleMeta(request_id=get_request_id(request)))


@router.post(
    "/mat_hang",
    response_model=MatHangSingleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(reject_query)],
)
async def create_mat_hang(
    payload: MatHangCreate, request: Request, response: Response, service: Writer, actor: WriteRole
):
    """UC-10/16 — specs/use_cases/bom/UC-16.md: tạo thành phẩm cùng BOM v1."""
    record, etag = await service.create_mat_hang(payload, actor)
    response.headers["ETag"] = etag
    response.headers["Location"] = f"/api/v1/mat_hang/{record.id}"
    return MatHangSingleResponse(data=record, meta=SingleMeta(request_id=get_request_id(request)))


@router.patch(
    "/mat_hang/{id}", response_model=MatHangSingleResponse, dependencies=[Depends(reject_query)]
)
async def patch_mat_hang(
    id: Annotated[int, Path(gt=0)],
    payload: MatHangPatch,
    request: Request,
    response: Response,
    service: Writer,
    actor: WriteRole,
    if_match: Annotated[str | None, Depends(get_strong_if_match)] = None,
):
    """UC-11/12 — trạng thái thành phẩm đi cùng BOM, cùng transaction và audit."""
    record, etag = await service.patch_mat_hang(id, payload, if_match, actor)
    response.headers["ETag"] = etag
    return MatHangSingleResponse(data=record, meta=SingleMeta(request_id=get_request_id(request)))


@router.delete(
    "/mat_hang/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(reject_query), Depends(reject_body)],
)
async def delete_mat_hang(
    id: Annotated[int, Path(gt=0)],
    service: Writer,
    actor: WriteRole,
    if_match: Annotated[str | None, Depends(get_strong_if_match)] = None,
):
    """UC-12/19 — ngừng thành phẩm và công thức, không xóa cứng."""
    await service.delete_mat_hang(id, if_match, actor)
    return Response(status_code=204)
