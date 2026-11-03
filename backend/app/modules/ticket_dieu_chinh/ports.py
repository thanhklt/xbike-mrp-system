"""Persistence contract for ticket handling; no stock or adjustment mutation methods."""

from datetime import datetime
from typing import Protocol

from app.modules.ticket_dieu_chinh.schemas import TicketListQuery, TicketRead
from app.shared.records import RecordPage


class TicketDieuChinhRepository(Protocol):
    async def list_tickets(self, params: TicketListQuery) -> RecordPage[TicketRead]: ...
    async def get_ticket(self, ticket_id: int) -> TicketRead | None: ...
    async def lock_ticket(self, ticket_id: int) -> TicketRead | None: ...
    async def claim_ticket(self, ticket_id: int, actor_id: int) -> TicketRead: ...
    async def resolve_ticket(
        self, ticket_id: int, actor_id: int, result: str, closed_at: datetime
    ) -> TicketRead: ...
