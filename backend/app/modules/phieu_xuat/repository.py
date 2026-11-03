"""Issue queries stay in the caller's session; no independent commit."""

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.phieu_xuat.models import ChiTietPhieuXuat, PhieuXuat
from app.modules.phieu_xuat.ports import PhieuXuatSnapshot


class SqlAlchemyPhieuXuatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def tong_da_xuat_thanh_pham(self, yeu_cau_ids: list[int]) -> dict[int, int]:
        rows = await self.session.execute(
            select(PhieuXuat.yeu_cau_san_xuat_id, func.sum(ChiTietPhieuXuat.so_luong))
            .join(ChiTietPhieuXuat, ChiTietPhieuXuat.phieu_xuat_id == PhieuXuat.id)
            .where(
                PhieuXuat.yeu_cau_san_xuat_id.in_(yeu_cau_ids),
                PhieuXuat.loai_phieu == "xuat_thanh_pham",
                PhieuXuat.trang_thai == "da_duyet",
            )
            .group_by(PhieuXuat.yeu_cau_san_xuat_id)
        )
        return {request_id: int(quantity) for request_id, quantity in rows}

    async def _snapshot(self, issue: PhieuXuat) -> PhieuXuatSnapshot:
        lines = (
            await self.session.scalars(
                select(ChiTietPhieuXuat)
                .where(ChiTietPhieuXuat.phieu_xuat_id == issue.id)
                .order_by(ChiTietPhieuXuat.id)
            )
        ).all()
        # JSON-compatible values for the append-only audit; no ORM crosses the port.
        values = {
            column.name: (
                str(value)
                if column.name == "tong_tien" and value is not None
                else value.isoformat()
                if column.name == "created_at"
                else value
            )
            for column in PhieuXuat.__table__.columns
            for value in [getattr(issue, column.name)]
        }
        values["chi_tiet"] = [
            {
                column.name: str(value)
                if column.name in {"don_gia_thuc", "tong_gia"} and value is not None
                else value
                for column in ChiTietPhieuXuat.__table__.columns
                for value in [getattr(line, column.name)]
            }
            for line in lines
        ]
        return PhieuXuatSnapshot(issue.id, issue.trang_thai, values)

    async def lock_by_sources(
        self, yeu_cau_id: int, lenh_ids: list[int]
    ) -> list[PhieuXuatSnapshot]:
        issues = (
            await self.session.scalars(
                select(PhieuXuat)
                .where(
                    or_(
                        PhieuXuat.yeu_cau_san_xuat_id == yeu_cau_id,
                        PhieuXuat.lenh_san_xuat_id.in_(lenh_ids),
                    )
                )
                .order_by(PhieuXuat.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).all()
        return [await self._snapshot(issue) for issue in issues]

    async def delete_draft(self, issue_id: int) -> None:
        await self.session.execute(
            delete(ChiTietPhieuXuat).where(ChiTietPhieuXuat.phieu_xuat_id == issue_id)
        )
        await self.session.execute(delete(PhieuXuat).where(PhieuXuat.id == issue_id))

    async def reject(self, issue_id: int) -> PhieuXuatSnapshot:
        issue = await self.session.get(PhieuXuat, issue_id)
        issue.trang_thai = "tu_choi"
        await self.session.flush()
        return await self._snapshot(issue)
