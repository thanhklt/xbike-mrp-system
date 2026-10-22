"""Account mutations enforce current permissions and write audit atomically."""

import asyncio
from collections.abc import Callable

from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.nhan_vien.dto import EmployeeData, NewEmployee
from app.modules.nhan_vien.errors import EmployeeError
from app.modules.nhan_vien.ports import EmployeeWriteRepository
from app.modules.nhan_vien.schemas import ChiTietNhanVienResponse, ResponseMeta
from app.modules.nhan_vien.service import _employee_response, employee_etag

SELF_FIELDS = frozenset({"ho_ten", "ngay_sinh", "so_dien_thoai", "email"})
ADMIN_FIELDS = SELF_FIELDS | {"ngay_vao_lam", "he_so_luong"}


class EmployeeWriter:
    def __init__(
        self,
        repository: EmployeeWriteRepository,
        audit: AuditWriter,
        transaction: Transaction,
        hash_password: Callable[[str], str],
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction
        self.hash_password = hash_password

    async def _actor(self, actor: dict) -> dict:
        # Authentication's snapshot may predate waiting for another account mutation.
        await self.repository.lock_writes()
        current = await self.repository.get_for_update(int(actor["sub"]))
        if current is None or current.trang_thai != "hoat_dong":
            raise EmployeeError("tai_khoan_bi_vo_hieu_hoa", "Tài khoản không còn hoạt động.", 403)
        return {"sub": str(current.id), "roles": [current.ma_vai_tro] if current.ma_vai_tro else []}

    @staticmethod
    def _admin(actor: dict) -> None:
        if "quan_tri_vien" not in actor["roles"]:
            raise EmployeeError(
                "khong_co_quyen", "Chỉ quản trị viên được thực hiện thao tác này.", 403
            )

    async def _target(self, employee_id: int, actor: dict, if_match: str | None) -> EmployeeData:
        employee = await self.repository.get_for_update(employee_id)
        if employee is None:
            raise EmployeeError("khong_tim_thay", "Không tìm thấy nhân viên.", 404)
        if if_match is None:
            raise EmployeeError("thieu_if_match", "Thiếu header If-Match.", 428)
        # Only exact strong validators from GET are accepted; wildcard is not a version.
        if if_match != employee_etag(employee, actor):
            raise EmployeeError("du_lieu_da_thay_doi", "Dữ liệu đã thay đổi; hãy tải lại.", 412)
        return employee

    async def _role(self, role_id: int) -> None:
        role = await self.repository.get_role(role_id)
        if role is None:
            raise EmployeeError("khong_tim_thay", "Không tìm thấy vai trò.", 404)
        if role.ma_vai_tro not in {"quan_tri_vien", "quan_ly", "nhan_vien"}:
            raise EmployeeError("du_lieu_khong_hop_le", "Vai trò không hợp lệ.", 422)

    async def _preserve_admin(self, employee: EmployeeData) -> None:
        if (
            employee.trang_thai == "hoat_dong"
            and employee.ma_vai_tro == "quan_tri_vien"
            and await self.repository.active_admin_count() <= 1
        ):
            raise EmployeeError(
                "quan_tri_vien_cuoi_cung", "Phải giữ ít nhất một quản trị viên hoạt động.", 409
            )

    @staticmethod
    def _result(
        employee: EmployeeData, actor: dict, request_id: str
    ) -> tuple[ChiTietNhanVienResponse, str]:
        return (
            ChiTietNhanVienResponse(
                data=_employee_response(employee, actor, detail=True),
                meta=ResponseMeta(request_id=request_id),
            ),
            employee_etag(employee, actor),
        )

    async def _audit(
        self,
        actor: dict,
        employee: EmployeeData,
        action: str,
        before: EmployeeData | None = None,
        reason: str | None = None,
    ) -> None:
        admin = {"sub": actor["sub"], "roles": ["quan_tri_vien"]}
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong="nhan_vien",
                doi_tuong_id=employee.id,
                thao_tac=action,
                du_lieu_sau=_employee_response(employee, admin).model_dump(
                    mode="json", exclude_unset=True
                ),
                du_lieu_truoc=_employee_response(before, admin).model_dump(
                    mode="json", exclude_unset=True
                )
                if before
                else None,
                ly_do=reason,
            )
        )

    async def create(
        self,
        username: str,
        code: str,
        role_id: int,
        password: str,
        profile: dict[str, object],
        actor: dict,
        request_id: str,
    ) -> tuple[ChiTietNhanVienResponse, str]:
        self._admin(actor)
        password_hash = await asyncio.to_thread(self.hash_password, password)
        async with self.transaction:
            actor = await self._actor(actor)
            self._admin(actor)
            await self._role(role_id)
            employee = await self.repository.create(
                NewEmployee(username, code, role_id, password_hash, profile)
            )
            await self._audit(actor, employee, "tao")
        return self._result(employee, actor, request_id)

    async def patch(
        self,
        employee_id: int,
        changes: dict[str, object],
        actor: dict,
        if_match: str | None,
        request_id: str,
    ) -> tuple[ChiTietNhanVienResponse, str]:
        async with self.transaction:
            actor = await self._actor(actor)
            admin = "quan_tri_vien" in actor["roles"]
            if not admin and int(actor["sub"]) != employee_id:
                raise EmployeeError("khong_co_quyen", "Chỉ được sửa hồ sơ của chính mình.", 403)
            allowed = ADMIN_FIELDS if admin else SELF_FIELDS
            if not changes.keys() <= allowed:
                raise EmployeeError("khong_co_quyen", "Có trường không được phép sửa.", 403)
            before = await self._target(employee_id, actor, if_match)
            employee = await self.repository.update_profile(employee_id, changes)
            if changes:
                await self._audit(actor, employee, "sua", before)
        return self._result(employee, actor, request_id)

    async def change_role(
        self, employee_id: int, role_id: int, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[ChiTietNhanVienResponse, str]:
        self._admin(actor)
        async with self.transaction:
            actor = await self._actor(actor)
            self._admin(actor)
            before = await self._target(employee_id, actor, if_match)
            await self._role(role_id)
            if before.vai_tro_id != role_id:
                await self._preserve_admin(before)
                employee = await self.repository.set_role(employee_id, role_id)
                if before.vai_tro_id is not None:
                    await self._audit(actor, employee, "thu_hoi_quyen", before)
                await self._audit(actor, employee, "cap_quyen", before)
            else:
                employee = before
        return self._result(employee, actor, request_id)

    async def _block(
        self,
        employee_id: int,
        actor: dict,
        if_match: str | None,
        reason: str | None,
        *,
        allow_blocked: bool,
    ) -> tuple[EmployeeData, dict]:
        self._admin(actor)
        actor = await self._actor(actor)
        self._admin(actor)
        before = await self._target(employee_id, actor, if_match)
        if int(actor["sub"]) == employee_id:
            raise EmployeeError("khong_the_tu_khoa", "Không được tự khóa tài khoản đang dùng.", 409)
        if before.trang_thai == "bi_khoa" and allow_blocked:
            return before, actor
        if before.trang_thai != "hoat_dong":
            raise EmployeeError(
                "trang_thai_khong_hop_le", "Tài khoản không ở trạng thái hoạt động.", 409
            )
        await self._preserve_admin(before)
        employee = await self.repository.set_status(employee_id, "bi_khoa")
        await self._audit(actor, employee, "vo_hieu_hoa", before, reason)
        return employee, actor

    async def soft_delete(self, employee_id: int, actor: dict, if_match: str | None) -> None:
        async with self.transaction:
            await self._block(employee_id, actor, if_match, None, allow_blocked=True)

    async def disable(
        self, employee_id: int, reason: str, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[ChiTietNhanVienResponse, str]:
        async with self.transaction:
            employee, actor = await self._block(
                employee_id, actor, if_match, reason, allow_blocked=False
            )
        return self._result(employee, actor, request_id)
