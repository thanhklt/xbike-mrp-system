"""Employee lookup, permissions, projections and contract v2 responses."""

from hashlib import sha256
from math import ceil

from app.core.errors import ForbiddenException, NotFoundException
from app.modules.nhan_vien.dto import EmployeeData, EmployeeListQuery
from app.modules.nhan_vien.ports import EmployeeRepository
from app.modules.nhan_vien.schemas import (
    ChiTietNhanVien,
    ChiTietNhanVienResponse,
    DanhSachNhanVienRequest,
    DanhSachNhanVienResponse,
    DanhSachVaiTroResponse,
    ListResponseMeta,
    ResponseMeta,
    VaiTroRead,
)

ASSIGNMENT_FIELDS = ("id", "ma_nhan_vien", "ho_ten", "vai_tro_id", "trang_thai")
PROFILE_FIELDS = (
    "ten_dang_nhap",
    "ngay_sinh",
    "so_dien_thoai",
    "email",
    "ngay_vao_lam",
    "he_so_luong",
)


def _employee_response(
    employee: EmployeeData, actor: dict, *, detail: bool = False
) -> ChiTietNhanVien:
    full_profile = "quan_tri_vien" in actor["roles"] or (
        detail and employee.id == int(actor["sub"])
    )
    fields = ASSIGNMENT_FIELDS + PROFILE_FIELDS if full_profile else ASSIGNMENT_FIELDS
    values = {name: getattr(employee, name) for name in fields}
    values["ma_vai_tro"] = employee.ma_vai_tro
    return ChiTietNhanVien.model_validate(values)


async def list_employees(
    repo: EmployeeRepository,
    params: DanhSachNhanVienRequest,
    actor: dict,
    request_id: str,
) -> DanhSachNhanVienResponse:
    if not {"quan_tri_vien", "quan_ly"}.intersection(actor["roles"]):
        raise ForbiddenException()
    employee_page = await repo.list(
        EmployeeListQuery(
            page=params.page,
            page_size=params.page_size,
            q=params.q,
            sort=params.sort,
            vai_tro_id=params.vai_tro_id,
            trang_thai=params.trang_thai,
        )
    )
    return DanhSachNhanVienResponse(
        data=[_employee_response(employee, actor) for employee in employee_page.items],
        meta=ListResponseMeta(
            request_id=request_id,
            page=params.page,
            page_size=params.page_size,
            total=employee_page.total,
            total_pages=ceil(employee_page.total / params.page_size),
        ),
    )


async def get_employee(
    repo: EmployeeRepository,
    employee_id: int,
    actor: dict,
    request_id: str,
) -> tuple[ChiTietNhanVienResponse, str]:
    employee = await repo.get_by_id(employee_id)
    if employee is None:
        raise NotFoundException(message=f"nhan_vien {employee_id} not found")
    if (
        not {"quan_tri_vien", "quan_ly"}.intersection(actor["roles"])
        and int(actor["sub"]) != employee_id
    ):
        raise ForbiddenException()
    profile = _employee_response(employee, actor, detail=True)
    etag = employee_etag(employee, actor)
    return ChiTietNhanVienResponse(data=profile, meta=ResponseMeta(request_id=request_id)), etag


def employee_etag(employee: EmployeeData, actor: dict) -> str:
    profile = _employee_response(employee, actor, detail=True)
    return f'"{sha256(profile.model_dump_json(exclude_unset=True).encode("utf-8")).hexdigest()}"'


async def list_roles(
    repo: EmployeeRepository,
    page: int,
    page_size: int,
    actor: dict,
    request_id: str,
) -> DanhSachVaiTroResponse:
    if not {"quan_tri_vien", "quan_ly"}.intersection(actor["roles"]):
        raise ForbiddenException()
    result = await repo.list_roles(page, page_size)
    return DanhSachVaiTroResponse(
        data=[
            VaiTroRead(id=r.id, ma_vai_tro=r.ma_vai_tro, ten_vai_tro=r.ten_vai_tro)
            for r in result.items
        ],
        meta=ListResponseMeta(
            request_id=request_id,
            page=page,
            page_size=page_size,
            total=result.total,
            total_pages=ceil(result.total / page_size),
        ),
    )
