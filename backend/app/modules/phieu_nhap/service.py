"""Receipt lifecycle with atomic stock posting and audit."""

from datetime import datetime, timezone
from hashlib import sha256

from pydantic import ValidationError

from app.core.errors import ConflictException, NotFoundException
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.inventory.ports import InventoryWriter, StockReceiptLine
from app.modules.phieu_nhap.errors import (
    ReceiptDependencyInvalid,
    ReceiptPreconditionFailed,
    ReceiptPreconditionRequired,
    ReceiptReferenced,
)
from app.modules.phieu_nhap.ports import ReceivingRepository
from app.modules.phieu_nhap.schemas import (
    INT_MAX,
    GoodsReceiptNoteCreate,
    GoodsReceiptNoteResponse,
    PhieuNhapActionRead,
    PhieuNhapActionResponse,
    PhieuNhapCreate,
    PhieuNhapDetailResponse,
    PhieuNhapListQuery,
    PhieuNhapListResponse,
    PhieuNhapPatch,
    PhieuNhapRead,
    ReceiptItemCreate,
)
from app.modules.users.schemas import ListResponseMeta, ResponseMeta
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response


class ReceivingService:
    def __init__(
        self,
        repository: ReceivingRepository,
        audit: AuditWriter,
        transaction: Transaction,
        inventory: InventoryWriter,
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction
        self.inventory = inventory

    async def _locked_receipt(self, record_id: int, if_match: str | None) -> PhieuNhapRead:
        if record_id > INT_MAX:
            raise NotFoundException()
        record = await self.repository.lock_receipt(record_id)
        if record is None:
            raise NotFoundException()
        if if_match is None:
            raise ReceiptPreconditionRequired()
        return record

    def _check_etag(self, record: PhieuNhapRead, if_match: str) -> None:
        if if_match.strip() != self.detail_response(record, "")[1]:
            raise ReceiptPreconditionFailed()

    async def _require_editable(self, record: PhieuNhapRead) -> None:
        if record.trang_thai != "nhap":
            raise ConflictException(message="Only draft receipts can be changed")
        if await self.repository.receipt_postings(record.id):
            raise ReceiptReferenced()

    async def _validate_parts(self, part_ids: list[int]) -> None:
        parts = await self.repository.lock_parts(part_ids)
        if len(parts) != len(part_ids):
            raise NotFoundException(message="Receipt item not found")
        if any(
            part.is_active is not True or part.loai_mat_hang not in ("nguyen_vat_lieu", "linh_kien")
            for part in parts
        ):
            raise ReceiptDependencyInvalid()

    async def _audit_change(
        self, operation: str, before: PhieuNhapRead, after: PhieuNhapRead | None, actor: dict
    ) -> None:
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong="phieu_nhap",
                doi_tuong_id=before.id,
                thao_tac=operation,
                du_lieu_truoc=before.model_dump(mode="json"),
                du_lieu_sau=after.model_dump(mode="json") if after is not None else None,
            )
        )

    async def patch_receipt(
        self,
        record_id: int,
        payload: PhieuNhapPatch,
        if_match: str | None,
        actor: dict,
        request_id: str,
    ) -> tuple[PhieuNhapDetailResponse, str]:
        async with self.transaction:
            before = await self._locked_receipt(record_id, if_match)
            self._check_etag(before, if_match)
            await self._require_editable(before)
            changes = {}
            items = None
            if "ncc_id" in payload.model_fields_set and payload.ncc_id != before.ncc_id:
                if payload.ncc_id is not None and not await self.repository.lock_supplier(
                    payload.ncc_id
                ):
                    raise NotFoundException(message="Supplier not found")
                changes["ncc_id"] = payload.ncc_id
            if payload.chi_tiet is not None:
                await self._validate_parts([item.mat_hang_id for item in payload.chi_tiet])
                current = [
                    {
                        "mat_hang_id": item.mat_hang_id,
                        "so_luong": item.so_luong,
                        "don_gia_thuc": item.don_gia_thuc,
                    }
                    for item in before.chi_tiet
                ]
                calculated = [
                    ReceiptItemCreate(
                        **item.model_dump(), tong_gia=item.so_luong * item.don_gia_thuc
                    )
                    for item in payload.chi_tiet
                ]
                total = sum(item.so_luong * item.don_gia_thuc for item in payload.chi_tiet)
                if (
                    current != [item.model_dump() for item in payload.chi_tiet]
                    or before.tong_tien != total
                    or any(
                        old.tong_gia != new.tong_gia
                        for old, new in zip(before.chi_tiet, calculated, strict=False)
                    )
                ):
                    items = calculated
                    changes["tong_tien"] = total
            after = before
            if changes or items is not None:
                after = await self.repository.patch_draft(record_id, changes, items)
                await self._audit_change("sua", before, after, actor)
        return self.detail_response(after, request_id)

    async def delete_receipt(self, record_id: int, if_match: str | None, actor: dict) -> None:
        async with self.transaction:
            before = await self._locked_receipt(record_id, if_match)
            self._check_etag(before, if_match)
            await self._require_editable(before)
            await self.repository.delete_draft(record_id)
            await self._audit_change("xoa_nhap", before, None, actor)

    async def complete_receipt(
        self, record_id: int, if_match: str | None, actor: dict, request_id: str
    ) -> tuple[PhieuNhapActionResponse, str]:
        async with self.transaction:
            before = await self._locked_receipt(record_id, if_match)
            postings = await self.repository.receipt_postings(record_id)
            already_posted = before.trang_thai == "hoan_thanh"
            if already_posted:
                expected = {
                    (item.id, item.mat_hang_id, item.so_luong, "nhap_vat_tu")
                    for item in before.chi_tiet
                }
                actual = {
                    (
                        entry.chi_tiet_phieu_nhap_id,
                        entry.mat_hang_id,
                        entry.so_luong_bien_dong,
                        entry.loai_giao_dich,
                    )
                    for entry in postings
                }
                if not expected or actual != expected or len(postings) != len(before.chi_tiet):
                    raise ConflictException(
                        message="Completed receipt does not match its stock ledger"
                    )
                after = before
                movement_ids = [entry.id for entry in postings]
            else:
                self._check_etag(before, if_match)
                if postings:
                    raise ReceiptReferenced()
                try:
                    valid = PhieuNhapCreate(
                        ncc_id=before.ncc_id,
                        chi_tiet=[
                            {
                                "mat_hang_id": item.mat_hang_id,
                                "so_luong": item.so_luong,
                                "don_gia_thuc": item.don_gia_thuc,
                            }
                            for item in before.chi_tiet
                        ],
                    )
                except ValidationError as exc:
                    raise ConflictException(
                        message="Draft has invalid items; correct it before completing"
                    ) from exc
                total = sum(item.so_luong * item.don_gia_thuc for item in valid.chi_tiet)
                if before.tong_tien != total or any(
                    item.tong_gia != item.so_luong * item.don_gia_thuc for item in before.chi_tiet
                ):
                    raise ConflictException(
                        message="Draft totals are inconsistent; correct it before completing"
                    )
                await self._validate_parts([item.mat_hang_id for item in before.chi_tiet])
                movement_ids = await self.inventory.receive_receipt(
                    [
                        StockReceiptLine(item.id, item.mat_hang_id, item.so_luong)
                        for item in before.chi_tiet
                    ],
                    int(actor["sub"]),
                    datetime.now(timezone.utc).replace(tzinfo=None),
                )
                after = await self.repository.mark_completed(record_id)
                await self._audit_change("hoan_tat", before, after, actor)
        detail, etag = self.detail_response(after, request_id)
        result = PhieuNhapActionRead(
            **after.model_dump(), giao_dich_kho_ids=movement_ids, da_ghi_so_truoc_do=already_posted
        )
        return PhieuNhapActionResponse(data=result, meta=detail.meta), etag

    @staticmethod
    def detail_response(
        record: PhieuNhapRead, request_id: str
    ) -> tuple[PhieuNhapDetailResponse, str]:
        etag = f'"{sha256(record.model_dump_json().encode()).hexdigest()}"'
        return PhieuNhapDetailResponse(data=record, meta=ResponseMeta(request_id=request_id)), etag

    async def list_receipts(
        self, params: PhieuNhapListQuery, request_id: str
    ) -> PhieuNhapListResponse:
        result = await self.repository.list_receipts(params)
        return PhieuNhapListResponse(
            data=result.items,
            meta=ListResponseMeta(
                request_id=request_id,
                page=params.page,
                page_size=params.page_size,
                total=result.total,
                total_pages=(result.total + params.page_size - 1) // params.page_size,
            ),
        )

    async def get_receipt(
        self, record_id: int, request_id: str
    ) -> tuple[PhieuNhapDetailResponse, str]:
        if record_id > INT_MAX:
            raise NotFoundException()
        record = await self.repository.get_receipt(record_id)
        if record is None:
            raise NotFoundException(message="Receipt not found")
        return self.detail_response(record, request_id)

    async def create_receipt(
        self, payload: PhieuNhapCreate, actor: dict, request_id: str
    ) -> tuple[PhieuNhapDetailResponse, str]:
        async with self.transaction:
            if payload.ncc_id is not None and not await self.repository.lock_supplier(
                payload.ncc_id
            ):
                raise NotFoundException(message="Supplier not found")
            await self._validate_parts([item.mat_hang_id for item in payload.chi_tiet])
            items = [
                ReceiptItemCreate(**item.model_dump(), tong_gia=item.so_luong * item.don_gia_thuc)
                for item in payload.chi_tiet
            ]
            draft = GoodsReceiptNoteCreate(
                ma_phieu_nhap="",
                nhan_vien_id=int(actor["sub"]),
                ncc_id=payload.ncc_id,
                tong_tien=sum(item.tong_gia for item in items),
                items=items,
            )
            record = await self.repository.add_draft(
                draft, created_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=int(actor["sub"]),
                    loai_doi_tuong="phieu_nhap",
                    doi_tuong_id=record.id,
                    du_lieu_sau=record.model_dump(mode="json"),
                )
            )
        return self.detail_response(record, request_id)

    async def list_entries(self, params: PageParams) -> PaginatedResponse[GoodsReceiptNoteResponse]:
        result = await self.repository.list_entries(params)
        return create_paginated_response(result.items, result.total, params.page, params.page_size)

    async def get_entry(self, record_id: int) -> GoodsReceiptNoteResponse:
        record = await self.repository.get_by_id(record_id)
        if record is None:
            raise NotFoundException(message=f"phieu_nhap {record_id} not found")
        return record

    async def create_entry(
        self, payload: GoodsReceiptNoteCreate, actor: dict
    ) -> GoodsReceiptNoteResponse:
        payload = payload.model_copy(update={"nhan_vien_id": int(actor["sub"])})
        async with self.transaction:
            created = await self.repository.add(payload, created_at=datetime.utcnow())
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=int(actor["sub"]),
                    loai_doi_tuong="phieu_nhap",
                    doi_tuong_id=created.record.id,
                    du_lieu_sau=created.snapshot,
                )
            )
        return created.record
