"""API báo cáo dành riêng cho quản lý kho."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_bao_cao_service, require_roles
from app.modules.reporting.schemas import NhapXuatTonQuery, NhapXuatTonResponse
from app.modules.reporting.service import BaoCaoService

router = APIRouter(
    prefix="/bao_cao",
    tags=["Báo cáo"],
    dependencies=[Depends(require_roles(["quan_ly"]))],
)


def get_report_query(params: Annotated[NhapXuatTonQuery, Query()]) -> NhapXuatTonQuery:
    return params


# UC-41 Xem báo cáo nhập-xuất-tồn — Main 1–4; R1–R5, A1–A3 (specs/use_cases/reporting/UC-41.md)
@router.get(
    "/nhap_xuat_ton",
    response_model=NhapXuatTonResponse,
    summary="UC-41: Xem báo cáo nhập-xuất-tồn",
    description="specs/use_cases/reporting/UC-41.md. Chỉ quản lý kho; kỳ theo giờ Việt Nam, không phân trang, chỉ đọc.",
)
async def nhap_xuat_ton(
    query: Annotated[NhapXuatTonQuery, Depends(get_report_query)],
    service: Annotated[BaoCaoService, Depends(get_bao_cao_service)],
) -> NhapXuatTonResponse:
    return await service.nhap_xuat_ton(query)
