"""Issue queries stay in the caller's session; no independent commit."""

from datetime import datetime, time, timedelta

from sqlalchemy import DateTime, delete, func, literal, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictException, NotFoundException
from app.modules.mat_hang.models import MatHang
from app.modules.phieu_xuat.models import ChiTietPhieuXuat, PhieuXuat
from app.modules.phieu_xuat.ports import IssuePart, IssueSource, PhieuXuatSnapshot
from app.modules.phieu_xuat.schemas import (
    PhieuXuatCreate,
    PhieuXuatCuaToiQuery,
    PhieuXuatCuaToiRead,
    PhieuXuatQuery,
    PhieuXuatRead,
)
from app.modules.san_xuat.models import YeuCauSanXuat
from app.shared.records import RecordPage


class SqlAlchemyPhieuXuatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def begin_read_snapshot(self) -> None:
        # Auth only reads in this request; release its transaction before setting isolation.
        if self.session.in_transaction():
            await self.session.rollback()
        await self.session.connection(
            execution_options={"isolation_level": "REPEATABLE READ", "postgresql_readonly": True}
        )

    async def _lines(
        self, issue_ids: list[int], *, lock: bool
    ) -> dict[int, list[ChiTietPhieuXuat]]:
        grouped: dict[int, list[ChiTietPhieuXuat]] = {issue_id: [] for issue_id in issue_ids}
        if not issue_ids:
            return grouped
        query = (
            select(ChiTietPhieuXuat)
            .where(ChiTietPhieuXuat.phieu_xuat_id.in_(issue_ids))
            .order_by(ChiTietPhieuXuat.phieu_xuat_id, ChiTietPhieuXuat.id)
            .execution_options(populate_existing=True)
        )
        if lock:
            query = query.with_for_update(read=True)
        for line in (await self.session.scalars(query)).all():
            grouped[line.phieu_xuat_id].append(line)
        return grouped

    @staticmethod
    def _build(record: PhieuXuat, lines: list[ChiTietPhieuXuat]) -> PhieuXuatRead:
        return PhieuXuatRead.model_validate(
            {
                **{
                    column.name: getattr(record, column.name)
                    for column in PhieuXuat.__table__.columns
                },
                "chi_tiet": lines,
            }
        )

    async def _resource(self, record: PhieuXuat, *, lock: bool = True) -> PhieuXuatRead:
        lines = await self._lines([record.id], lock=lock)
        return self._build(record, lines[record.id])

    async def assigned_to(self, record: PhieuXuatRead, employee_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    'SELECT EXISTS (SELECT 1 FROM "YeuCauSanXuat" WHERE id=:id AND nhan_vien_duoc_giao_id=:employee)'
                ),
                {"id": record.yeu_cau_san_xuat_id, "employee": employee_id},
            )
        )

    async def list_issues(
        self, params: PhieuXuatQuery, employee_id: int | None
    ) -> RecordPage[PhieuXuatRead]:
        query = select(PhieuXuat)
        if getattr(params, "q", None):
            query = query.where(PhieuXuat.ma_phieu_xuat.icontains(params.q, autoescape=True))
        for name in (
            "loai_phieu",
            "trang_thai",
            "nhan_vien_id",
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
                query.order_by(order, PhieuXuat.id).offset(offset).limit(params.page_size)
            )
        ).all()
        lines = await self._lines([record.id for record in records], lock=False)
        return RecordPage([self._build(record, lines[record.id]) for record in records], total)

    async def list_my_issues(
        self, params: PhieuXuatCuaToiQuery, employee_id: int
    ) -> RecordPage[PhieuXuatCuaToiRead]:
        query = (
            select(PhieuXuat, YeuCauSanXuat.ma_yeu_cau_san_xuat)
            .join(YeuCauSanXuat, PhieuXuat.yeu_cau_san_xuat_id == YeuCauSanXuat.id)
            .where(YeuCauSanXuat.nhan_vien_duoc_giao_id == employee_id)
        )
        if getattr(params, "q", None):
            query = query.where(PhieuXuat.ma_phieu_xuat.icontains(params.q, autoescape=True))
        for name in (
            "loai_phieu",
            "trang_thai",
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
        sort_value = getattr(params, "sort", "-created_at") or "-created_at"
        column = getattr(PhieuXuat, sort_value.lstrip("-"))
        order = column.desc() if sort_value.startswith("-") else column.asc()
        results = (
            await self.session.execute(
                query.order_by(order, PhieuXuat.id.desc()).offset(offset).limit(params.page_size)
            )
        ).all()
        lines = await self._lines([record.id for record, _ in results], lock=False)
        return RecordPage(
            [
                PhieuXuatCuaToiRead(
                    **self._build(record, lines[record.id]).model_dump(),
                    ma_yeu_cau_san_xuat=source_code,
                )
                for record, source_code in results
            ],
            total,
        )

    async def get_issue(self, issue_id: int, *, lock: bool = True) -> PhieuXuatRead | None:
        query = (
            select(PhieuXuat)
            .where(PhieuXuat.id == issue_id)
            .execution_options(populate_existing=True)
        )
        if lock:
            query = query.with_for_update(read=True)
        record = await self.session.scalar(query)
        return await self._resource(record, lock=lock) if record is not None else None

    async def lock_source(self, kind: str, request_id: int, *, lock: bool = True) -> IssueSource:
        # Shared ordering with cancellation: source request, issue, items, reservations.
        row = (
            (
                await self.session.execute(
                    text(
                        'SELECT * FROM "YeuCauSanXuat" WHERE id=:id'
                        + (" FOR UPDATE" if lock else "")
                    ),
                    {"id": request_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise NotFoundException(message="Source request not found")
        demand = {row["mat_hang_id"]: row["so_luong"]}
        if kind == "xuat_linh_kien":
            demand = dict(
                (
                    await self.session.execute(
                        text(
                            'SELECT mat_hang_id, so_luong_can FROM "NhuCauLinhKien" WHERE yeu_cau_san_xuat_id=:id ORDER BY mat_hang_id'
                        ),
                        {"id": request_id},
                    )
                ).all()
            )
        completion = (
            await self.session.execute(
                text(
                    'SELECT id, trang_thai FROM "ChungTuHoanThanhSx" WHERE yeu_cau_san_xuat_id=:id'
                ),
                {"id": request_id},
            )
        ).one_or_none()
        return IssueSource(
            row["trang_thai"],
            row["nhan_vien_duoc_giao_id"],
            request_id,
            demand,
            row["loai_yeu_cau"],
            row["so_luong_can_san_xuat"],
            completion.id if completion else None,
            completion.trang_thai if completion else None,
            dict(row),
        )

    async def lock_context(self, issue_id: int) -> tuple[PhieuXuatRead, IssueSource] | None:
        peek = (
            await self.session.execute(
                select(PhieuXuat.loai_phieu, PhieuXuat.yeu_cau_san_xuat_id).where(
                    PhieuXuat.id == issue_id
                )
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
        if record is None:
            return None
        resource = await self._resource(record)
        if source.completion_id is not None:
            await self.session.execute(
                text('SELECT id FROM "ChungTuHoanThanhSx" WHERE id=:id FOR SHARE'),
                {"id": source.completion_id},
            )
        return resource, source

    async def exists_for_source(self, request_id: int, kind: str) -> bool:
        return (
            await self.session.scalar(
                select(PhieuXuat.id)
                .where(PhieuXuat.yeu_cau_san_xuat_id == request_id, PhieuXuat.loai_phieu == kind)
                .limit(1)
            )
        ) is not None

    async def lock_parts(
        self, item_ids: list[int], *, posting: bool, lock: bool = True
    ) -> list[IssuePart]:
        query = (
            select(MatHang)
            .where(MatHang.id.in_(item_ids))
            .order_by(MatHang.id)
            .execution_options(populate_existing=True)
        )
        if lock:
            query = query.with_for_update(read=not posting)
        records = (await self.session.scalars(query)).all()
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

    async def add(
        self, payload: PhieuXuatCreate, actor_id: int, demand: dict[int, int]
    ) -> PhieuXuatRead:
        record = PhieuXuat(
            **payload.model_dump(),
            ma_phieu_xuat=await self._next_code(),
            nhan_vien_id=actor_id,
        )
        self.session.add(record)
        await self.session.flush()
        self.session.add_all(
            [
                ChiTietPhieuXuat(phieu_xuat_id=record.id, mat_hang_id=item_id, so_luong=quantity)
                for item_id, quantity in sorted(demand.items())
            ]
        )
        await self.session.flush()
        return await self._resource(record)

    async def change_state(
        self, issue_id: int, state: str, actor_id: int, at: datetime, reason: str | None = None
    ) -> PhieuXuatRead:
        values = dict(trang_thai=state, updated_at=at, phien_ban=PhieuXuat.phien_ban + 1)
        if state == "cho_duyet":
            values.update(gui_at=at, nguoi_xu_ly_id=None, xu_ly_at=None, ly_do_tu_choi=None)
        else:
            values.update(nguoi_xu_ly_id=actor_id, xu_ly_at=at, ly_do_tu_choi=reason)
        await self.session.execute(
            update(PhieuXuat).where(PhieuXuat.id == issue_id).values(**values)
        )
        resource = await self.get_issue(issue_id)
        if resource is None:
            raise NotFoundException()
        return resource

    async def postings(self, issue_id: int) -> list[dict]:
        rows = await self.session.execute(
            text(
                'SELECT g.id, g.chi_tiet_phieu_xuat_id, g.mat_hang_id, g.loai_giao_dich, g.so_luong_bien_dong FROM "GiaoDichKho" g JOIN "ChiTietPhieuXuat" c ON c.id=g.chi_tiet_phieu_xuat_id WHERE c.phieu_xuat_id=:id ORDER BY g.id'
            ),
            {"id": issue_id},
        )
        return [dict(row) for row in rows.mappings()]

    async def freeze_prices(
        self, record: PhieuXuatRead, prices: dict[int, int], actor_id: int, at: datetime
    ) -> PhieuXuatRead:
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
            .values(
                tong_tien=total,
                trang_thai="da_duyet",
                nguoi_xu_ly_id=actor_id,
                xu_ly_at=at,
                updated_at=at,
                ly_do_tu_choi=None,
                phien_ban=PhieuXuat.phien_ban + 1,
            )
        )
        resource = await self.get_issue(record.id)
        if resource is None:
            raise NotFoundException()
        return resource

    async def ready_for_production(self, request_id: int, at: datetime) -> dict:
        result = await self.session.execute(
            text('''UPDATE "YeuCauSanXuat" SET trang_thai='dang_thuc_hien', updated_at=:at,
                phien_ban=phien_ban+1 WHERE id=:id AND trang_thai='cho_bo_sung_linh_kien'
                RETURNING *'''), {"id": request_id, "at": at},
        )
        return dict(result.mappings().one())

    async def update_progress(self, request_id: int, at: datetime) -> dict:
        row = (
            (
                await self.session.execute(
                    text(
                        """UPDATE "YeuCauSanXuat" SET trang_thai='hoan_thanh', completed_at=:at, updated_at=:at, phien_ban=phien_ban+1 WHERE id=:id RETURNING *"""
                    ),
                    {"id": request_id, "at": at},
                )
            )
            .mappings()
            .one()
        )
        return dict(row)

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

    # UC-28 Hủy yêu cầu sản xuất — D4 đọc phiếu của yêu cầu không khóa (specs/use_cases/production/UC-28.md)
    async def phieu_cua_yeu_cau(self, yeu_cau_id: int) -> list[dict]:
        rows = await self.session.execute(
            select(
                PhieuXuat.id, PhieuXuat.ma_phieu_xuat, PhieuXuat.loai_phieu, PhieuXuat.trang_thai
            )
            .where(PhieuXuat.yeu_cau_san_xuat_id == yeu_cau_id)
            .order_by(PhieuXuat.id)
        )
        return [dict(row) for row in rows.mappings()]

    # UC-28 Hủy yêu cầu sản xuất — A4 khóa phiếu sau khóa yêu cầu (specs/use_cases/production/UC-28.md)
    async def lock_by_sources(self, yeu_cau_id: int) -> list[PhieuXuatSnapshot]:
        issues = (
            await self.session.scalars(
                select(PhieuXuat)
                .where(PhieuXuat.yeu_cau_san_xuat_id == yeu_cau_id)
                .order_by(PhieuXuat.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).all()
        return [await self._snapshot(issue) for issue in issues]

    # UC-28 Hủy yêu cầu sản xuất — R4 bỏ phiếu nháp cùng chi tiết (specs/use_cases/production/UC-28.md)
    async def delete_draft(self, issue_id: int) -> None:
        await self.session.execute(
            delete(ChiTietPhieuXuat).where(ChiTietPhieuXuat.phieu_xuat_id == issue_id)
        )
        await self.session.execute(delete(PhieuXuat).where(PhieuXuat.id == issue_id))

    # UC-28 Hủy yêu cầu sản xuất — R4 từ chối phiếu chờ duyệt (specs/use_cases/production/UC-28.md)
    async def reject(self, issue_id: int, actor_id: int, at: datetime) -> PhieuXuatSnapshot:
        resource = await self.change_state(issue_id, "tu_choi", actor_id, at, "Yêu cầu đã hủy")
        return PhieuXuatSnapshot(resource.id, resource.trang_thai, resource.model_dump(mode="json"))
