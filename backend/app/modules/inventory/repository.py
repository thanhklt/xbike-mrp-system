"""Inventory and ledger queries; no stock mutation is implemented here."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.persistence import select_page
from app.modules.inventory.models import StockLevel, StockMovement
from app.modules.inventory.schemas import StockLevelResponse, StockMovementResponse
from app.shared.pagination import PageParams
from app.shared.records import RecordPage


class SqlAlchemyInventoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_stock(self, params: PageParams) -> RecordPage[StockLevelResponse]:
        return await select_page(self.session, StockLevel, StockLevelResponse, params)

    async def list_movements(self, params: PageParams) -> RecordPage[StockMovementResponse]:
        return await select_page(self.session, StockMovement, StockMovementResponse, params)
