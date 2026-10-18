"""Employee lookup, permissions, projections and contract v2 responses."""

from hashlib import sha256
from math import ceil

from app.core.errors import ForbiddenException, NotFoundException
from app.modules.users.ports import UserRepository
from app.modules.users.schemas import (
    MAX_EMPLOYEE_ID,
    EmployeeRecord,
    ListResponseMeta,
    NhanVienAssignmentRead,
    NhanVienDetailResponse,
    NhanVienListQuery,
    NhanVienListResponse,
    NhanVienRead,
    ResponseMeta,
)


def _employee_response(user: EmployeeRecord, actor: dict, *, detail: bool = False):
    full_profile = "quan_tri_vien" in actor["roles"] or (detail and user.id == int(actor["sub"]))
    schema = NhanVienRead if full_profile else NhanVienAssignmentRead
    values = {name: getattr(user, name) for name in schema.model_fields if name != "ma_vai_tro"}
    values["ma_vai_tro"] = user.ma_vai_tro
    return schema.model_validate(values)


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

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
