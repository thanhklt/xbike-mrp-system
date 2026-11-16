"""Production request policy and atomic transitions (UC-23)."""

from datetime import datetime, timezone

from app.core.errors import (
    ForbiddenException,
    InvalidAssignee,
    InvalidInputException,
    InvalidWorkflowState,
    NotFoundException,
    PostedProductionDependency,
    PreconditionFailedException,
    PreconditionRequiredException,
)
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.mat_hang.ports import MatHangStockReader
from app.modules.mat_hang.service import InactiveMatHang
from app.modules.san_xuat.ports import (
    AssigneeReader,
    HangKhaDung,
    ProductionIssues,
    YeuCauSanXuatRepository,
)
from app.modules.san_xuat.schemas import (
    HuyPreview,
    HuyPreviewResponse,
    KiemTraData,
    KiemTraKetQua,
    KiemTraLine,
    KiemTraPreviewResponse,
    KiemTraResponse,
    ListResponseMeta,
    NhuCauBoSungData,
    NhuCauBoSungResponse,
    NhuCauThieuLine,
    PhieuXuatHuyLine,
    ResponseMeta,
    TongHopLinhKien,
    YeuCauChoBoSung,
    YeuCauCreate,
    YeuCauDetailResponse,
    YeuCauListQuery,
    YeuCauListResponse,
    YeuCauPatch,
    YeuCauRead,
)
from app.modules.san_xuat.service.common import canonical_hash


def generate_yeu_cau_etag(record: YeuCauRead) -> str:
    return f'"{canonical_hash(record.model_dump(mode="json"))}"'


def _verify_if_match(if_match: str | None, record: YeuCauRead) -> None:
    if not if_match or not if_match.strip():
        raise PreconditionRequiredException()
    if if_match.strip() != generate_yeu_cau_etag(record):
        raise PreconditionFailedException()


def _require_manager(actor: dict) -> None:
    if "quan_ly" not in actor.get("roles", []):
        raise ForbiddenException()


def _require_scope(record: YeuCauRead, actor: dict) -> None:
    if "quan_ly" in actor.get("roles", []):
        return
    if "nhan_vien" not in actor.get("roles", []) or record.nhan_vien_duoc_giao_id != int(
        actor["sub"]
    ):
        raise ForbiddenException()


def _require_draft(record: YeuCauRead) -> None:
    if record.trang_thai != "nhap":
        raise InvalidWorkflowState()


def _require_check_actor(actor: dict) -> None:
    roles = actor.get("roles", [])
    if "nhan_vien" not in roles or "quan_ly" in roles:
        raise ForbiddenException()


def _require_check_state(record: YeuCauRead) -> None:
    if record.trang_thai not in {"da_gui", "cho_bo_sung_linh_kien"}:
        raise InvalidWorkflowState()


# UC-26 Kiểm tra yêu cầu sản xuất và giữ hàng — Main 3, 6; A1–A3, A7 tính theo còn dùng được (specs/use_cases/production/UC-26.md)
def tinh_ket_qua_kiem_tra(
    yeu_cau: YeuCauRead,
    dinh_muc_hoac_nhu_cau: dict[int, int],
    kha_dung: dict[int, HangKhaDung],
) -> KiemTraKetQua:
    lan_dau = yeu_cau.kiem_tra_lan_dau_at is None
    if lan_dau:
        dung = (
            min(kha_dung[yeu_cau.mat_hang_id].so_luong_con_dung, yeu_cau.so_luong)
            if yeu_cau.loai_yeu_cau == "xuat_giao" else 0
        )
        can_san_xuat = yeu_cau.so_luong - dung
        quantities = (
            {id_: n * can_san_xuat for id_, n in dinh_muc_hoac_nhu_cau.items()}
            if can_san_xuat else {}
        )
    else:
        dung = yeu_cau.so_luong_dung_thanh_pham
        can_san_xuat = yeu_cau.so_luong_can_san_xuat
        quantities = dinh_muc_hoac_nhu_cau
    lines = [
        KiemTraLine(
            mat_hang_id=id_,
            ma_mat_hang=kha_dung[id_].ma_mat_hang,
            ten_mat_hang=kha_dung[id_].ten_mat_hang,
            don_vi_tinh=kha_dung[id_].don_vi_tinh,
            so_luong_can=n,
            so_luong_con_dung=kha_dung[id_].so_luong_con_dung,
            so_luong_thieu=max(0, n - kha_dung[id_].so_luong_con_dung),
        )
        for id_, n in sorted(quantities.items())
    ]
    du = all(line.so_luong_thieu == 0 for line in lines)
    return KiemTraKetQua(
        lan_dau=lan_dau, so_luong=yeu_cau.so_luong, so_luong_dung_thanh_pham=dung,
        so_luong_can_san_xuat=can_san_xuat, du_linh_kien=du,
        trang_thai_du_kien="dang_thuc_hien" if du else "cho_bo_sung_linh_kien",
        linh_kien=lines, giu_thanh_pham=dung if lan_dau else 0,
    )


