"""Durable local queue for ticket persistence after a database outage."""

import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4


class DieuChinhIncidents:
    def __init__(self, directory: Path | None = None):
        self.directory = directory or Path(
            os.environ.get("DIEU_CHINH_INCIDENT_DIR", ".runtime/dieu_chinh_kho")
        )

    async def store(self, failure: dict) -> None:
        await asyncio.to_thread(self._store, failure)

    def _store(self, failure: dict) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{uuid4()}.json"
        data = failure | {"actor": {"sub": failure["actor"]["sub"]}}
        temporary = path.with_suffix(".tmp")
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)


async def recover() -> None:
    """Retry ticket storage only. Never re-run approval or change stock."""
    from app.core.database import AsyncSessionLocal
    from app.modules.audit.repository import SqlAlchemyAuditRepository
    from app.modules.audit.service import AuditService
    from app.modules.dieu_chinh_kho.errors import DieuChinhError
    from app.modules.dieu_chinh_kho.repository import SqlAlchemyDieuChinhRepository
    from app.modules.dieu_chinh_kho.service import DieuChinhService

    incidents = DieuChinhIncidents()
    for path in sorted(incidents.directory.glob("*.json")):
        failure = json.loads(path.read_text(encoding="utf-8"))
        failure["incident_queued"] = True
        failure["stocks"] = {int(key): value for key, value in failure["stocks"].items()}
        async with AsyncSessionLocal() as session:
            service = DieuChinhService(
                SqlAlchemyDieuChinhRepository(session),
                AuditService(SqlAlchemyAuditRepository(session)),
                incidents,
            )
            try:
                await service.save_failure(failure)
            except DieuChinhError as error:
                if error.extra.get("ticket_da_luu"):
                    path.unlink()
                elif error.status == 503:
                    break
                else:
                    print(f"{path.name}: {error.code}; cần đối soát thủ công")
            else:
                # A concurrent successful approval requires no failure ticket.
                path.unlink()


if __name__ == "__main__":
    asyncio.run(recover())
