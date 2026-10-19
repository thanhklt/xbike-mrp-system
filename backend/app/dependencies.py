"""FastAPI dependency composition; application services never import this module."""

from typing import Annotated, Optional

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import ForbiddenException
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.audit.service import AuditService
from app.modules.auth.repository import SqlAlchemyAuthRepository
from app.modules.auth.service import AuthService
from app.modules.bom.repository import SqlAlchemyBomRepository
from app.modules.bom.service import BomService
from app.modules.catalog.repository import SqlAlchemyCatalogRepository
from app.modules.catalog.service import CatalogService
from app.modules.finished_goods_issuing.repository import SqlAlchemyFinishedGoodsIssuingRepository
from app.modules.finished_goods_issuing.service import FinishedGoodsIssuingService
from app.modules.inventory.repository import SqlAlchemyInventoryRepository
from app.modules.inventory.service import InventoryService
from app.modules.material_issuing.repository import SqlAlchemyMaterialIssuingRepository
from app.modules.material_issuing.service import MaterialIssuingService
from app.modules.nhan_vien.ports import EmployeeRepository
from app.modules.nhan_vien.repository import SqlAlchemyEmployeeRepository
from app.modules.production.repository import SqlAlchemyProductionRepository
from app.modules.production.service import ProductionService
from app.modules.receiving.repository import SqlAlchemyReceivingRepository
from app.modules.receiving.service import ReceivingService
from app.modules.reporting.repository import SqlAlchemyReportingRepository
from app.modules.reporting.service import ReportingService
from app.modules.suppliers.repository import SqlAlchemySupplierRepository
from app.modules.suppliers.service import SupplierService
from app.shared.pagination import PageParams

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")


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


def get_auth_service(db: Annotated[AsyncSession, Depends(get_db)]) -> AuthService:
    return AuthService(SqlAlchemyAuthRepository(db))


def get_employee_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> EmployeeRepository:
    return SqlAlchemyEmployeeRepository(db)


def get_audit_service(db: Annotated[AsyncSession, Depends(get_db)]) -> AuditService:
    return AuditService(SqlAlchemyAuditRepository(db))


async def get_current_user_payload(
    token: Annotated[str, Depends(oauth2_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    return await service.current_payload(token)


def require_roles(allowed_roles: list[str]):
    async def role_checker(payload: Annotated[dict, Depends(get_current_user_payload)]) -> dict:
        if not any(role in allowed_roles for role in payload.get("roles", [])):
            raise ForbiddenException(message="You do not have permission to perform this action")
        return payload

    return role_checker


def get_suppliers_service(db: Annotated[AsyncSession, Depends(get_db)]) -> SupplierService:
    return SupplierService(
        SqlAlchemySupplierRepository(db),
        SqlAlchemyAuditRepository(db),
        SqlAlchemyTransaction(db),
    )


def get_catalog_service(db: Annotated[AsyncSession, Depends(get_db)]) -> CatalogService:
    return CatalogService(
        SqlAlchemyCatalogRepository(db),
        SqlAlchemyAuditRepository(db),
        SqlAlchemyTransaction(db),
    )


def get_bom_service(db: Annotated[AsyncSession, Depends(get_db)]) -> BomService:
    return BomService(
        SqlAlchemyBomRepository(db),
        SqlAlchemyAuditRepository(db),
        SqlAlchemyTransaction(db),
    )


def get_receiving_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ReceivingService:
    return ReceivingService(
        SqlAlchemyReceivingRepository(db),
        SqlAlchemyAuditRepository(db),
        SqlAlchemyTransaction(db),
    )


def get_material_issuing_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MaterialIssuingService:
    return MaterialIssuingService(
        SqlAlchemyMaterialIssuingRepository(db),
        SqlAlchemyAuditRepository(db),
        SqlAlchemyTransaction(db),
    )


def get_finished_goods_issuing_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FinishedGoodsIssuingService:
    return FinishedGoodsIssuingService(
        SqlAlchemyFinishedGoodsIssuingRepository(db),
        SqlAlchemyAuditRepository(db),
        SqlAlchemyTransaction(db),
    )


def get_production_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ProductionService:
    return ProductionService(
        SqlAlchemyProductionRepository(db),
        SqlAlchemyAuditRepository(db),
        SqlAlchemyTransaction(db),
    )


def get_inventory_service(db: Annotated[AsyncSession, Depends(get_db)]) -> InventoryService:
    return InventoryService(SqlAlchemyInventoryRepository(db))


def get_reporting_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ReportingService:
    return ReportingService(SqlAlchemyReportingRepository(db))
