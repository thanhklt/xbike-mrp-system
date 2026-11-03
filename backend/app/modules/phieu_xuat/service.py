"""Production-facing issue cancellation in the caller's atomic operation."""

from app.core.errors import PostedProductionDependency
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.phieu_xuat.ports import PhieuXuatRepository


class PhieuXuatSanXuatService:
    def __init__(self, repository: PhieuXuatRepository, audit: AuditWriter):
        self.repository = repository
        self.audit = audit

    async def tong_da_xuat_thanh_pham(self, yeu_cau_ids: list[int]) -> dict[int, int]:
        return await self.repository.tong_da_xuat_thanh_pham(yeu_cau_ids)

    async def co_phieu_da_ghi_so(self, yeu_cau_id: int, lenh_ids: list[int]) -> bool:
        records = await self.repository.lock_by_sources(yeu_cau_id, lenh_ids)
        return any(record.trang_thai == "da_duyet" for record in records)

    async def huy_phieu_chua_ghi_so(
        self, yeu_cau_id: int, lenh_ids: list[int], ly_do: str, actor_id: int
    ) -> None:
        records = await self.repository.lock_by_sources(yeu_cau_id, lenh_ids)
        if any(record.trang_thai == "da_duyet" for record in records):
            raise PostedProductionDependency()
        for record in records:
            if record.trang_thai not in {"nhap", "cho_duyet"}:
                continue
            if record.trang_thai == "nhap":
                await self.repository.delete_draft(record.id)
                after = {}
                action = "xoa_nhap"
            else:
                after = (await self.repository.reject(record.id)).values
                action = "tu_choi"
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=actor_id,
                    loai_doi_tuong="phieu_xuat",
                    doi_tuong_id=record.id,
                    thao_tac=action,
                    du_lieu_truoc=record.values,
                    du_lieu_sau=after,
                    ly_do=ly_do,
                )
            )