# UC-27 Xem nhu cầu bổ sung linh kiện — Main 2–3; D3–D4 tính thiếu riêng và tổng hợp (specs/use_cases/production/UC-27.md)
def tong_hop_nhu_cau_bo_sung(
    yeu_cau: list[YeuCauRead],
    nhu_cau: dict[int, dict[int, int]],
    kha_dung: dict[int, HangKhaDung],
) -> NhuCauBoSungData:
    requests = []
    totals: dict[int, TongHopLinhKien] = {}
    for record in yeu_cau:
        missing = []
        for item_id, quantity in sorted(nhu_cau.get(record.id, {}).items()):
            item = kha_dung[item_id]
            identity = {
                "mat_hang_id": item_id, "ma_mat_hang": item.ma_mat_hang,
                "ten_mat_hang": item.ten_mat_hang, "don_vi_tinh": item.don_vi_tinh,
                "so_luong_con_dung": item.so_luong_con_dung,
            }
            if quantity > item.so_luong_con_dung:
                missing.append(NhuCauThieuLine(
                    **identity, so_luong_can=quantity,
                    so_luong_thieu=quantity - item.so_luong_con_dung,
                ))
            if item_id not in totals:
                totals[item_id] = TongHopLinhKien(
                    **identity, tong_can=0, so_luong_thieu=0, so_yeu_cau=0,
                )
            total = totals[item_id]
            total.tong_can += quantity
            total.so_yeu_cau += 1
            total.so_luong_thieu = max(0, total.tong_can - total.so_luong_con_dung)
        requests.append(YeuCauChoBoSung(
            **record.model_dump(include={
                "id", "ma_yeu_cau_san_xuat", "mat_hang_id", "loai_yeu_cau",
                "so_luong_can_san_xuat", "han_hoan_thanh", "nhan_vien_duoc_giao_id",
                "kiem_tra_lan_dau_at",
            }),
            linh_kien_thieu=missing, da_du=not missing,
        ))
    return NhuCauBoSungData(
        yeu_cau=requests,
        tong_hop=sorted(totals.values(), key=lambda row: (-row.so_luong_thieu, row.ma_mat_hang)),
    )


