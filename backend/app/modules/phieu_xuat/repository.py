"""Issue queries stay in the caller's session; no independent commit."""

from datetime import datetime, time, timedelta, timezone

from sqlalchemy import DateTime, delete, exists, func, literal, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictException, NotFoundException
from app.modules.mat_hang.models import MatHang
from app.modules.phieu_xuat.models import ChiTietPhieuXuat, PhieuXuat
from app.modules.phieu_xuat.ports import IssuePart, IssueSource, PhieuXuatSnapshot
from app.modules.phieu_xuat.schemas import (
    ChiTietPhieuXuatCreate,
    PhieuXuatCreate,
    PhieuXuatQuery,
    PhieuXuatRead,
)
from app.modules.san_xuat.models import ChiTietLenhSanXuat, LenhSanXuat, YeuCauSanXuat
from app.shared.records import RecordPage


class SqlAlchemyPhieuXuatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _resource(self, record: PhieuXuat) -> PhieuXuatRead:
        lines = (
            await self.session.scalars(
                select(ChiTietPhieuXuat)
                .where(ChiTietPhieuXuat.phieu_xuat_id == record.id)
                .order_by(ChiTietPhieuXuat.id)
                .with_for_update(read=True)
                .execution_options(populate_existing=True)
            )
        ).all()
        return PhieuXuatRead.model_validate(
            {
                **{
                    column.name: getattr(record, column.name)
                    for column in PhieuXuat.__table__.columns
                },
                "chi_tiet": lines,
            }
        )

    @staticmethod
    def _scope(employee_id: int):
        return or_(
            exists().where(
                LenhSanXuat.id == PhieuXuat.lenh_san_xuat_id,
                LenhSanXuat.nhan_vien_id == employee_id,
            ),
            exists().where(
                YeuCauSanXuat.id == PhieuXuat.yeu_cau_san_xuat_id,
                YeuCauSanXuat.nhan_vien_duoc_giao_id == employee_id,
            ),
        )

    async def assigned_to(self, record: PhieuXuatRead, employee_id: int) -> bool:
        return bool(
            await self.session.scalar(
                select(exists().where(PhieuXuat.id == record.id, self._scope(employee_id)))
            )
        )

    async def list_issues(
        self, params: PhieuXuatQuery, employee_id: int | None
    ) -> RecordPage[PhieuXuatRead]:
        query = select(PhieuXuat)
        if employee_id is not None:
            query = query.where(self._scope(employee_id))
        if params.q:
            query = query.where(PhieuXuat.ma_phieu_xuat.icontains(params.q, autoescape=True))
        for name in (
            "loai_phieu",
            "trang_thai",
            "nhan_vien_id",
            "lenh_san_xuat_id",
            "yeu_cau_san_xuat_id",
        ):
            if (value := getattr(params, name)) is not None:
                query = query.where(getattr(PhieuXuat, name) == value)
        for day, end in ((params.tu_ngay, False), (params.den_ngay, True)):
            if day:
                boundary = func.timezone(
                    "Asia/Ho_Chi_Minh",
                    literal(
                        datetime.combine(day + timedelta(days=int(end)), time.min), type_=DateTime()
                    ),
                )
                query = query.where(
                    PhieuXuat.created_at < boundary if end else PhieuXuat.created_at >= boundary
                )
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        if (offset := (params.page - 1) * params.page_size) >= total:
            return RecordPage([], total)
        column = getattr(PhieuXuat, params.sort.lstrip("-"))
        order = column.desc() if params.sort.startswith("-") else column.asc()
        records = (
            await self.session.scalars(
                query.order_by(order, PhieuXuat.id)
                .offset(offset)
                .limit(params.page_size)
                .with_for_update(read=True)
            )
        ).all()
        return RecordPage([await self._resource(record) for record in records], total)

    async def get_issue(self, issue_id: int) -> PhieuXuatRead | None:
        record = await self.session.scalar(
            select(PhieuXuat)
            .where(PhieuXuat.id == issue_id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        return await self._resource(record) if record is not None else None

    async def lock_source(
        self, kind: str, order_id: int | None, request_id: int | None
    ) -> IssueSource:
        if kind == "xuat_vat_tu":
            request_id = await self.session.scalar(
                select(LenhSanXuat.yeu_cau_san_xuat_id).where(LenhSanXuat.id == order_id)
            )
        if request_id is None:
            raise NotFoundException(message="Source not found")
        # Same ordering as production cancellation: request, order, issue, items.
        request = await self.session.scalar(
            select(YeuCauSanXuat)
            .where(YeuCauSanXuat.id == request_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if request is None:
            raise NotFoundException(message="Source request not found")
        if kind == "xuat_thanh_pham":
            return IssueSource(
                request.trang_thai,
                request.nhan_vien_duoc_giao_id,
                request.id,
                request.trang_thai,
                {request.mat_hang_id: request.so_luong},
            )
        order = await self.session.scalar(
            select(LenhSanXuat)
            .where(LenhSanXuat.id == order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if order is None or order.yeu_cau_san_xuat_id != request.id:
            raise ConflictException(message="Source order changed")
        rows = (
            await self.session.execute(
                select(ChiTietLenhSanXuat.mat_hang_id, ChiTietLenhSanXuat.so_luong_can)
                .where(ChiTietLenhSanXuat.lenh_san_xuat_id == order.id)
                .order_by(ChiTietLenhSanXuat.id)
                .with_for_update(read=True)
            )
        ).all()
        return IssueSource(
            order.trang_thai, order.nhan_vien_id, request.id, request.trang_thai, dict(rows)
        )

    async def lock_context(self, issue_id: int) -> tuple[PhieuXuatRead, IssueSource] | None:
        peek = (
            await self.session.execute(
                select(
                    PhieuXuat.loai_phieu, PhieuXuat.lenh_san_xuat_id, PhieuXuat.yeu_cau_san_xuat_id
                ).where(PhieuXuat.id == issue_id)
            )
        ).one_or_none()
        if peek is None:
            return None
        source = await self.lock_source(*peek)
        record = await self.session.scalar(
            select(PhieuXuat)
            .where(PhieuXuat.id == issue_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return (await self._resource(record), source) if record is not None else None

    async def lock_parts(self, item_ids: list[int], *, posting: bool) -> list[IssuePart]:
        records = (
            await self.session.scalars(
                select(MatHang)
                .where(MatHang.id.in_(item_ids))
                .order_by(MatHang.id)
                .with_for_update(read=not posting)
                .execution_options(populate_existing=True)
            )
        ).all()
        return [
            IssuePart(r.id, r.loai_mat_hang, r.is_active, r.don_gia, r.so_luong_ton)
            for r in records
        ]

    async def _next_code(self) -> str:
        await self.session.execute(text("SELECT pg_advisory_xact_lock(20261022, 3)"))
        month = await self.session.scalar(
            text("SELECT to_char(now() AT TIME ZONE 'Asia/Ho_Chi_Minh','YYYYMM')")
        )
        prefix = f"PX-{month}-"
        serial = await self.session.scalar(
            text("""
            WITH history AS (
                SELECT du_lieu_truoc AS snapshot FROM "LichSuThaoTac" WHERE loai_doi_tuong='phieu_xuat'
                UNION ALL SELECT du_lieu_sau FROM "LichSuThaoTac" WHERE loai_doi_tuong='phieu_xuat'
            ), codes AS (
                SELECT ma_phieu_xuat AS code FROM "PhieuXuat"
                UNION ALL SELECT snapshot->>'ma_phieu_xuat' FROM history
            ) SELECT COALESCE(max(right(code,6)::int),0) FROM codes WHERE code ~ :pattern
        """),
            {"pattern": f"^{prefix}[0-9]{{6}}$"},
        )
        if serial >= 999999:
            raise ConflictException(message="Monthly issue number range exhausted")
        return f"{prefix}{serial + 1:06d}"

    async def add(self, payload: PhieuXuatCreate, actor_id: int) -> PhieuXuatRead:
        record = PhieuXuat(
            **payload.model_dump(exclude={"chi_tiet"}),
            ma_phieu_xuat=await self._next_code(),
            nhan_vien_id=actor_id,
        )
        self.session.add(record)
        await self.session.flush()
        self.session.add_all(
            [
                ChiTietPhieuXuat(phieu_xuat_id=record.id, **line.model_dump())
                for line in payload.chi_tiet
            ]
        )
        await self.session.flush()
        return await self._resource(record)

    async def replace_lines(
        self, issue_id: int, lines: list[ChiTietPhieuXuatCreate]
    ) -> PhieuXuatRead:
        await self.session.execute(
            delete(ChiTietPhieuXuat).where(ChiTietPhieuXuat.phieu_xuat_id == issue_id)
        )
        self.session.add_all(
            [ChiTietPhieuXuat(phieu_xuat_id=issue_id, **line.model_dump()) for line in lines]
        )
        await self.session.execute(
            update(PhieuXuat).where(PhieuXuat.id == issue_id).values(tong_tien=None)
        )
        await self.session.flush()
        return await self.get_issue(issue_id)

    async def change_state(self, issue_id: int, state: str) -> PhieuXuatRead:
        await self.session.execute(
            update(PhieuXuat).where(PhieuXuat.id == issue_id).values(trang_thai=state)
        )
        return await self.get_issue(issue_id)

    async def approved_quantities(self, record: PhieuXuatRead) -> dict[int, int]:
        source = (
            PhieuXuat.lenh_san_xuat_id == record.lenh_san_xuat_id
            if record.loai_phieu == "xuat_vat_tu"
            else PhieuXuat.yeu_cau_san_xuat_id == record.yeu_cau_san_xuat_id
        )
        rows = (
            await self.session.execute(
                select(ChiTietPhieuXuat.mat_hang_id, func.sum(ChiTietPhieuXuat.so_luong))
                .join(PhieuXuat, PhieuXuat.id == ChiTietPhieuXuat.phieu_xuat_id)
                .where(
                    source,
                    PhieuXuat.loai_phieu == record.loai_phieu,
                    PhieuXuat.trang_thai == "da_duyet",
                )
                .group_by(ChiTietPhieuXuat.mat_hang_id)
            )
        ).all()
        return dict(rows)

    async def postings(self, issue_id: int) -> list[int]:
        return list(
            (
                await self.session.scalars(
                    text(
                        'SELECT g.id FROM "GiaoDichKho" g JOIN "ChiTietPhieuXuat" c ON c.id=g.chi_tiet_phieu_xuat_id WHERE c.phieu_xuat_id=:id ORDER BY g.id'
                    ),
                    {"id": issue_id},
                )
            ).all()
        )

    async def freeze_prices(self, record: PhieuXuatRead, prices: dict[int, int]) -> PhieuXuatRead:
        total = 0
        for line in record.chi_tiet:
            price = prices[line.mat_hang_id]
            amount = price * line.so_luong
            total += amount
            await self.session.execute(
                update(ChiTietPhieuXuat)
                .where(ChiTietPhieuXuat.id == line.id)
                .values(don_gia_thuc=price, tong_gia=amount)
            )
        await self.session.execute(
            update(PhieuXuat)
            .where(PhieuXuat.id == record.id)
            .values(tong_tien=total, trang_thai="da_duyet")
        )
        return await self.get_issue(record.id)

    async def update_progress(self, request_id: int, total: int, required: int) -> None:
        await self.session.execute(
            update(YeuCauSanXuat)
            .where(YeuCauSanXuat.id == request_id)
            .values(
                trang_thai="hoan_thanh" if total == required else "dang_thuc_hien",
                completed_at=datetime.now(timezone.utc) if total == required else None,
            )
        )

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
        resource = await self._resource(issue)
        return PhieuXuatSnapshot(issue.id, issue.trang_thai, resource.model_dump(mode="json"))

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
