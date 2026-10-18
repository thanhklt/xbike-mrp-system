"""Commit/rollback adapter for a session shared by document and audit repositories."""

from types import TracebackType
from typing import Self

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictException


class SqlAlchemyTransaction:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self) -> Self:
        # Authentication may already have started this session's transaction.
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc is not None:
            await self.session.rollback()
            if isinstance(exc, IntegrityError):
                raise ConflictException(message="Document violates a database constraint") from exc
            return
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise ConflictException(message="Document violates a database constraint") from error
        except BaseException:
            await self.session.rollback()
            raise