class YeuCauSanXuatService:
    def __init__(
        self,
        repository: YeuCauSanXuatRepository,
        audit: AuditWriter,
        transaction: Transaction,
        items: MatHangStockReader,
        employees: AssigneeReader,
        issues: ProductionIssues,
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction
        self.items = items
        self.employees = employees
        self.issues = issues

    # UC-27 Xem nhu cầu bổ sung linh kiện — Main 1–3; A1 chỉ QLK, chỉ đọc không khóa (specs/use_cases/production/UC-27.md)
    async def xem_nhu_cau_bo_sung(self, actor: dict, request_id: str) -> NhuCauBoSungResponse:
        _require_manager(actor)
        requests = await self.repository.yeu_cau_cho_bo_sung()
        needs = (
            await self.repository.nhu_cau_cua_cac_yeu_cau([row.id for row in requests])
            if requests else {}
        )
        item_ids = sorted({item_id for quantities in needs.values() for item_id in quantities})
        available = await self.repository.kha_dung(item_ids, lock=False) if item_ids else {}
        return NhuCauBoSungResponse(
            data=tong_hop_nhu_cau_bo_sung(requests, needs, available),
            meta=ResponseMeta(request_id=request_id),
        )

    async def _check_result(self, record: YeuCauRead, *, lock: bool) -> KiemTraKetQua:
        quantities = (
            await self.repository.dinh_muc(record.bom_id)
            if record.kiem_tra_lan_dau_at is None
            else await self.repository.nhu_cau(record.id)
        )
        ids = sorted({record.mat_hang_id, *quantities})
        available = await self.repository.kha_dung(ids, lock=lock)
        if set(available) != set(ids) or not quantities:
            raise InvalidWorkflowState(message="Không đủ dữ liệu công thức hoặc nhu cầu đã chốt")
        return tinh_ket_qua_kiem_tra(record, quantities, available)

    # UC-26 Kiểm tra yêu cầu sản xuất và giữ hàng — Main 2–4; A5 chỉ đọc, không khóa (specs/use_cases/production/UC-26.md)
    async def xem_truoc_kiem_tra(
        self, resource_id: int, actor: dict, request_id: str,
    ) -> KiemTraPreviewResponse:
        _require_check_actor(actor)
        record = await self._require_request(resource_id, actor)
        _require_check_state(record)
        result = await self._check_result(record, lock=False)
        return KiemTraPreviewResponse(data=result, meta=ResponseMeta(request_id=request_id))

    # UC-26 Kiểm tra yêu cầu sản xuất và giữ hàng — Main 5–8; A1–A4, A6, A7 xác nhận và audit (specs/use_cases/production/UC-26.md)
    async def kiem_tra(
        self, resource_id: int, actor: dict, if_match: str | None, request_id: str,
    ) -> tuple[KiemTraResponse, str]:
        _require_check_actor(actor)
        async with self.transaction:
            before = await self._require_request(resource_id, actor, lock=True)
            _verify_if_match(if_match, before)
            _require_check_state(before)
            result = await self._check_result(before, lock=True)
            after = before
            if result.lan_dau or result.du_linh_kien:
                reservations = []
                changes = {"trang_thai": result.trang_thai_du_kien}
                if result.lan_dau:
                    changes.update(
                        so_luong_dung_thanh_pham=result.so_luong_dung_thanh_pham,
                        so_luong_can_san_xuat=result.so_luong_can_san_xuat,
                        kiem_tra_lan_dau_at=datetime.now(timezone.utc),
                    )
                    if result.linh_kien:
                        await self.repository.ghi_nhu_cau(
                            resource_id, {line.mat_hang_id: line.so_luong_can for line in result.linh_kien},
                        )
                    if result.giu_thanh_pham:
                        reservations.append({
                            "mat_hang_id": before.mat_hang_id,
                            "loai_giu": "thanh_pham_co_san",
                            "so_luong": result.giu_thanh_pham,
                        })
                if result.du_linh_kien:
                    reservations.extend({
                        "mat_hang_id": line.mat_hang_id,
                        "loai_giu": "linh_kien",
                        "so_luong": line.so_luong_can,
                    } for line in result.linh_kien)
                if reservations:
                    await self.repository.giu_hang(resource_id, reservations)
                after = await self.repository.update(resource_id, changes)
                await self.audit.append(
                    CreationAudit(
                        nhan_vien_id=int(actor["sub"]),
                        loai_doi_tuong="yeu_cau_san_xuat",
                        doi_tuong_id=resource_id,
                        thao_tac="kiem_tra",
                        trang_thai_truoc=before.trang_thai,
                        trang_thai_sau=after.trang_thai,
                        du_lieu_truoc=before.model_dump(mode="json"),
                        du_lieu_sau={
                            "lan_dau": result.lan_dau,
                            "so_luong_dung_thanh_pham": result.so_luong_dung_thanh_pham,
                            "so_luong_can_san_xuat": result.so_luong_can_san_xuat,
                            "giu_hang": reservations,
                            "thieu": [
                                line.model_dump() for line in result.linh_kien if line.so_luong_thieu
                            ],
                        },
                    )
                )
        return (
            KiemTraResponse(
                data=KiemTraData(yeu_cau=after, ket_qua=result),
                meta=ResponseMeta(request_id=request_id),
            ),
            generate_yeu_cau_etag(after),
        )

    async def _require_request(
        self, request_id: int, actor: dict, *, lock: bool = False
    ) -> YeuCauRead:
        if request_id > 2**31 - 1:
            raise NotFoundException()
        record = (
            await self.repository.get_for_update(request_id)
            if lock
            else await self.repository.get_by_id(request_id)
        )
        if record is None or ("quan_ly" not in actor.get("roles", []) and record.trang_thai == "nhap"):
            raise NotFoundException()
        _require_scope(record, actor)
        return record

    async def _audit(
        self,
        kind: str,
        action: str,
        actor: dict,
        before,
        after,
        *,
        reason: str | None = None,
        trang_thai_truoc: str | None = None,
        trang_thai_sau: str | None = None,
    ) -> None:
        record = after if after is not None else before
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong=kind,
                doi_tuong_id=record.id,
                thao_tac=action,
                du_lieu_truoc=before.model_dump(mode="json") if before else None,
                du_lieu_sau=after.model_dump(mode="json") if after else {},
                ly_do=reason,
                trang_thai_truoc=trang_thai_truoc,
                trang_thai_sau=trang_thai_sau,
            )
        )

    def _detail(self, record: YeuCauRead, request_id: str) -> tuple[YeuCauDetailResponse, str]:
        return (
            YeuCauDetailResponse(data=record, meta=ResponseMeta(request_id=request_id)),
            generate_yeu_cau_etag(record),
        )

    # UC-23 Lập và gửi yêu cầu sản xuất — A2; D5 (specs/use_cases/production/UC-23.md)
    # UC-25 Xem danh sách yêu cầu sản xuất — Main 2–3; A1, A3 (specs/use_cases/production/UC-25.md)
    async def list_entries(
        self, params: YeuCauListQuery, actor: dict, request_id: str
    ) -> YeuCauListResponse:
        if not {"quan_ly", "nhan_vien"}.intersection(actor.get("roles", [])):
            raise ForbiddenException()
        actor_id = None if "quan_ly" in actor["roles"] else int(actor["sub"])
        if params.sort is None:
            # Dev chốt 16/11/2026: mặc định mới nhất trước cho cả QLK và NV (UC-25 R2, AC-3).
            params = params.model_copy(update={"sort": "-created_at"})
        result = await self.repository.list_entries(params, actor_id)
        return YeuCauListResponse(
            data=result.items,
            meta=ListResponseMeta(
                request_id=request_id,
                page=params.page,
                page_size=params.page_size,
                total=result.total,
                total_pages=(result.total + params.page_size - 1) // params.page_size,
            ),
        )

    # UC-23 Lập và gửi yêu cầu sản xuất — A2; D5 (specs/use_cases/production/UC-23.md)
    # UC-25 Xem danh sách yêu cầu sản xuất — Main 4; A2 (specs/use_cases/production/UC-25.md)
    async def get_entry(
        self, resource_id: int, actor: dict, request_id: str
    ) -> tuple[YeuCauDetailResponse, str]:
        return self._detail(await self._require_request(resource_id, actor), request_id)

    async def _validate_product(self, item_id: int) -> None:
        records = await self.items.read_items([item_id], lock=True)
        if not records[0].is_active:
            raise InactiveMatHang()
        if records[0].loai_mat_hang != "thanh_pham":
            raise InvalidInputException(message="mat_hang_id phải là thành phẩm")

    # UC-23 Lập và gửi yêu cầu sản xuất — Main 4–6; A1 (specs/use_cases/production/UC-23.md)
    async def create_entry(
        self, payload: YeuCauCreate, actor: dict, request_id: str
    ) -> tuple[YeuCauDetailResponse, str]:
        _require_manager(actor)
        async with self.transaction:
            await self._validate_product(payload.mat_hang_id)
            await self.employees.kiem_tra_nguoi_duoc_giao(
                payload.nhan_vien_duoc_giao_id, lock=True
            )
            created = await self.repository.add(payload, int(actor["sub"]))
            await self._audit(
                "yeu_cau_san_xuat", "tao", actor, None, created,
                trang_thai_truoc=None,
                trang_thai_sau="nhap",
            )
        return self._detail(created, request_id)

    # UC-24 Sửa, xóa, gửi yêu cầu sản xuất nháp — A1; R2, R3, R9, R10 (specs/use_cases/production/UC-24.md)
    async def patch_entry(
        self,
        resource_id: int,
        payload: YeuCauPatch,
        actor: dict,
        if_match: str | None,
        request_id: str,
    ) -> tuple[YeuCauDetailResponse, str]:
        _require_manager(actor)
        async with self.transaction:
            before = await self._require_request(resource_id, actor, lock=True)
            _verify_if_match(if_match, before)
            _require_draft(before)
            changes = payload.model_dump()
            await self._validate_product(payload.mat_hang_id)
            await self.employees.kiem_tra_nguoi_duoc_giao(
                payload.nhan_vien_duoc_giao_id, lock=True
            )
            updated = await self.repository.update(resource_id, changes)
            await self._audit(
                "yeu_cau_san_xuat", "sua", actor, before, updated,
                trang_thai_truoc="nhap",
                trang_thai_sau="nhap",
            )
        return self._detail(updated, request_id)

    # UC-24 Sửa, xóa, gửi yêu cầu sản xuất nháp — A2; R4, R9, R10 (specs/use_cases/production/UC-24.md)
    async def delete_entry(self, resource_id: int, actor: dict, if_match: str | None) -> None:
        _require_manager(actor)
        async with self.transaction:
            before = await self._require_request(resource_id, actor, lock=True)
            _verify_if_match(if_match, before)
            _require_draft(before)
            await self.repository.delete(resource_id)
            await self._audit(
                "yeu_cau_san_xuat", "xoa_nhap", actor, before, None,
                trang_thai_truoc="nhap",
                trang_thai_sau=None,
            )

    # UC-23 Lập và gửi yêu cầu sản xuất — Main 7–9; A3 (specs/use_cases/production/UC-23.md)
    # UC-24 Sửa, xóa, gửi yêu cầu sản xuất nháp — Main 5–7; A4, A5 (specs/use_cases/production/UC-24.md)
    async def gui(
        self, resource_id: int, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[YeuCauDetailResponse, str]:
        _require_manager(actor)
        async with self.transaction:
            before = await self._require_request(resource_id, actor, lock=True)
            _verify_if_match(if_match, before)
            _require_draft(before)
            try:
                await self._validate_product(before.mat_hang_id)
            except InactiveMatHang as exc:
                raise InvalidWorkflowState(
                    message="Thành phẩm đã ngừng hoạt động, không thể gửi yêu cầu"
                ) from exc
            try:
                await self.employees.kiem_tra_nguoi_duoc_giao(
                    before.nhan_vien_duoc_giao_id, lock=True
                )
            except (NotFoundException, InvalidAssignee) as exc:
                raise InvalidAssignee(
                    message="Nhân viên được giao đã bị khóa hoặc không còn hợp lệ"
                ) from exc
            bom_id = await self.repository.bom_dang_dung(before.mat_hang_id)
            after = await self.repository.update(
                resource_id,
                {"trang_thai": "da_gui", "bom_id": bom_id, "gui_at": datetime.now(timezone.utc)},
            )
            await self._audit(
                "yeu_cau_san_xuat", "gui", actor, before, after,
                trang_thai_truoc="nhap",
                trang_thai_sau="da_gui",
            )
        return self._detail(after, request_id)

    # UC-28 Hủy yêu cầu sản xuất — D4 xem trước chỉ đọc, không khóa hoặc ghi lịch sử (specs/use_cases/production/UC-28.md)
    async def xem_truoc_huy(
        self, resource_id: int, actor: dict, request_id: str,
    ) -> HuyPreviewResponse:
        _require_manager(actor)
        record = await self._require_request(resource_id, actor)
        issues = await self.issues.phieu_cua_yeu_cau(resource_id)
        reason = None
        if record.trang_thai not in {"da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien"}:
            reason = "Chỉ hủy yêu cầu Đã gửi, Chờ bổ sung linh kiện hoặc Đang thực hiện."
        elif any(row["trang_thai"] == "da_duyet" for row in issues):
            reason = "Yêu cầu đã có phiếu xuất được duyệt, không thể hủy."
        return HuyPreviewResponse(
            data=HuyPreview(
                duoc_huy=reason is None, ly_do_khong_huy=reason,
                hang_tra=await self.repository.giu_hang_dang_giu(resource_id, lock=False),
                phieu_xuat=[
                    PhieuXuatHuyLine(**row, xu_ly="bo" if row["trang_thai"] == "nhap" else "tu_choi")
                    for row in issues if row["trang_thai"] in {"nhap", "cho_duyet"}
                ],
            ),
            meta=ResponseMeta(request_id=request_id),
        )

    # UC-28 Hủy yêu cầu sản xuất — Main 3, 6–7; D1–D3 hủy và trả giữ hàng nguyên tử (specs/use_cases/production/UC-28.md)
    async def huy(
        self, resource_id: int, reason: str, actor: dict, if_match: str | None, request_id: str,
    ) -> tuple[YeuCauDetailResponse, str]:
        _require_manager(actor)
        reason = reason.strip()
        if not reason:
            raise InvalidInputException(message="Lý do hủy không được để trống")
        async with self.transaction:
            before = await self._require_request(resource_id, actor, lock=True)
            _verify_if_match(if_match, before)
            if before.trang_thai not in {"da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien"}:
                raise InvalidWorkflowState()
            if await self.issues.co_phieu_da_ghi_so(resource_id):
                raise PostedProductionDependency()
            issues = await self.issues.phieu_cua_yeu_cau(resource_id)
            returned = await self.repository.tra_giu_hang(resource_id)
            await self.issues.huy_phieu_chua_ghi_so(resource_id, "Yêu cầu đã hủy", int(actor["sub"]))
            after = await self.repository.update(resource_id, {
                "trang_thai": "da_huy", "huy_at": datetime.now(timezone.utc),
                "nguoi_huy_id": int(actor["sub"]), "ly_do_huy": reason,
            })
            await self.audit.append(CreationAudit(
                nhan_vien_id=int(actor["sub"]), loai_doi_tuong="yeu_cau_san_xuat",
                doi_tuong_id=resource_id, thao_tac="huy", ly_do=reason,
                trang_thai_truoc=before.trang_thai, trang_thai_sau="da_huy",
                du_lieu_truoc=before.model_dump(mode="json"),
                du_lieu_sau={
                    **after.model_dump(mode="json"),
                    "hang_tra": [row.model_dump(mode="json") for row in returned],
                    "phieu_xuat": [
                        {"ma_phieu_xuat": row["ma_phieu_xuat"],
                         "xu_ly": "bo" if row["trang_thai"] == "nhap" else "tu_choi"}
                        for row in issues if row["trang_thai"] in {"nhap", "cho_duyet"}
                    ],
                },
            ))
        return self._detail(after, request_id)
