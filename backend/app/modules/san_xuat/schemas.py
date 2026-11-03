"""Production request and frozen planning representations (contract v3 §8)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

YeuCauStatus = Literal[
    "nhap", "da_gui", "cho_bo_sung_vat_tu", "dang_thuc_hien", "hoan_thanh", "da_huy"
]
YeuCauSort = Literal[
    "id", "-id", "created_at", "-created_at", "ma_yeu_cau_san_xuat", "-ma_yeu_cau_san_xuat"
]


class YeuCauCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_hang_id: int = Field(gt=0, strict=True)
    so_luong: int = Field(gt=0, le=2**31 - 1, strict=True)
    nhan_vien_duoc_giao_id: int | None = Field(default=None, gt=0, strict=True)


class YeuCauPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_hang_id: int | None = Field(default=None, gt=0, strict=True)
    so_luong: int | None = Field(default=None, gt=0, le=2**31 - 1, strict=True)
    nhan_vien_duoc_giao_id: int | None = Field(default=None, gt=0, strict=True)

    @model_validator(mode="after")
    def validate_patch(self):
        if not self.model_fields_set:
            raise ValueError("Cần ít nhất một trường cập nhật")
        for name in ("mat_hang_id", "so_luong"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} không nhận null")
        return self


class TinhKeHoachInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GuiYeuCauInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ke_hoach_token: str = Field(min_length=1)


class LyDoInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ly_do: str = Field(min_length=1)


class YeuCauListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = None
    mat_hang_id: int | None = Field(default=None, gt=0)
    trang_thai: YeuCauStatus | None = None
    nhan_vien_duoc_giao_id: int | None = Field(default=None, gt=0)
    tu_ngay: date | None = None
    den_ngay: date | None = None
    sort: YeuCauSort = "-created_at"

    @model_validator(mode="after")
    def validate_dates(self):
        if self.tu_ngay and self.den_ngay and self.tu_ngay > self.den_ngay:
            raise ValueError("tu_ngay phải nhỏ hơn hoặc bằng den_ngay")
        return self


class YeuCauRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_yeu_cau_san_xuat: str
    mat_hang_id: int
    so_luong: int
    nhan_vien_id: int
    nhan_vien_duoc_giao_id: int | None
    trang_thai: YeuCauStatus
    created_at: datetime
    completed_at: datetime | None
    so_luong_da_xuat: int = 0
    so_luong_con_phai_xuat: int = 0
    lenh_san_xuat_ids: list[int] = Field(default_factory=list)


class NhuCauDuKien(BaseModel):
    mat_hang_id: int
    so_luong_can: int


class LenhDuKien(BaseModel):
    ma_tam: str
    ma_cha_tam: str | None
    mat_hang_id: int
    bom_id: int | None
    so_luong: int
    nhu_cau_truc_tiep: list[NhuCauDuKien] = Field(default_factory=list)


class VatTuDuKien(BaseModel):
    mat_hang_id: int
    ma_mat_hang: str
    ten_mat_hang: str
    don_vi_tinh: str
    so_luong_can_tu_kho: int
    so_luong_hien_co: int
    so_luong_thieu: int


class KeHoachPreview(BaseModel):
    yeu_cau_san_xuat_id: int
    tinh_luc: datetime
    ke_hoach_token: str
    so_luong_yeu_cau: int
    ton_thanh_pham: int
    so_luong_can_san_xuat: int
    du_dieu_kien_gui: bool
    thieu_vat_tu: bool
    lenh_du_kien: list[LenhDuKien]
    vat_tu: list[VatTuDuKien]


class NhuCauRead(NhuCauDuKien):
    model_config = ConfigDict(from_attributes=True)
    id: int


class LenhRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_lenh_san_xuat: str
    yeu_cau_san_xuat_id: int
    lenh_san_xuat_cha_id: int | None
    mat_hang_id: int
    bom_id: int
    so_luong: int
    nhan_vien_id: int | None
    trang_thai: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    nhu_cau_truc_tiep: list[NhuCauRead] = Field(default_factory=list)
    so_luong_da_hoan_thanh: int = 0
    so_luong_con_phai_hoan_thanh: int = 0
    lenh_con_ids: list[int] = Field(default_factory=list)


class ChungTuRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_phieu: str
    lenh_san_xuat_id: int
    so_luong_hoan_thanh: int
    nhan_vien_id: int
    trang_thai: str
    finish_time: datetime | None
    created_at: datetime


class KeHoachRead(BaseModel):
    yeu_cau_san_xuat_id: int
    lenh: list[LenhRead]


class GuiYeuCauRead(BaseModel):
    yeu_cau: YeuCauRead
    ke_hoach: KeHoachRead


class ResponseMeta(BaseModel):
    request_id: str


class ListResponseMeta(ResponseMeta):
    page: int
    page_size: int
    total: int
    total_pages: int


class YeuCauDetailResponse(BaseModel):
    data: YeuCauRead
    meta: ResponseMeta


class YeuCauListResponse(BaseModel):
    data: list[YeuCauRead]
    meta: ListResponseMeta


class KeHoachPreviewResponse(BaseModel):
    data: KeHoachPreview
    meta: ResponseMeta


class KeHoachResponse(BaseModel):
    data: KeHoachRead
    meta: ResponseMeta


class GuiYeuCauResponse(BaseModel):
    data: GuiYeuCauRead
    meta: ResponseMeta


class SanXuatError(BaseModel):
    code: str
    message: str
    details: list[dict[str, str]]


class SanXuatErrorResponse(BaseModel):
    error: SanXuatError
    meta: ResponseMeta
