"""Admin-only traffic statistics for the overview chart."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.exceptions import RequestValidationError

from app.core.request_context import get_request_id, reject_repeated_query
from app.dependencies import get_luu_luong_service, require_roles
from app.modules.luu_luong.schemas import KhoangThoiGian, LuuLuongResponse
from app.modules.luu_luong.service import LuuLuongService

router = APIRouter(prefix="/luu_luong_truy_cap", tags=["luu_luong"])

ALLOWED_QUERY = {"khoang_thoi_gian"}


def get_khoang_thoi_gian(
    request: Request,
    khoang_thoi_gian: Annotated[KhoangThoiGian, Query()] = "hom_nay",
) -> KhoangThoiGian:
    reject_repeated_query(request)
    unknown = [key for key in request.query_params if key not in ALLOWED_QUERY]
    if unknown:
        raise RequestValidationError(
            [
                {
                    "loc": ("query", key),
                    "msg": "Extra inputs are not permitted",
                    "type": "extra_forbidden",
                }
                for key in unknown
            ]
        )
    return khoang_thoi_gian


@router.get("", response_model=LuuLuongResponse)
async def get_series(
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien"]))],
    khoang: Annotated[KhoangThoiGian, Depends(get_khoang_thoi_gian)],
    service: Annotated[LuuLuongService, Depends(get_luu_luong_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> LuuLuongResponse:
    return await service.get_series(khoang, request_id)
