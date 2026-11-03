"""Atomic receipt corrections and independent failure tickets."""

import hashlib
from collections import defaultdict

from sqlalchemy.exc import SQLAlchemyError

from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.dieu_chinh_kho.errors import DieuChinhError
from app.modules.dieu_chinh_kho.ports import DieuChinhRepository, IncidentStore
from app.modules.dieu_chinh_kho.schemas import DieuChinhRead, DongDieuChinh


def etag(record: dict) -> str:
    value = DieuChinhRead.model_validate(record).model_dump_json()
    return '"' + hashlib.sha256(value.encode()).hexdigest() + '"'


def precondition(record: dict | None, token: str | None) -> dict:
    if record is None:
        raise DieuChinhError(404, "khong_tim_thay", "Không tìm thấy phiếu")
    if token is None:
        raise DieuChinhError(428, "thieu_if_match", "Thiếu If-Match")
    if token != etag(record):
        raise DieuChinhError(412, "du_lieu_da_thay_doi", "Dữ liệu đã thay đổi")
    return record


def require_state(record: dict, state: str):
    if record["trang_thai"] != state:
        raise DieuChinhError(
            409, "trang_thai_khong_hop_le", "Trạng thái phiếu không cho phép thao tác"
        )


def stock_changes(lines: list[dict], stocks: dict[int, int]) -> dict[int, int]:
    changes = defaultdict(int)
    for line in lines:
        changes[line["mat_hang_id"]] += line["so_luong_bien_dong"]
    if any(not 0 <= stocks[id] + delta <= 2147483647 for id, delta in changes.items()):
        raise DieuChinhError(
            409, "dieu_chinh_khong_hop_le", "Số dư tồn sau điều chỉnh không hợp lệ"
        )
    return dict(changes)


