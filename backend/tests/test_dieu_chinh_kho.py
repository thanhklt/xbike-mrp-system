"""Validation, API authorization and PostgreSQL transaction regressions."""

import json

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.audit.service import AuditService
from app.modules.dieu_chinh_kho.errors import DieuChinhError
from app.modules.dieu_chinh_kho.incidents import DieuChinhIncidents
from app.modules.dieu_chinh_kho.repository import SqlAlchemyDieuChinhRepository
from app.modules.dieu_chinh_kho.schemas import (
    DieuChinhCreate,
    DieuChinhPatch,
    DieuChinhQuery,
    EmptyInput,
    LyDoInput,
)
from app.modules.dieu_chinh_kho.service import DieuChinhService, etag, stock_changes


@pytest.mark.parametrize(
    "changes",
    [
        {"phieu_nhap_id": True},
        {"chi_tiet": []},
        {"ly_do": "  "},
        {"trang_thai": "nhap"},
        {"chi_tiet": [{"giao_dich_goc_id": 1, "so_luong_dung": 1.5}]},
        {"chi_tiet": [{"giao_dich_goc_id": 1, "so_luong_dung": 5}] * 2},
    ],
)
def test_invalid_create(changes):
    with pytest.raises(ValidationError):
        DieuChinhCreate.model_validate(
            {
                "phieu_nhap_id": 1,
                "ly_do": "Kiểm tra",
                "chi_tiet": [{"giao_dich_goc_id": 1, "so_luong_dung": 5}],
            }
            | changes
        )


@pytest.mark.parametrize("payload", [{"ly_do": None}, {"chi_tiet": None}, {"chi_tiet": []}])
def test_patch_rejects_null_and_empty_lines(payload):
    with pytest.raises(ValidationError):
        DieuChinhPatch.model_validate(payload)


def test_query_rejects_dates_and_unsupported_sort():
    for payload in ({"sort": "ly_do"}, {"tu_ngay": "2026-11-03", "den_ngay": "2026-11-02"}):
        with pytest.raises(ValidationError):
            DieuChinhQuery.model_validate(payload)


def test_stock_aggregates_all_sources_of_same_item():
    lines = [{"mat_hang_id": 1, "so_luong_bien_dong": -4}] * 2
    with pytest.raises(DieuChinhError):
        stock_changes(lines, {1: 5})
    assert stock_changes(lines, {1: 10}) == {1: -8}


async def test_incident_persists_only_actor_id(tmp_path):
    queue = DieuChinhIncidents(tmp_path)
    await queue.store({"id": 1, "actor": {"sub": "2", "token": "secret"}})
    value = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    assert value["actor"] == {"sub": "2"}


@pytest.mark.parametrize("role", ["quan_tri_vien", "nhan_vien"])
async def test_every_endpoint_rejects_other_roles(async_client, role):
    from app.dependencies import get_current_user_payload
    from app.main import app

    app.dependency_overrides[get_current_user_payload] = lambda: {"sub": "2", "roles": [role]}
    try:
        for method, path, body in [
            ("GET", "", None),
            ("GET", "/1", None),
            (
                "POST",
                "",
                {
                    "phieu_nhap_id": 1,
                    "ly_do": "test",
                    "chi_tiet": [{"giao_dich_goc_id": 1, "so_luong_dung": 5}],
                },
            ),
            ("PATCH", "/1", {}),
            ("DELETE", "/1", None),
            *[
                (
                    "POST",
                    f"/1/{action}",
                    {"ly_do": "test"} if action in ("tu_choi", "ve_nhap") else {},
                )
                for action in ("gui", "duyet", "tu_choi", "ve_nhap")
            ],
        ]:
            response = await async_client.request(
                method,
                "/api/v1/phieu_dieu_chinh_kho" + path,
                **({"json": body} if body is not None else {}),
            )
            assert response.status_code == 403, response.text
            assert response.json()["error"]["code"] == "khong_co_quyen"
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
async def correction_service(bootstrapped_connection, tmp_path):
    async with AsyncSession(
        bind=bootstrapped_connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    ) as session:
        yield DieuChinhService(
            SqlAlchemyDieuChinhRepository(session),
            AuditService(SqlAlchemyAuditRepository(session)),
            DieuChinhIncidents(tmp_path),
        )


def payload(desired=986):
    return DieuChinhCreate(
        phieu_nhap_id=1,
        ly_do="Đối chiếu",
        chi_tiet=[{"giao_dich_goc_id": 12, "so_luong_dung": desired}],
    )


