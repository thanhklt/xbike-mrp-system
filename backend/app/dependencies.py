"""FastAPI dependency composition; application services never import this module."""

from typing import Annotated, Optional

from fastapi import Depends, Query, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.core.database import get_db
from app.core.errors import ForbiddenException, UnauthorizedException
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.audit.service import AuditService
from app.modules.auth.service import AuthService
from app.modules.bom.repository import SqlAlchemyBomRepository
from app.modules.bom.service import BomPlanningReader, BomService
from app.modules.finished_goods_issuing.repository import SqlAlchemyFinishedGoodsIssuingRepository
from app.modules.finished_goods_issuing.service import FinishedGoodsIssuingService
from app.modules.inventory.repository import SqlAlchemyInventoryRepository
from app.modules.inventory.service import InventoryService
from app.modules.mat_hang.cache import MatHangCache
from app.modules.mat_hang.repository import SqlAlchemyMatHangRepository
from app.modules.mat_hang.service import MatHangAvailabilityService, MatHangReader, MatHangService
from app.modules.material_issuing.repository import SqlAlchemyMaterialIssuingRepository
from app.modules.material_issuing.service import MaterialIssuingService
from app.modules.nha_cung_cap.repository import SqlAlchemySupplierRepository
from app.modules.nha_cung_cap.service import SupplierService
from app.modules.nhan_vien.repository import SqlAlchemyNhanVienRepository
from app.modules.nhan_vien.service import NhanVienService
from app.modules.phieu_nhap.repository import SqlAlchemyPhieuNhapRepository
from app.modules.phieu_nhap.service import PhieuNhapService
from app.modules.phieu_xuat.repository import SqlAlchemyPhieuXuatRepository
from app.modules.phieu_xuat.service import PhieuXuatSanXuatService
from app.modules.reporting.repository import SqlAlchemyReportingRepository
from app.modules.reporting.service import ReportingService
from app.modules.san_xuat.repository import SqlAlchemyYeuCauSanXuatRepository
from app.modules.san_xuat.service import YeuCauSanXuatService
from app.modules.ticket_dieu_chinh.repository import SqlAlchemyTicketDieuChinhRepository
from app.modules.ticket_dieu_chinh.service import TicketDieuChinhService
from app.shared.pagination import PageParams

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_str}/auth/token", auto_error=False)


def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search filter"),
    sort_by: Optional[str] = Query("created_at", description="Sort field"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
) -> PageParams:
    return PageParams(
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


def get_audit_service(db: Annotated[AsyncSession, Depends(get_db)]) -> AuditService:
    return AuditService(SqlAlchemyAuditRepository(db))


def get_nhan_vien_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> NhanVienService:
    return NhanVienService(SqlAlchemyNhanVienRepository(db), audit, SqlAlchemyTransaction(db))


def get_auth_service(
    employees: Annotated[NhanVienService, Depends(get_nhan_vien_service)],
) -> AuthService:
    return AuthService(employees)


async def get_current_user_payload(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    if not token:
        raise UnauthorizedException()
    return await service.current_payload(token)


def require_roles(allowed_roles: list[str]):
    async def role_checker(payload: Annotated[dict, Depends(get_current_user_payload)]) -> dict:
        if not any(role in allowed_roles for role in payload.get("roles", [])):
            raise ForbiddenException(message="You do not have permission to perform this action")
        return payload

    role_checker.allowed_roles = frozenset(allowed_roles)
    return role_checker


def get_suppliers_service(db: Annotated[AsyncSession, Depends(get_db)]) -> SupplierService:
    return SupplierService(
        SqlAlchemySupplierRepository(db),
        SqlAlchemyAuditRepository(db),
        SqlAlchemyTransaction(db),
    )


def get_mat_hang_cache(request: Request) -> MatHangCache:
    return request.app.state.mat_hang_cache


def get_mat_hang_reader(
    cache: Annotated[MatHangCache, Depends(get_mat_hang_cache)],
) -> MatHangReader:
    return MatHangReader(cache)


def get_mat_hang_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[MatHangCache, Depends(get_mat_hang_cache)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> MatHangService:
    return MatHangService(SqlAlchemyMatHangRepository(db), audit, SqlAlchemyTransaction(db), cache)


def get_mat_hang_availability(db: AsyncSession) -> MatHangAvailabilityService:
    return MatHangAvailabilityService(SqlAlchemyMatHangRepository(db))


def get_bom_service(db: Annotated[AsyncSession, Depends(get_db)]) -> BomService:
    return BomService(
        SqlAlchemyBomRepository(db),
        SqlAlchemyAuditRepository(db),
        SqlAlchemyTransaction(db),
        get_mat_hang_availability(db),
    )


def get_receiving_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> PhieuNhapService:
    return PhieuNhapService(
        SqlAlchemyPhieuNhapRepository(db),
        audit,
        SqlAlchemyTransaction(db),
        SqlAlchemyInventoryRepository(db),
    )


def get_material_issuing_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MaterialIssuingService:
    return MaterialIssuingService(
        SqlAlchemyMaterialIssuingRepository(db),
        SqlAlchemyAuditRepository(db),
        SqlAlchemyTransaction(db),
        get_mat_hang_availability(db),
    )


def get_finished_goods_issuing_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FinishedGoodsIssuingService:
    return FinishedGoodsIssuingService(
        SqlAlchemyFinishedGoodsIssuingRepository(db),
        SqlAlchemyAuditRepository(db),
        SqlAlchemyTransaction(db),
        get_mat_hang_availability(db),
    )


def get_yeu_cau_san_xuat_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> YeuCauSanXuatService:
    audit = AuditService(SqlAlchemyAuditRepository(db))
    transaction = SqlAlchemyTransaction(db)
    return YeuCauSanXuatService(
        SqlAlchemyYeuCauSanXuatRepository(db),
        audit,
        transaction,
        get_mat_hang_availability(db),
        NhanVienService(SqlAlchemyNhanVienRepository(db), audit, transaction),
        BomPlanningReader(SqlAlchemyBomRepository(db)),
        PhieuXuatSanXuatService(SqlAlchemyPhieuXuatRepository(db), audit),
    )


def get_inventory_service(db: Annotated[AsyncSession, Depends(get_db)]) -> InventoryService:
    return InventoryService(SqlAlchemyInventoryRepository(db))


def get_reporting_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ReportingService:
    return ReportingService(SqlAlchemyReportingRepository(db))


def get_ticket_dieu_chinh_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> TicketDieuChinhService:
    return TicketDieuChinhService(
        SqlAlchemyTicketDieuChinhRepository(db), audit, SqlAlchemyTransaction(db)
    )