class DieuChinhService:
    def __init__(
        self, repository: DieuChinhRepository, audit: AuditWriter, incidents: IncidentStore
    ):
        self.repo, self.audit, self.incidents = repository, audit, incidents

    async def verify_actor(self, actor: dict) -> None:
        identity = await self.repo.actor(int(actor["sub"]))
        if identity is None:
            raise DieuChinhError(401, "chua_xac_thuc", "Tài khoản không còn tồn tại")
        if identity["trang_thai"] != "hoat_dong" or identity["ma_vai_tro"] != "quan_ly":
            raise DieuChinhError(403, "khong_co_quyen", "Tài khoản không còn quyền điều chỉnh kho")

    async def append_audit(self, actor: dict, action: str, record: dict, before=None, reason=None):
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong="phieu_dieu_chinh_kho",
                doi_tuong_id=record["id"],
                thao_tac=action,
                du_lieu_truoc=before,
                du_lieu_sau=DieuChinhRead.model_validate(record).model_dump(mode="json"),
                ly_do=reason,
            )
        )

    async def lines(self, receipt_id: int, inputs) -> list[dict]:
        receipt = await self.repo.lock_receipt(receipt_id)
        if receipt is None:
            raise DieuChinhError(404, "khong_tim_thay", "Không tìm thấy phiếu nhập")
        if receipt["trang_thai"] != "hoan_thanh":
            raise DieuChinhError(409, "dieu_chinh_khong_hop_le", "Phiếu nhập chưa hoàn thành")
        lines = []
        for entry in inputs:
            source = await self.repo.source(entry.giao_dich_goc_id, receipt_id)
            if source is None:
                raise DieuChinhError(
                    409,
                    "dieu_chinh_khong_hop_le",
                    "Nguồn phải là giao dịch nhập cùng phiếu và mặt hàng hợp lệ",
                )
            delta = entry.so_luong_dung - source["so_luong_hieu_luc_truoc"]
            if delta == 0 or not -2147483648 <= delta <= 2147483647:
                raise DieuChinhError(
                    409, "dieu_chinh_khong_hop_le", "Biến động phải khác 0 và trong miền integer"
                )
            lines.append(
                source | {"so_luong_dung": entry.so_luong_dung, "so_luong_bien_dong": delta}
            )
        return lines

    async def get(self, id):
        record = await self.repo.lock(id)
        if record is None:
            raise DieuChinhError(404, "khong_tim_thay", "Không tìm thấy phiếu")
        return record

    async def create(self, payload, actor):
        try:
            await self.repo.serialize()
            await self.verify_actor(actor)
            lines = await self.lines(payload.phieu_nhap_id, payload.chi_tiet)
            code = await self.repo.next_code("PhieuDieuChinhKho", "ma_phieu", "DCK")
            records = await self.repo.create_header(
                code=code,
                receipt=payload.phieu_nhap_id,
                actor=int(actor["sub"]),
                reason=payload.ly_do,
            )
            id = records[0]["id"]
            await self.repo.replace_lines(id, lines)
            record = await self.get(id)
            await self.append_audit(actor, "tao", record)
            await self.repo.session.commit()
            return record
        except BaseException:
            await self.repo.session.rollback()
            raise

    async def mutate(self, id, action, payload, token, actor):
        try:
            locked = await self.repo.lock(id)
            await self.verify_actor(actor)
            record = precondition(locked, token)
            before = DieuChinhRead.model_validate(record).model_dump(mode="json")
            require_state(
                record,
                {
                    "sua": "nhap",
                    "xoa_nhap": "nhap",
                    "gui": "nhap",
                    "tu_choi": "cho_duyet",
                    "ve_nhap": "tu_choi",
                }[action],
            )
            if action == "sua":
                if payload.chi_tiet is not None:
                    lines = await self.lines(record["phieu_nhap_id"], payload.chi_tiet)
                    await self.repo.replace_lines(id, lines)
                if payload.ly_do is not None:
                    await self.repo.update_reason(id=id, reason=payload.ly_do)
            elif action == "xoa_nhap":
                # Audit is append-only and has no FK to a deleted draft.
                await self.append_audit(actor, action, record, before)
                await self.repo.delete_lines(id=id)
                await self.repo.delete_header(id=id)
                await self.repo.session.commit()
                return None
            else:
                if action == "gui":
                    await self.lines(
                        record["phieu_nhap_id"],
                        [
                            DongDieuChinh(**line)
                            for line in [
                                {
                                    "giao_dich_goc_id": x["giao_dich_goc_id"],
                                    "so_luong_dung": x["so_luong_dung"],
                                }
                                for x in record["chi_tiet"]
                            ]
                        ],
                    )
                state = {"gui": "cho_duyet", "tu_choi": "tu_choi", "ve_nhap": "nhap"}[action]
                await self.repo.update_state(state=state, id=id)
            result = await self.get(id)
            if DieuChinhRead.model_validate(result).model_dump(mode="json") != before:
                await self.append_audit(
                    actor, action, result, before, getattr(payload, "ly_do", None)
                )
            await self.repo.session.commit()
            return result
        except BaseException:
            await self.repo.session.rollback()
            raise

    async def approve(self, id, token, actor):
        failure = None
        try:
            record = await self.repo.lock(id)
            await self.verify_actor(actor)
            if record and record["trang_thai"] == "da_duyet":
                ids = await self.repo.ledger_ids(id)
                await self.repo.session.rollback()
                return record, ids, True
            record = precondition(record, token)
            require_state(record, "cho_duyet")
            inputs = [
                DongDieuChinh(
                    giao_dich_goc_id=x["giao_dich_goc_id"], so_luong_dung=x["so_luong_dung"]
                )
                for x in record["chi_tiet"]
            ]
            lines = await self.lines(record["phieu_nhap_id"], inputs)
            stocks = await self.repo.stock([line["mat_hang_id"] for line in lines])
            failure = {
                "id": id,
                "record": DieuChinhRead.model_validate(record).model_dump(mode="json"),
                "lines": lines,
                "stocks": stocks,
                "actor": actor,
            }
            changes = stock_changes(lines, stocks)
            before = DieuChinhRead.model_validate(record).model_dump(mode="json")
            await self.repo.replace_lines(id, lines)
            # Detail snapshot must be written before header becomes immutable.
            await self.repo.mark_approved(id=id)
            current = await self.get(id)
            for item_id, delta in changes.items():
                await self.repo.update_stock(delta=delta, id=item_id)
            for line in current["chi_tiet"]:
                await self.repo.insert_movement(
                    item=line["mat_hang_id"],
                    delta=line["so_luong_bien_dong"],
                    line=line["id"],
                    actor=int(actor["sub"]),
                )
            await self.append_audit(actor, "duyet", current, before)
            ids = await self.repo.ledger_ids(id)
            await self.repo.session.commit()
            return current, ids, False
        except (DieuChinhError, SQLAlchemyError) as error:
            await self.repo.session.rollback()
            if failure is None:
                raise
            failure["message"] = (
                "Điều chỉnh không hợp lệ"
                if isinstance(error, DieuChinhError)
                else "Không thể ghi sổ điều chỉnh"
            )
            return await self.save_failure(failure)
        except BaseException:
            await self.repo.session.rollback()
            raise

    async def save_failure(self, failure):
        try:
            record = await self.repo.lock(failure["id"])
            if record and record["trang_thai"] == "da_duyet":
                ids = await self.repo.ledger_ids(record["id"])
                await self.repo.session.rollback()
                return record, ids, True
            if (
                record is None
                or etag(record) != etag(failure["record"])
                or record["trang_thai"] != "cho_duyet"
            ):
                raise DieuChinhError(
                    409, "can_xu_ly_thu_cong", "Phiếu đã thay đổi; không tạo ticket trùng"
                )
            code = await self.repo.next_code("TicketLoiDieuChinh", "ma_ticket", "TKDC")
            tickets = await self.repo.create_ticket(
                code=code,
                receipt=record["phieu_nhap_id"],
                actor=int(failure["actor"]["sub"]),
                message=failure["message"],
            )
            ticket_id = tickets[0]["id"]
            for line in failure["lines"]:
                await self.repo.create_ticket_line(
                    ticket=ticket_id,
                    receipt_line=line["chi_tiet_phieu_nhap_id"],
                    item=line["mat_hang_id"],
                    previous=line["so_luong_hieu_luc_truoc"],
                    desired=line["so_luong_dung"],
                    delta=line["so_luong_bien_dong"],
                    stock=failure["stocks"][line["mat_hang_id"]],
                )
            await self.repo.mark_failed(id=record["id"])
            await self.append_audit(failure["actor"], "ghi_nhan_loi", await self.get(record["id"]))
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=int(failure["actor"]["sub"]),
                    loai_doi_tuong="ticket_loi_dieu_chinh",
                    doi_tuong_id=ticket_id,
                    thao_tac="tao",
                    du_lieu_sau={"ma_ticket": code, "phieu_nhap_id": record["phieu_nhap_id"]},
                )
            )
            await self.repo.session.commit()
        except SQLAlchemyError:
            await self.repo.session.rollback()
            if not failure.get("incident_queued"):
                await self.incidents.store(failure)
            raise DieuChinhError(
                503,
                "dich_vu_tam_thoi_khong_kha_dung",
                "Chưa lưu được ticket",
                ticket_id=None,
                ticket_da_luu=False,
            ) from None
        except BaseException:
            await self.repo.session.rollback()
            raise
        raise DieuChinhError(
            409,
            "dieu_chinh_khong_hop_le",
            failure["message"],
            details=failure["lines"],
            ticket_id=ticket_id,
            ticket_da_luu=True,
            phieu_dieu_chinh_kho_id=record["id"],
            trang_thai_phieu="loi",
        )
