"""SQLAlchemy persistence for BOM; no commit or business policy."""

from collections.abc import Iterable

from sqlalchemy import column, exists, func, select, table, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bom.models import Bom, ChiTietBom
from app.modules.bom.ports import ActiveBom, BomContext
from app.modules.bom.schemas import BomListQuery, BomRead, ChiTietBomInput, ChiTietBomRead
from app.modules.mat_hang.models import MatHang
from app.modules.mat_hang.schemas import MatHangRead
from app.shared.records import RecordPage

# Read the v4 request reference without importing legacy production ORM.
_requests = table("YeuCauSanXuat", column("bom_id"))
_used = exists().where(_requests.c.bom_id == Bom.id)


def _to_read(bom: Bom, used: bool) -> BomRead:
    return BomRead(
        id=bom.id,
        mat_hang_id=bom.mat_hang_id,
        version=bom.version,
        created_at=bom.created_at,
        kich_hoat_gan_nhat_at=bom.kich_hoat_gan_nhat_at,
        is_active=bom.is_active,
        da_duoc_su_dung=used,
        chi_tiet=[ChiTietBomRead.model_validate(line) for line in bom.chi_tiet],
    )


class SqlAlchemyBomRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def context(self, item_id: int) -> BomContext | None:
        return await self._context(item_id, None)

    async def context_for_bom(self, bom_id: int) -> BomContext | None:
        return await self._context(None, bom_id)

    async def _context(self, item_id: int | None, bom_id: int | None) -> BomContext | None:
        # Header, active state, usage and immutable lines share one statement snapshot.
        row = (
            (
                await self.session.execute(
                    text("""
            SELECT to_jsonb(m) AS item, COALESCE((
                SELECT jsonb_agg(to_jsonb(b) || jsonb_build_object(
                    'da_duoc_su_dung', EXISTS(SELECT 1 FROM "YeuCauSanXuat" y WHERE y.bom_id=b.id),
                    'chi_tiet', COALESCE((SELECT jsonb_agg(to_jsonb(c) ORDER BY c.id)
                        FROM "ChiTietBom" c WHERE c.bom_id=b.id), '[]'::jsonb)
                ) ORDER BY b.version, b.id) FROM "Bom" b WHERE b.mat_hang_id=m.id
            ), '[]'::jsonb) AS versions
            FROM "MatHang" m WHERE m.id=COALESCE(CAST(:item_id AS integer),
                (SELECT mat_hang_id FROM "Bom" WHERE id=CAST(:bom_id AS integer)))
        """),
                    {"item_id": item_id, "bom_id": bom_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return BomContext(
            MatHangRead.model_validate(row["item"]),
            tuple(BomRead.model_validate(v) for v in row["versions"]),
        )

    async def lock_versions(self, item_id: int) -> None:
        await self.session.execute(
            select(Bom.id).where(Bom.mat_hang_id == item_id).order_by(Bom.id).with_for_update()
        )

    async def lock_bom_graph(self) -> None:
        await self.session.execute(text("SELECT pg_advisory_xact_lock(20261020, 2)"))

    async def list_bom(self, params: BomListQuery) -> RecordPage[BomRead]:
        query = select(Bom, _used.label("da_duoc_su_dung"))
        if params.mat_hang_id is not None:
            query = query.where(Bom.mat_hang_id == params.mat_hang_id)
        if params.version is not None:
            query = query.where(Bom.version == params.version)
        if params.is_active is not None:
            query = query.where(Bom.is_active == params.is_active)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = (params.page - 1) * params.page_size
        if offset >= total:
            return RecordPage([], total)
        sort_column = getattr(Bom, params.sort.removeprefix("-"))
        ordering = sort_column.desc() if params.sort.startswith("-") else sort_column.asc()
        rows = await self.session.execute(
            query.order_by(ordering, Bom.id)
            .offset(offset)
            .limit(params.page_size)
            .execution_options(populate_existing=True)
        )
        return RecordPage([_to_read(bom, used) for bom, used in rows], total)

    async def get_by_id(self, bom_id: int) -> BomRead | None:
        row = (
            await self.session.execute(
                select(Bom, _used.label("da_duoc_su_dung"))
                .where(Bom.id == bom_id)
                .execution_options(populate_existing=True)
            )
        ).one_or_none()
        return _to_read(*row) if row is not None else None

    async def get_active_for_item(self, mat_hang_id: int) -> BomRead | None:
        row = (
            await self.session.execute(
                select(Bom, _used.label("da_duoc_su_dung"))
                .where(Bom.mat_hang_id == mat_hang_id, Bom.is_active.is_(True))
                .execution_options(populate_existing=True)
            )
        ).one_or_none()
        return _to_read(*row) if row is not None else None

    async def get_item_types(self, item_ids: Iterable[int]) -> dict[int, str]:
        rows = await self.session.execute(
            select(MatHang.id, MatHang.loai_mat_hang).where(MatHang.id.in_(list(item_ids)))
        )
        return dict(rows.all())

    async def load_active_graph(self) -> dict[int, ActiveBom]:
        rows = await self.session.execute(
            select(
                Bom.mat_hang_id, Bom.id, Bom.version, ChiTietBom.mat_hang_id, ChiTietBom.so_luong
            )
            .outerjoin(ChiTietBom, ChiTietBom.bom_id == Bom.id)
            .where(Bom.is_active.is_(True))
            .order_by(Bom.id, ChiTietBom.id)
        )
        components: dict[int, list[tuple[int, int]]] = {}
        headers: dict[int, tuple[int, int]] = {}
        for output, bom_id, version, component, quantity in rows:
            headers[output] = (bom_id, version)
            components.setdefault(output, [])
            if component is not None:
                components[output].append((component, quantity))
        return {
            output: ActiveBom(bom_id, version, tuple(components[output]))
            for output, (bom_id, version) in headers.items()
        }

    async def next_version(self, mat_hang_id: int) -> int:
        maximum = await self.session.scalar(
            select(func.coalesce(func.max(Bom.version), 0)).where(Bom.mat_hang_id == mat_hang_id)
        )
        return (maximum or 0) + 1

    async def add(self, mat_hang_id: int, version: int, chi_tiet: list[ChiTietBomInput]) -> BomRead:
        record = Bom(
            mat_hang_id=mat_hang_id,
            version=version,
            is_active=True,
            kich_hoat_gan_nhat_at=func.clock_timestamp(),
            chi_tiet=[ChiTietBom(**component.model_dump()) for component in chi_tiet],
        )
        self.session.add(record)
        await self.session.flush()
        return await self._require_saved(record.id)

    async def deactivate(self, bom_id: int) -> BomRead:
        await self.session.execute(update(Bom).where(Bom.id == bom_id).values(is_active=False))
        return await self._require_saved(bom_id)

    async def activate(self, bom_id: int) -> BomRead:
        await self.session.execute(
            update(Bom)
            .where(Bom.id == bom_id)
            .values(is_active=True, kich_hoat_gan_nhat_at=func.clock_timestamp())
        )
        return await self._require_saved(bom_id)

    async def _require_saved(self, bom_id: int) -> BomRead:
        record = await self.get_by_id(bom_id)
        if record is None:
            raise LookupError("BOM disappeared during a locked write")
        return record
