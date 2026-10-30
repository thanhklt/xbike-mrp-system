"""Employee lookup, permissions, projections and contract v2 responses."""

import asyncio
import hmac
from hashlib import sha256
from math import ceil

from app.core.errors import (
    ForbiddenException,
    InactiveAccountException,
    InvalidCredentialsException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import get_password_hash, password_version, verify_password
from app.core.transactions import Transaction
from app.modules.audit.service import AuditService, CreationAudit
from app.modules.nhan_vien.ports import NhanVienRepository
from app.modules.nhan_vien.schemas import (
    MAX_EMPLOYEE_ID,
    AuthIdentity,
    EmployeeCredentials,
    EmployeeRecord,
    ListResponseMeta,
    NhanVienAssignmentRead,
    NhanVienDetailResponse,
    NhanVienListQuery,
    NhanVienListResponse,
    NhanVienRead,
    ResponseMeta,
)

__all__ = ["NhanVienService", "AuthIdentity", "NhanVienRead", "ResponseMeta"]


def _require_active(user: EmployeeCredentials) -> None:
    if user.trang_thai != "hoat_dong":
        raise InactiveAccountException()
    if not {"quan_tri_vien", "quan_ly", "nhan_vien"}.intersection(user.roles):
        raise ForbiddenException()


def _require_current_password(user: EmployeeCredentials, version: str) -> None:
    if (
        not isinstance(version, str)
        or not version.isascii()
        or not hmac.compare_digest(version, password_version(user.password_hash))
    ):
        raise UnauthorizedException(message="Please sign in again")


def _identity(user: EmployeeCredentials) -> AuthIdentity:
    return AuthIdentity(
        profile=NhanVienRead.model_validate(user),
        roles=user.roles,
        credential_version=password_version(user.password_hash),
    )


def _employee_response(user: EmployeeRecord, actor: dict, *, detail: bool = False):
    full_profile = "quan_tri_vien" in actor["roles"] or (detail and user.id == int(actor["sub"]))
    schema = NhanVienRead if full_profile else NhanVienAssignmentRead
    values = {name: getattr(user, name) for name in schema.model_fields if name != "ma_vai_tro"}
    values["ma_vai_tro"] = user.ma_vai_tro
    return schema.model_validate(values)


class NhanVienService:
    def __init__(
        self, repository: NhanVienRepository, audit: AuditService, transaction: Transaction
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction

    async def authenticate_employee(
        self, identifier: str, password: str, *, allow_email: bool = False
    ) -> AuthIdentity:
        user = await self.repository.find_by_username(identifier)
        if user is None and allow_email:
            user = await self.repository.find_unique_by_email(identifier)
        if user is None or not await asyncio.to_thread(
            verify_password, password, user.password_hash
        ):
            raise InvalidCredentialsException()
        _require_active(user)
        return _identity(user)

    async def get_auth_identity(self, employee_id: int, *, credential_version: str) -> AuthIdentity:
        if not 1 <= employee_id <= MAX_EMPLOYEE_ID:
            raise UnauthorizedException(message="Invalid token subject")
        user = await self.repository.get_credentials_by_id(employee_id)
        if user is None:
            raise UnauthorizedException(message="Employee no longer exists")
        _require_active(user)
        _require_current_password(user, credential_version)
        return _identity(user)

    async def change_password(
        self, employee_id: int, current_password: str, new_password: str, *, credential_version: str
    ) -> None:
        async with self.transaction:
            user = await self.repository.lock_credentials_by_id(employee_id)
            if user is None:
                raise UnauthorizedException(message="Employee no longer exists")
            _require_active(user)
            _require_current_password(user, credential_version)
            if not await asyncio.to_thread(verify_password, current_password, user.password_hash):
                raise InvalidCredentialsException()
            new_hash = await asyncio.to_thread(get_password_hash, new_password)
            await self.repository.set_password_hash(user.id, new_hash)
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=user.id,
                    loai_doi_tuong="nhan_vien",
                    doi_tuong_id=user.id,
                    thao_tac="sua",
                    du_lieu_sau={"da_doi_mat_khau": True},
                )
            )

    async def list_employees(
        self,
        params: NhanVienListQuery,
        actor: dict,
        request_id: str,
    ) -> NhanVienListResponse:
        if not {"quan_tri_vien", "quan_ly"}.intersection(actor["roles"]):
            raise ForbiddenException()
        result = await self.repository.list_employees(params)
        total = result.total
        records = result.items
        return NhanVienListResponse(
            data=[_employee_response(user, actor) for user in records],
            meta=ListResponseMeta(
                request_id=request_id,
                page=params.page,
                page_size=params.page_size,
                total=total,
                total_pages=ceil(total / params.page_size),
            ),
        )

    async def get_employee(
        self,
        employee_id: int,
        actor: dict,
        request_id: str,
    ) -> tuple[NhanVienDetailResponse, str]:
        if employee_id > MAX_EMPLOYEE_ID:
            raise NotFoundException(message=f"nhan_vien {employee_id} not found")
        user = await self.repository.get_by_id(employee_id)
        if user is None:
            raise NotFoundException(message=f"nhan_vien {employee_id} not found")
        if (
            not {"quan_tri_vien", "quan_ly"}.intersection(actor["roles"])
            and int(actor["sub"]) != employee_id
        ):
            raise ForbiddenException()
        profile = _employee_response(user, actor, detail=True)
        # Exclude per-request metadata from the strong representation ETag.
        etag = f'"{sha256(profile.model_dump_json().encode("utf-8")).hexdigest()}"'
        return NhanVienDetailResponse(data=profile, meta=ResponseMeta(request_id=request_id)), etag
