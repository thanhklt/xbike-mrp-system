"""Production requests (v4)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

YeuCauStatus = Literal[
    "nhap", "da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien", "hoan_thanh", "da_huy"
]
YeuCauSort = Literal[
    "id", "-id", "created_at", "-created_at", "ma_yeu_cau_san_xuat", "-ma_yeu_cau_san_xuat",
    "han_hoan_thanh", "-han_hoan_thanh",
]
LoaiYeuCau = Literal["xuat_giao", "nhap_kho"]


class YeuCauCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loai_yeu_cau: LoaiYeuCau = "xuat_giao"
    han_hoan_thanh: date
    mat_hang_id: int = Field(gt=0, strict=True)
    so_luong: int = Field(gt=0, le=2**31 - 1, strict=True)
    nhan_vien_duoc_giao_id: int = Field(gt=0, strict=True)


class YeuCauPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loai_yeu_cau: LoaiYeuCau
    han_hoan_thanh: date
    mat_hang_id: int = Field(gt=0, strict=True)
    so_luong: int = Field(gt=0, le=2**31 - 1, strict=True)
    nhan_vien_duoc_giao_id: int = Field(gt=0, strict=True)


class GuiYeuCauInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LyDoInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ly_do: str = Field(min_length=1)


class HangTraLine(BaseModel):
    id: int
    mat_hang_id: int
    ma_mat_hang: str
    ten_mat_hang: str
    don_vi_tinh: str
    loai_giu: Literal["thanh_pham_co_san", "linh_kien", "thanh_pham_san_xuat"]
    so_luong: int


class PhieuXuatHuyLine(BaseModel):
    id: int
    ma_phieu_xuat: str
    loai_phieu: Literal["xuat_linh_kien", "xuat_thanh_pham"]
    trang_thai: Literal["nhap", "cho_duyet"]
    xu_ly: Literal["bo", "tu_choi"]


class HuyPreview(BaseModel):
    duoc_huy: bool
    ly_do_khong_huy: str | None
    hang_tra: list[HangTraLine]
    phieu_xuat: list[PhieuXuatHuyLine]


class YeuCauListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = None
    mat_hang_id: int | None = Field(default=None, gt=0)
    trang_thai: YeuCauStatus | None = None
    loai_yeu_cau: LoaiYeuCau | None = None
    nhan_vien_duoc_giao_id: int | None = Field(default=None, gt=0)
    tu_ngay: date | None = None
    den_ngay: date | None = None
    sort: YeuCauSort | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.tu_ngay and self.den_ngay and self.tu_ngay > self.den_ngay:
            raise ValueError("tu_ngay phải nhỏ hơn hoặc bằng den_ngay")
        return self


class YeuCauRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_yeu_cau_san_xuat: str
    loai_yeu_cau: LoaiYeuCau
    han_hoan_thanh: date
    mat_hang_id: int
    so_luong: int
    nhan_vien_id: int
    nhan_vien_duoc_giao_id: int
    trang_thai: YeuCauStatus
    created_at: datetime
    completed_at: datetime | None
    bom_id: int | None
    so_luong_dung_thanh_pham: int | None
    so_luong_can_san_xuat: int | None
    updated_at: datetime
    gui_at: datetime | None
    kiem_tra_lan_dau_at: datetime | None
    started_at: datetime | None
    huy_at: datetime | None
    nguoi_huy_id: int | None
    ly_do_huy: str | None
    phien_ban: int


class ResponseMeta(BaseModel):
    request_id: str


class ChungTuCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    yeu_cau_san_xuat_id: int = Field(gt=0, strict=True)


class GuiChungTuInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChungTuRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_phieu: str
    yeu_cau_san_xuat_id: int
    so_luong_hoan_thanh: int
    nhan_vien_id: int
    trang_thai: Literal["nhap", "cho_duyet", "da_duyet", "tu_choi"]
    finish_time: datetime | None
    created_at: datetime
    updated_at: datetime
    nguoi_xu_ly_id: int | None
    xu_ly_at: datetime | None
    ly_do_tu_choi: str | None
    phien_ban: int


class ChungTuDetailResponse(BaseModel):
    data: ChungTuRead | None
    meta: ResponseMeta


class ChungTuListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    mat_hang_id: int | None = Field(default=None, gt=0)
    nhan_vien_id: int | None = Field(default=None, gt=0)
    trang_thai: Literal["cho_duyet", "da_duyet", "tu_choi"] | None = None
    loai_yeu_cau: LoaiYeuCau | None = None
    tu_ngay: date | None = None
    den_ngay: date | None = None

    @field_validator("*", mode="before")
    @classmethod
    def strip_query_strings(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.tu_ngay and self.den_ngay and self.tu_ngay > self.den_ngay:
            raise ValueError("tu_ngay phải nhỏ hơn hoặc bằng den_ngay")
        return self


class ChungTuListItem(ChungTuRead):
    ma_yeu_cau_san_xuat: str
    mat_hang_id: int
    loai_yeu_cau: LoaiYeuCau


class HuyPreviewResponse(BaseModel):
    data: HuyPreview
    meta: ResponseMeta


class ListResponseMeta(ResponseMeta):
    page: int
    page_size: int
    total: int
    total_pages: int


class ChungTuListResponse(BaseModel):
    data: list[ChungTuListItem]
    meta: ListResponseMeta


class YeuCauDetailResponse(BaseModel):
    data: YeuCauRead
    meta: ResponseMeta


class YeuCauListResponse(BaseModel):
    data: list[YeuCauRead]
    meta: ListResponseMeta


GuiYeuCauResponse = YeuCauDetailResponse


class KiemTraInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KiemTraLine(BaseModel):
    mat_hang_id: int
    ma_mat_hang: str
    ten_mat_hang: str
    don_vi_tinh: str
    so_luong_can: int
    so_luong_con_dung: int
    so_luong_thieu: int


class KiemTraKetQua(BaseModel):
    lan_dau: bool
    so_luong: int
    so_luong_dung_thanh_pham: int
    so_luong_can_san_xuat: int
    du_linh_kien: bool
    trang_thai_du_kien: YeuCauStatus
    linh_kien: list[KiemTraLine]
    giu_thanh_pham: int


class KiemTraPreviewResponse(BaseModel):
    data: KiemTraKetQua
    meta: ResponseMeta


class KiemTraData(BaseModel):
    yeu_cau: YeuCauRead
    ket_qua: KiemTraKetQua


class KiemTraResponse(BaseModel):
    data: KiemTraData
    meta: ResponseMeta


class NhuCauThieuLine(KiemTraLine):
    """Linh kiện hiện còn thiếu của một yêu cầu đang chờ."""


class YeuCauChoBoSung(BaseModel):
    id: int
    ma_yeu_cau_san_xuat: str
    mat_hang_id: int
    loai_yeu_cau: LoaiYeuCau
    so_luong_can_san_xuat: int
    han_hoan_thanh: date
    nhan_vien_duoc_giao_id: int
    kiem_tra_lan_dau_at: datetime
    linh_kien_thieu: list[NhuCauThieuLine]
    da_du: bool


class TongHopLinhKien(BaseModel):
    mat_hang_id: int
    ma_mat_hang: str
    ten_mat_hang: str
    don_vi_tinh: str
    tong_can: int
    so_luong_con_dung: int
    so_luong_thieu: int
    so_yeu_cau: int


class NhuCauBoSungData(BaseModel):
    yeu_cau: list[YeuCauChoBoSung]
    tong_hop: list[TongHopLinhKien]


class NhuCauBoSungResponse(BaseModel):
    data: NhuCauBoSungData
    meta: ResponseMeta


class SanXuatError(BaseModel):
    code: str
    message: str
    details: list[dict[str, str]]


class SanXuatErrorResponse(BaseModel):
    error: SanXuatError
    meta: ResponseMeta
