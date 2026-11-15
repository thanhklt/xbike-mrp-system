"""Employee lookup, permissions, projections and contract v2 responses."""

import asyncio
import hmac
from hashlib import sha256
from math import ceil

from app.core.errors import (
    ConflictException,
    DuplicateUsernameException,
    ForbiddenException,
    InactiveAccountException,
    InvalidAssignee,
    InvalidCredentialsException,
    InvalidWorkflowState,
    LastActiveAdminException,
    NotFoundException,
    PreconditionFailedException,
    PreconditionRequiredException,
    UnauthorizedException,
    UnfinishedAssignmentException,
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
    NewEmployee,
    NhanVienAssignmentRead,
    NhanVienCreate,
    NhanVienDetailResponse,
    NhanVienListQuery,
    NhanVienListResponse,
    NhanVienPatch,
    NhanVienRead,
    ResponseMeta,
    VaiTroListQuery,
    VaiTroListResponse,
    VaiTroRead,
)

__all__ = ["NhanVienService", "AuthIdentity", "NhanVienRead", "ResponseMeta"]


# UC-01 Đăng nhập — Main 4; R2, A3 (specs/use_cases/identity_access/UC-01.md)
# UC-02 Đăng xuất — A2: từ chối tài khoản khóa hoặc vai trò không hợp lệ (specs/use_cases/identity_access/UC-02.md)
def _require_active(user: EmployeeCredentials) -> None:
    if user.trang_thai != "hoat_dong":
        raise InactiveAccountException()
    if not {"quan_tri_vien", "quan_ly", "nhan_vien"}.intersection(user.roles):
        raise ForbiddenException()


# UC-02 Đăng xuất — A2: từ chối token có phiên bản mật khẩu cũ (specs/use_cases/identity_access/UC-02.md)
def _require_current_password(user: EmployeeCredentials, version: str) -> None:
    if (
        not isinstance(version, str)
        or not version.isascii()
        or not hmac.compare_digest(version, password_version(user.password_hash))
    ):
        raise UnauthorizedException(message="Please sign in again")


# UC-01 Đăng nhập — Main 5: hồ sơ và vai trò hiện tại (specs/use_cases/identity_access/UC-01.md)
# UC-02 Đăng xuất — A2: dùng hồ sơ và vai trò hiện tại khi xác minh phiên (specs/use_cases/identity_access/UC-02.md)
def _identity(user: EmployeeCredentials) -> AuthIdentity:
    return AuthIdentity(
        profile=NhanVienRead.model_validate(user),
        roles=user.roles,
        credential_version=password_version(user.password_hash),
        session_version=user.phien_ban_dang_nhap,
    )


# UC-03 Xem danh sách tài khoản — R4: QTV/chính chủ đủ hồ sơ, QLK không có tên đăng nhập (specs/use_cases/identity_access/UC-03.md)
def _employee_response(user: EmployeeRecord, actor: dict, *, detail: bool = False):
    full_profile = "quan_tri_vien" in actor["roles"] or (detail and user.id == int(actor["sub"]))
    schema = NhanVienRead if full_profile else NhanVienAssignmentRead
    values = {name: getattr(user, name) for name in schema.model_fields if name != "ma_vai_tro"}
    values["ma_vai_tro"] = user.ma_vai_tro
    return schema.model_validate(values)


# UC-03 Xem danh sách tài khoản — R4: ETag từ hồ sơ sau projection (specs/use_cases/identity_access/UC-03.md)
def _employee_etag(user: EmployeeRecord, actor: dict) -> str:
    profile = _employee_response(user, actor, detail=True)
    return f'"{sha256(profile.model_dump_json().encode("utf-8")).hexdigest()}"'


def _require_admin(actor: dict) -> None:
    if "quan_tri_vien" not in actor["roles"]:
        raise ForbiddenException(message="Chỉ quản trị viên được thực hiện thao tác này")