ACTOR = {"sub": "2"}


async def test_postgres_workflow_and_duplicate_approval(correction_service):
    service = correction_service
    initial = (await service.repo.stock([17]))[17]
    draft = await service.create(payload(), ACTOR)
    sent = await service.mutate(draft["id"], "gui", EmptyInput(), etag(draft), ACTOR)
    approved, ids, previous = await service.approve(sent["id"], etag(sent), ACTOR)
    assert approved["trang_thai"] == "da_duyet"
    assert len(ids) == 1 and previous is False
    assert (await service.repo.stock([17]))[17] == initial + 1
    repeated, repeated_ids, previous = await service.approve(sent["id"], '"stale"', ACTOR)
    assert previous is True and repeated_ids == ids and repeated == approved
    assert (await service.repo.stock([17]))[17] == initial + 1


async def test_postgres_reject_return_draft_etag_and_delete(correction_service):
    service = correction_service
    draft = await service.create(payload(), ACTOR)
    for token, status in [(None, 428), ('"old"', 412)]:
        with pytest.raises(DieuChinhError) as error:
            await service.mutate(draft["id"], "gui", EmptyInput(), token, ACTOR)
        assert error.value.status == status
    sent = await service.mutate(draft["id"], "gui", EmptyInput(), etag(draft), ACTOR)
    rejected = await service.mutate(
        sent["id"], "tu_choi", LyDoInput(ly_do="Sai chứng từ"), etag(sent), ACTOR
    )
    draft = await service.mutate(
        sent["id"], "ve_nhap", LyDoInput(ly_do="Sửa lại"), etag(rejected), ACTOR
    )
    patched = await service.mutate(
        draft["id"], "sua", DieuChinhPatch(ly_do="Lý do mới"), etag(draft), ACTOR
    )
    await service.mutate(patched["id"], "xoa_nhap", None, etag(patched), ACTOR)
    assert await service.repo.get(patched["id"]) is None


async def test_postgres_insufficient_stock_ticket_and_immutable_error(correction_service):
    service = correction_service
    stocks = await service.repo.stock([17])
    draft = await service.create(payload(0), ACTOR)
    sent = await service.mutate(draft["id"], "gui", EmptyInput(), etag(draft), ACTOR)
    with pytest.raises(DieuChinhError) as failure:
        await service.approve(sent["id"], etag(sent), ACTOR)
    assert failure.value.extra["ticket_da_luu"] is True
    assert failure.value.extra["ticket_id"] > 0
    assert await service.repo.stock([17]) == stocks
    assert await service.repo.ledger_ids(sent["id"]) == []
    failed = await service.get(sent["id"])
    assert failed["trang_thai"] == "loi"
    for action in ("tu_choi", "ve_nhap"):
        with pytest.raises(DieuChinhError) as error:
            await service.mutate(sent["id"], action, LyDoInput(ly_do="test"), etag(failed), ACTOR)
        assert error.value.status == 409


async def test_postgres_all_nine_routes(async_client, correction_service):
    from app.dependencies import get_current_user_payload
    from app.main import app
    from app.modules.dieu_chinh_kho.router import get_service

    app.dependency_overrides[get_current_user_payload] = lambda: {"sub": "2", "roles": ["quan_ly"]}
    app.dependency_overrides[get_service] = lambda: correction_service
    base = "/api/v1/phieu_dieu_chinh_kho"
    try:
        response = await async_client.post(base, json=payload().model_dump())
        assert response.status_code == 201, response.text
        path = response.headers["location"]
        detail = await async_client.get(path)
        assert detail.status_code == 200 and detail.headers["etag"] == response.headers["etag"]
        listing = await async_client.get(
            base, params={"q": response.json()["data"]["ma_phieu"], "sort": "-created_at"}
        )
        assert listing.status_code == 200 and listing.json()["meta"]["total"] == 1
        assert (await async_client.get(base, params={"unknown": "x"})).status_code == 422
        assert (await async_client.patch(path, json={})).status_code == 428
        patched = await async_client.patch(
            path, json={"ly_do": "Sửa lý do"}, headers={"If-Match": detail.headers["etag"]}
        )
        assert patched.status_code == 200
        sent = await async_client.post(
            path + "/gui", json={}, headers={"If-Match": patched.headers["etag"]}
        )
        assert sent.status_code == 200
        rejected = await async_client.post(
            path + "/tu_choi",
            json={"ly_do": "Kiểm tra lại"},
            headers={"If-Match": sent.headers["etag"]},
        )
        assert rejected.status_code == 200
        draft = await async_client.post(
            path + "/ve_nhap",
            json={"ly_do": "Đã sửa"},
            headers={"If-Match": rejected.headers["etag"]},
        )
        assert draft.status_code == 200
        assert (
            await async_client.delete(path, headers={"If-Match": draft.headers["etag"]})
        ).status_code == 204
        created = await async_client.post(base, json=payload().model_dump())
        path = created.headers["location"]
        sent = await async_client.post(
            path + "/gui", json={}, headers={"If-Match": created.headers["etag"]}
        )
        approved = await async_client.post(
            path + "/duyet", json={}, headers={"If-Match": sent.headers["etag"]}
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["da_ghi_so_truoc_do"] is False
        repeated = await async_client.post(path + "/duyet", json={}, headers={"If-Match": '"old"'})
        assert repeated.status_code == 200 and repeated.json()["da_ghi_so_truoc_do"] is True
    finally:
        app.dependency_overrides.clear()


async def test_audit_write_failure_rolls_back_stock_and_saves_ticket(
    correction_service, monkeypatch
):
    from sqlalchemy.exc import SQLAlchemyError

    service = correction_service
    draft = await service.create(payload(), ACTOR)
    sent = await service.mutate(draft["id"], "gui", EmptyInput(), etag(draft), ACTOR)
    stock = await service.repo.stock([17])
    original = service.audit.append

    async def append(entry):
        if entry.thao_tac == "duyet":
            raise SQLAlchemyError("injected audit failure")
        await original(entry)

    monkeypatch.setattr(service.audit, "append", append)
    with pytest.raises(DieuChinhError) as failure:
        await service.approve(sent["id"], etag(sent), ACTOR)
    assert failure.value.extra["ticket_da_luu"] is True
    assert await service.repo.stock([17]) == stock
    assert await service.repo.ledger_ids(sent["id"]) == []


async def test_ticket_outage_spools_failure(correction_service, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    service = correction_service
    draft = await service.create(payload(0), ACTOR)
    sent = await service.mutate(draft["id"], "gui", EmptyInput(), etag(draft), ACTOR)
    stock = await service.repo.stock([17])

    async def unavailable(**params):
        raise SQLAlchemyError("injected ticket outage")

    monkeypatch.setattr(service.repo, "create_ticket", unavailable)
    with pytest.raises(DieuChinhError) as error:
        await service.approve(sent["id"], etag(sent), ACTOR)
    assert error.value.status == 503
    assert error.value.extra == {"ticket_id": None, "ticket_da_luu": False}
    assert len(list(service.incidents.directory.glob("*.json"))) == 1
    assert (await service.get(sent["id"]))["trang_thai"] == "cho_duyet"
    assert await service.repo.stock([17]) == stock
    assert await service.repo.ledger_ids(sent["id"]) == []


async def test_concurrent_approvals_post_exactly_once(bootstrapped_connection, tmp_path):
    import asyncio

    engine = bootstrapped_connection.engine

    def make_service(session):
        return DieuChinhService(
            SqlAlchemyDieuChinhRepository(session),
            AuditService(SqlAlchemyAuditRepository(session)),
            DieuChinhIncidents(tmp_path),
        )

    async with AsyncSession(engine) as session:
        service = make_service(session)
        source = await service.repo.source(1, 1)
        initial = (await service.repo.stock([6]))[6]
        desired = source["so_luong_hieu_luc_truoc"] + 1
        draft = await service.create(
            DieuChinhCreate(
                phieu_nhap_id=1,
                ly_do="Concurrent test",
                chi_tiet=[{"giao_dich_goc_id": 1, "so_luong_dung": desired}],
            ),
            ACTOR,
        )
        sent = await service.mutate(draft["id"], "gui", EmptyInput(), etag(draft), ACTOR)

    async def approve():
        async with AsyncSession(engine) as session:
            return await make_service(session).approve(sent["id"], etag(sent), ACTOR)

    results = await asyncio.gather(approve(), approve())
    assert sorted(result[2] for result in results) == [False, True]
    assert results[0][1] == results[1][1] and len(results[0][1]) == 1
    async with AsyncSession(engine) as session:
        assert (await make_service(session).repo.stock([6]))[6] == initial + 1