class NhanVienService:
    def __init__(
        self, repository: NhanVienRepository, audit: AuditService, transaction: Transaction
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction

    async def kiem_tra_nguoi_duoc_giao(self, employee_id: int, *, lock: bool) -> None:
        employee = (
            await self.repository.get_for_share(employee_id)
            if lock
            else await self.repository.get_by_id(employee_id)
        )
        if employee is None:
            raise NotFoundException(message="Nhân viên không tồn tại")
        if employee.trang_thai != "hoat_dong" or employee.ma_vai_tro != "nhan_vien":
            raise InvalidAssignee()

    # UC-01 Đăng nhập — Main 3–4; A2, A3 (specs/use_cases/identity_access/UC-01.md)
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

    # UC-01 Đăng nhập — Main 5; R4, A4 (specs/use_cases/identity_access/UC-01.md)
    async def record_login(self, employee_id: int) -> None:
        try:
            async with self.transaction:
                await self.audit.append(
                    CreationAudit(
                        nhan_vien_id=employee_id,
                        loai_doi_tuong="nhan_vien",
                        doi_tuong_id=employee_id,
                        thao_tac="dang_nhap",
                        du_lieu_truoc=None,
                        du_lieu_sau=None,
                        ly_do=None,
                    )
                )
        except ConflictException as error:
            # The shared transaction maps integrity errors to 409; login audit failures are 500.
            raise RuntimeError("Không ghi được lịch sử đăng nhập") from error

    # UC-02 Đăng xuất — A2: kiểm tra tài khoản khóa và phiên bản mật khẩu (specs/use_cases/identity_access/UC-02.md)
    # UC-06 Mở khóa tài khoản — A3: từ chối phiên có từ trước khi khóa (specs/use_cases/identity_access/UC-06.md)
    async def get_auth_identity(
        self, employee_id: int, *, credential_version: str, session_version: int = 0
    ) -> AuthIdentity:
        if not 1 <= employee_id <= MAX_EMPLOYEE_ID:
            raise UnauthorizedException(message="Invalid token subject")
        user = await self.repository.get_credentials_by_id(employee_id)
        if user is None:
            raise UnauthorizedException(message="Employee no longer exists")
        _require_active(user)
        _require_current_password(user, credential_version)
        if type(session_version) is not int or session_version != user.phien_ban_dang_nhap:
            raise UnauthorizedException(message="Please sign in again")
        return _identity(user)

    # UC-03 Xem danh sách tài khoản — Main 2–4; R1, A1–A3 (specs/use_cases/identity_access/UC-03.md)
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

    # UC-03 Xem danh sách tài khoản — R4: quyền đọc chi tiết (specs/use_cases/identity_access/UC-03.md)
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
        return self._result(user, actor, request_id)

    # UC-03 Xem danh sách tài khoản — R4: trả hồ sơ chi tiết và ETag (specs/use_cases/identity_access/UC-03.md)
    @staticmethod
    def _result(
        user: EmployeeRecord, actor: dict, request_id: str
    ) -> tuple[NhanVienDetailResponse, str]:
        return (
            NhanVienDetailResponse(
                data=_employee_response(user, actor, detail=True),
                meta=ResponseMeta(request_id=request_id),
            ),
            _employee_etag(user, actor),
        )

    # UC-04 Thêm tài khoản — Main 4–5; A6: khóa và làm mới quyền QTV (specs/use_cases/identity_access/UC-04.md)
    async def _lock_admin(self, actor: dict) -> dict:
        _require_admin(actor)
        # Lock this actor's row to serialize their writes and refresh credentials
        # after waiting. Employee codes come from the database identity trigger.
        current = await self.repository.lock_credentials_by_id(int(actor["sub"]))
        if current is None:
            raise UnauthorizedException(message="Employee no longer exists")
        _require_active(current)
        _require_current_password(current, actor.get("pwdv"))
        refreshed = {**actor, "roles": current.roles}
        _require_admin(refreshed)
        return refreshed

    async def _target(self, employee_id: int, actor: dict, if_match: str | None) -> EmployeeRecord:
        employee = await self.repository.get_for_update(employee_id)
        if employee is None:
            raise NotFoundException(message="Không tìm thấy nhân viên")
        if if_match is None:
            raise PreconditionRequiredException()
        if if_match != _employee_etag(employee, actor):
            raise PreconditionFailedException()
        return employee

    async def _role(self, role_id: int) -> VaiTroRead:
        role = await self.repository.get_role(role_id)
        if role is None:
            raise NotFoundException(message="Không tìm thấy vai trò")
        return role

    # UC-04 Thêm tài khoản — Main 6; R5: ghi lịch sử cùng transaction tạo (specs/use_cases/identity_access/UC-04.md)
    # UC-05 Khóa tài khoản — Main 6; R6: ghi người thực hiện, lý do và trạng thái trước/sau (specs/use_cases/identity_access/UC-05.md)
    # UC-07 Đổi vai trò — Main 6; R6: ghi một lịch sử với hồ sơ và lý do trước/sau (specs/use_cases/identity_access/UC-07.md)
    async def _audit(
        self,
        actor: dict,
        employee: EmployeeRecord,
        action: str,
        *,
        before: EmployeeRecord | None = None,
        reason: str | None = None,
        status_before: str | None = None,
        status_after: str | None = None,
    ) -> None:
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong="nhan_vien",
                doi_tuong_id=employee.id,
                thao_tac=action,
                du_lieu_sau=_employee_response(employee, actor, detail=True).model_dump(
                    mode="json"
                ),
                du_lieu_truoc=_employee_response(before, actor, detail=True).model_dump(mode="json")
                if before is not None
                else None,
                ly_do=reason,
                trang_thai_truoc=status_before,
                trang_thai_sau=status_after,
            )
        )

    # UC-04 Thêm tài khoản — Main 4–6; R6: DB cấp mã từ id khi tạo, ghi lịch sử cùng transaction (specs/use_cases/identity_access/UC-04.md)
    async def create_employee(
        self, params: NhanVienCreate, actor: dict, request_id: str
    ) -> tuple[NhanVienDetailResponse, str]:
        _require_admin(actor)
        password_hash = await asyncio.to_thread(
            get_password_hash, params.mat_khau.get_secret_value()
        )
        profile = params.model_dump(exclude={"ten_dang_nhap", "vai_tro_id", "ly_do"})
        async with self.transaction:
            actor = await self._lock_admin(actor)
            await self._role(params.vai_tro_id)
            if await self.repository.find_by_username(params.ten_dang_nhap) is not None:
                raise DuplicateUsernameException()
            employee = await self.repository.create(
                NewEmployee(
                    params.ten_dang_nhap,
                    params.vai_tro_id,
                    password_hash,
                    profile,
                )
            )
            await self._audit(actor, employee, "tao", reason=params.ly_do)
        return self._result(employee, actor, request_id)

    async def patch_employee(
        self,
        employee_id: int,
        params: NhanVienPatch,
        actor: dict,
        if_match: str | None,
        request_id: str,
    ) -> tuple[NhanVienDetailResponse, str]:
        _require_admin(actor)
        async with self.transaction:
            actor = await self._lock_admin(actor)
            before = await self._target(employee_id, actor, if_match)
            changes = {
                key: value
                for key, value in params.model_dump(exclude_unset=True).items()
                if getattr(before, key) != value
            }
            employee = before
            if changes:
                employee = await self.repository.update_profile(employee_id, changes)
                await self._audit(actor, employee, "sua", before=before)
        return self._result(employee, actor, request_id)

    # UC-08 Đổi mật khẩu tài khoản — Main 4–6; A2, A6: QTV đổi mật khẩu và ghi audit cùng transaction (specs/use_cases/identity_access/UC-08.md)
    async def reset_password(
        self,
        employee_id: int,
        new_password: str,
        actor: dict,
        if_match: str | None,
        request_id: str,
    ) -> tuple[NhanVienDetailResponse, str]:
        _require_admin(actor)
        new_hash = await asyncio.to_thread(get_password_hash, new_password)
        async with self.transaction:
            actor = await self._lock_admin(actor)
            employee = await self._target(employee_id, actor, if_match)
            await self.repository.set_password_hash(employee.id, new_hash)
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=int(actor["sub"]),
                    loai_doi_tuong="nhan_vien",
                    doi_tuong_id=employee.id,
                    thao_tac="doi_mat_khau",
                    du_lieu_truoc=None,
                    du_lieu_sau={"da_doi_mat_khau": True},
                    ly_do=None,
                )
            )
        return self._result(employee, actor, request_id)

    # UC-07 Đổi vai trò — Main 4–6; R3–R8, A2–A6, A9: kiểm tra và lưu cùng transaction (specs/use_cases/identity_access/UC-07.md)
    async def change_role(
        self,
        employee_id: int,
        role_id: int,
        actor: dict,
        if_match: str | None,
        request_id: str,
        reason: str | None = None,
    ) -> tuple[NhanVienDetailResponse, str]:
        _require_admin(actor)
        async with self.transaction:
            await self.repository.lock_admin_role()
            actor = await self._lock_admin(actor)
            before = await self._target(employee_id, actor, if_match)
            role = await self._role(role_id)
            if before.vai_tro_id == role_id:
                raise InvalidWorkflowState(message="Vai trò mới trùng vai trò hiện tại")
            if (
                before.ma_vai_tro == "quan_tri_vien"
                and before.trang_thai == "hoat_dong"
                and role.ma_vai_tro != "quan_tri_vien"
                and await self.repository.count_active_admins() <= 1
            ):
                raise LastActiveAdminException(
                    message="Không hạ quyền được Quản trị viên đang hoạt động cuối cùng"
                )
            if (
                before.ma_vai_tro == "nhan_vien"
                and await self.repository.count_unfinished_assigned_requests(employee_id) > 0
            ):
                raise UnfinishedAssignmentException()
            employee = await self.repository.set_role(employee_id, role_id)
            await self._audit(actor, employee, "doi_vai_tro", before=before, reason=reason)
        return self._result(employee, actor, request_id)

    # UC-05 Khóa tài khoản — Main 4–6; A2–A4, A9: kiểm tra QTV cuối và lưu atomic (specs/use_cases/identity_access/UC-05.md)
    # UC-06 Mở khóa tài khoản — Main 4–6; A2, A6: kiểm tra trạng thái, lưu và audit cùng transaction (specs/use_cases/identity_access/UC-06.md)
    async def _change_status(
        self,
        employee_id: int,
        actor: dict,
        if_match: str | None,
        reason: str | None,
        request_id: str,
        *,
        status: str,
        action: str,
    ) -> tuple[NhanVienDetailResponse, str]:
        _require_admin(actor)
        async with self.transaction:
            if status == "bi_khoa":
                await self.repository.lock_admin_role()
            actor = await self._lock_admin(actor)
            before = await self._target(employee_id, actor, if_match)
            if before.trang_thai == status:
                raise InvalidWorkflowState(message="Tài khoản không ở trạng thái phù hợp")
            if (
                status == "bi_khoa"
                and before.ma_vai_tro == "quan_tri_vien"
                and await self.repository.count_active_admins() <= 1
            ):
                raise LastActiveAdminException()
            employee = await self.repository.set_status(employee_id, status)
            await self._audit(
                actor,
                employee,
                action,
                before=before,
                reason=reason,
                status_before=before.trang_thai,
                status_after=employee.trang_thai,
            )
        return self._result(employee, actor, request_id)

    # UC-05 Khóa tài khoản — Main 5–6; A1: khóa thay xóa, lý do tùy chọn (specs/use_cases/identity_access/UC-05.md)
    async def soft_delete_employee(
        self,
        employee_id: int,
        actor: dict,
        if_match: str | None,
        reason: str | None,
        request_id: str,
    ) -> tuple[NhanVienDetailResponse, str]:
        return await self._change_status(
            employee_id,
            actor,
            if_match,
            reason,
            request_id,
            status="bi_khoa",
            action="khoa",
        )

    # UC-06 Mở khóa tài khoản — Main 5–6; A1: hoạt động lại, giữ vai trò và ghi mo_khoa (specs/use_cases/identity_access/UC-06.md)
    async def unlock_employee(
        self,
        employee_id: int,
        actor: dict,
        if_match: str | None,
        reason: str | None,
        request_id: str,
    ) -> tuple[NhanVienDetailResponse, str]:
        return await self._change_status(
            employee_id,
            actor,
            if_match,
            reason,
            request_id,
            status="hoat_dong",
            action="mo_khoa",
        )

    async def list_roles(
        self, params: VaiTroListQuery, actor: dict, request_id: str
    ) -> VaiTroListResponse:
        if not {"quan_tri_vien", "quan_ly"}.intersection(actor["roles"]):
            raise ForbiddenException()
        result = await self.repository.list_roles(params)
        return VaiTroListResponse(
            data=list(result.items),
            meta=ListResponseMeta(
                request_id=request_id,
                page=params.page,
                page_size=params.page_size,
                total=result.total,
                total_pages=ceil(result.total / params.page_size),
            ),
        )
