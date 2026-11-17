"""Employee source lookup and preview against real PostgreSQL, without writes."""

from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import (
    create_access_token,
    get_password_hash,
    password_version,
    verify_password,
)
from app.main import app

BASE = "/api/v1/phieu_xuat"


async def test_lookup_empty_existing_completed_and_no_writes(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, goods_issue_pending
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    source = await scenario.source()
    url = f"{BASE}/theo_yeu_cau/{source}"
    assert (await client.get(url, headers=auth())).status_code == 200
    assert (await client.get(url, headers=auth())).json()["data"] == []
    created, _, source = await goods_issue_pending()
    await scenario.sql(
        "UPDATE \"YeuCauSanXuat\" SET trang_thai='hoan_thanh',completed_at=now() WHERE id=:id",
        id=source,
    )
    before = await scenario.snapshot()
    response = await client.get(f"{BASE}/theo_yeu_cau/{source}", headers=auth())
    assert response.status_code == 200, response.text
    assert response.json()["data"] == [
        {
            key: created.json()["data"][key]
            for key in ("id", "ma_phieu_xuat", "loai_phieu", "trang_thai")
        }
        | {"trang_thai": "cho_duyet"}
    ]
    assert await scenario.snapshot() == before


@pytest.mark.parametrize("kind", ["xuat_linh_kien", "xuat_thanh_pham"])
async def test_preview_matches_server_create_without_writing(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, kind
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    source = await scenario.source(production=7 if kind == "xuat_linh_kien" else 0, available=3)
    before = await scenario.snapshot()
    response = await client.get(
        f"{BASE}/xem_truoc/{source}", params={"loai_phieu": kind}, headers=auth()
    )
    assert response.status_code == 200, response.text
    lines = response.json()["data"]["chi_tiet"]
    assert lines and await scenario.snapshot() == before
    created = await client.post(
        BASE, headers=auth(), json={"loai_phieu": kind, "yeu_cau_san_xuat_id": source}
    )
    assert created.status_code == 201, created.text
    assert [
        {key: line[key] for key in ("mat_hang_id", "so_luong")}
        for line in created.json()["data"]["chi_tiet"]
    ] == lines
    assert (
        await client.get(f"{BASE}/xem_truoc/{source}", params={"loai_phieu": kind}, headers=auth())
    ).status_code == 409


async def test_read_permissions_validation_and_changed_source(
    goods_issue_client, goods_issue_auth, goods_issue_scenario
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    source = await scenario.source()
    for suffix in (f"theo_yeu_cau/{source}", f"xem_truoc/{source}?loai_phieu=xuat_linh_kien"):
        url = f"{BASE}/{suffix}"
        assert (await client.get(url)).status_code == 401
        assert (await client.get(url, headers=auth(3))).status_code == 403
        assert (await client.get(url, headers=auth(4))).status_code == 403
    assert (await client.get(f"{BASE}/theo_yeu_cau/{source}", headers=auth(1))).status_code == 200
    assert (
        await client.get(f"{BASE}/xem_truoc/{source}?loai_phieu=xuat_linh_kien", headers=auth(1))
    ).status_code == 403
    for suffix in ("theo_yeu_cau/2147483648", "xem_truoc/2147483648?loai_phieu=xuat_linh_kien"):
        assert (await client.get(f"{BASE}/{suffix}", headers=auth())).status_code == 404
    for suffix in (
        f"theo_yeu_cau/{source}?extra=1",
        f"xem_truoc/{source}?loai_phieu=bad",
        f"xem_truoc/{source}?loai_phieu=xuat_linh_kien&extra=1",
        f"xem_truoc/{source}?loai_phieu=xuat_linh_kien&loai_phieu=xuat_linh_kien",
    ):
        assert (await client.get(f"{BASE}/{suffix}", headers=auth())).status_code == 422
    preview = await client.get(
        f"{BASE}/xem_truoc/{source}?loai_phieu=xuat_linh_kien", headers=auth()
    )
    assert preview.status_code == 200
    await scenario.sql(
        "UPDATE \"YeuCauSanXuat\" SET trang_thai='da_huy',huy_at=now(),nguoi_huy_id=1,ly_do_huy='Test cancellation' WHERE id=:id",
        id=source,
    )
    before = await scenario.snapshot()
    result = await client.post(
        BASE, headers=auth(), json={"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": source}
    )
    assert result.status_code == 409
    assert await scenario.snapshot() == before


async def test_employee_list_my_issues_with_isolation(
    goods_issue_client, goods_issue_auth, goods_issue_scenario
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    source_emp2 = await scenario.source(assigned=2)
    source_emp3 = await scenario.source(assigned=3)

    res_emp2 = await client.post(
        BASE,
        headers=auth(employee_id=2, roles=["nhan_vien"]),
        json={"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": source_emp2},
    )
    assert res_emp2.status_code == 201, res_emp2.text
    issue_emp2_id = res_emp2.json()["data"]["id"]

    res_emp3 = await client.post(
        BASE,
        headers=auth(employee_id=3, roles=["nhan_vien"]),
        json={"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": source_emp3},
    )
    assert res_emp3.status_code == 201, res_emp3.text
    issue_emp3_id = res_emp3.json()["data"]["id"]

    before = await scenario.snapshot()

    # Employee 2 lists own issues
    res2 = await client.get(
        f"{BASE}/cua_toi", headers=auth(employee_id=2, roles=["nhan_vien"])
    )
    assert res2.status_code == 200, res2.text
    emp2_items = res2.json()["data"]
    emp2_ids = [item["id"] for item in emp2_items]
    assert issue_emp2_id in emp2_ids
    assert issue_emp3_id not in emp2_ids

    # Employee 3 lists own issues
    res3 = await client.get(
        f"{BASE}/cua_toi", headers=auth(employee_id=3, roles=["nhan_vien"])
    )
    assert res3.status_code == 200, res3.text
    emp3_items = res3.json()["data"]
    emp3_ids = [item["id"] for item in emp3_items]
    assert issue_emp3_id in emp3_ids
    assert issue_emp2_id not in emp3_ids

    # Filter by yeu_cau_san_xuat_id
    res_filtered = await client.get(
        f"{BASE}/cua_toi",
        headers=auth(employee_id=2, roles=["nhan_vien"]),
        params={"yeu_cau_san_xuat_id": source_emp2},
    )
    assert res_filtered.status_code == 200
    assert len(res_filtered.json()["data"]) == 1
    assert res_filtered.json()["data"][0]["id"] == issue_emp2_id

    # Filter by another employee's source returns empty
    res_empty = await client.get(
        f"{BASE}/cua_toi",
        headers=auth(employee_id=2, roles=["nhan_vien"]),
        params={"yeu_cau_san_xuat_id": source_emp3},
    )
    assert res_empty.status_code == 200
    assert len(res_empty.json()["data"]) == 0

    # Role enforcement: quan_ly and quan_tri_vien get 403
    assert (
        await client.get(f"{BASE}/cua_toi", headers=auth(employee_id=1, roles=["quan_ly"]))
    ).status_code == 403
    assert (
        await client.get(f"{BASE}/cua_toi", headers=auth(employee_id=4, roles=["quan_tri_vien"]))
    ).status_code == 403

    # Forbids nhan_vien_id query parameter
    assert (
        await client.get(
            f"{BASE}/cua_toi",
            headers=auth(employee_id=2, roles=["nhan_vien"]),
            params={"nhan_vien_id": 3},
        )
    ).status_code == 422

    # Snapshot check: listing issues produced no DB writes
    assert await scenario.snapshot() == before


async def test_employee_list_my_completions_with_isolation(
    goods_issue_client, goods_issue_auth, goods_issue_scenario
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    COMP_BASE = "/api/v1/chung_tu_hoan_thanh_sx"

    # Employee 2 owns source_a and source_b; Employee 3 owns source_emp3
    source_emp2_a = await scenario.source(assigned=2)
    source_emp2_b = await scenario.source(assigned=2)
    source_emp3 = await scenario.source(assigned=3)

    # Employee 2 has 2 completions: draft (nhap) and approved (da_duyet)
    comp_draft = await scenario.sql(
        """INSERT INTO "ChungTuHoanThanhSx" (ma_phieu,yeu_cau_san_xuat_id,so_luong_hoan_thanh,nhan_vien_id,trang_thai)
           VALUES ('HTSX-202611-000101',:s,3,2,'nhap') RETURNING id""",
        s=source_emp2_a,
    )
    draft_id = comp_draft[0]["id"]

    comp_app = await scenario.sql(
        """INSERT INTO "ChungTuHoanThanhSx" (ma_phieu,yeu_cau_san_xuat_id,so_luong_hoan_thanh,nhan_vien_id,trang_thai,finish_time,nguoi_xu_ly_id,xu_ly_at)
           VALUES ('HTSX-202611-000102',:s,3,2,'da_duyet',now(),1,now()) RETURNING id""",
        s=source_emp2_b,
    )
    app_id = comp_app[0]["id"]

    # Employee 3 has 1 completion
    comp_emp3 = await scenario.sql(
        """INSERT INTO "ChungTuHoanThanhSx" (ma_phieu,yeu_cau_san_xuat_id,so_luong_hoan_thanh,nhan_vien_id,trang_thai,finish_time,nguoi_xu_ly_id,xu_ly_at)
           VALUES ('HTSX-202611-000103',:s,2,3,'da_duyet',now(),1,now()) RETURNING id""",
        s=source_emp3,
    )
    emp3_id = comp_emp3[0]["id"]

    before = await scenario.snapshot()

    # Employee 2 lists own completions: sees draft and approved for source_emp2, NOT emp3's
    res2 = await client.get(
        f"{COMP_BASE}/cua_toi", headers=auth(employee_id=2, roles=["nhan_vien"])
    )
    assert res2.status_code == 200, res2.text
    emp2_comp_ids = [c["id"] for c in res2.json()["data"]]
    assert draft_id in emp2_comp_ids
    assert app_id in emp2_comp_ids
    assert emp3_id not in emp2_comp_ids

    # Employee 3 lists own completions: sees only own completion
    res3 = await client.get(
        f"{COMP_BASE}/cua_toi", headers=auth(employee_id=3, roles=["nhan_vien"])
    )
    assert res3.status_code == 200, res3.text
    emp3_comp_ids = [c["id"] for c in res3.json()["data"]]
    assert emp3_id in emp3_comp_ids
    assert draft_id not in emp3_comp_ids
    assert app_id not in emp3_comp_ids

    # Filter by draft status
    res_draft = await client.get(
        f"{COMP_BASE}/cua_toi",
        headers=auth(employee_id=2, roles=["nhan_vien"]),
        params={"trang_thai": "nhap"},
    )
    assert res_draft.status_code == 200
    assert len(res_draft.json()["data"]) == 1
    assert res_draft.json()["data"][0]["id"] == draft_id

    # Manager list excludes draft
    res_mgr = await client.get(COMP_BASE, headers=auth(employee_id=1, roles=["quan_ly"]))
    assert res_mgr.status_code == 200
    mgr_ids = [c["id"] for c in res_mgr.json()["data"]]
    assert draft_id not in mgr_ids
    assert app_id in mgr_ids

    # Role enforcement: quan_ly and quan_tri_vien get 403 on cua_toi
    assert (
        await client.get(f"{COMP_BASE}/cua_toi", headers=auth(employee_id=1, roles=["quan_ly"]))
    ).status_code == 403
    assert (
        await client.get(f"{COMP_BASE}/cua_toi", headers=auth(employee_id=4, roles=["quan_tri_vien"]))
    ).status_code == 403

    # Query validation rejects forbidden q, nhan_vien_id, date.max and non-positive IDs
    for bad_params in (
        {"q": "anything"},
        {"nhan_vien_id": 2},
        {"den_ngay": "9999-12-31"},
        {"mat_hang_id": 0},
        {"mat_hang_id": -1},
    ):
        res_bad = await client.get(
            f"{COMP_BASE}/cua_toi",
            headers=auth(employee_id=2, roles=["nhan_vien"]),
            params=bad_params,
        )
        assert res_bad.status_code == 422

    # Oversized ID returns 200 with empty data (consistent with main)
    res_oversized = await client.get(
        f"{COMP_BASE}/cua_toi",
        headers=auth(employee_id=2, roles=["nhan_vien"]),
        params={"mat_hang_id": 2147483648},
    )
    assert res_oversized.status_code == 200
    assert res_oversized.json()["data"] == []

    # Snapshot check: listing completions produced no DB writes
    assert await scenario.snapshot() == before


async def test_employee_change_password_self_pg_transaction_and_invalidation(
    goods_issue_client, goods_issue_scenario
):
    client, scenario = goods_issue_client, goods_issue_scenario
    PWD_URL = "/api/v1/nhan_vien/me/doi_mat_khau"

    # Set up employee 2 with a known Argon2id hash
    old_hash = get_password_hash("OldPassword123")
    await scenario.sql(
        'UPDATE "NhanVien" SET mat_khau=:h, phien_ban_dang_nhap=0 WHERE id=2',
        h=old_hash,
    )

    # Issue two distinct valid sessions for employee 2
    token_a = create_access_token(
        2, ["nhan_vien"], credential_version=password_version(old_hash), session_version=0,
        expires_delta=timedelta(minutes=30),
    )
    token_b = create_access_token(
        2, ["nhan_vien"], credential_version=password_version(old_hash), session_version=0,
        expires_delta=timedelta(minutes=60),
    )
    assert token_a != token_b

    # Both tokens are initially valid
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})).status_code == 200
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})).status_code == 200

    # 1. Wrong current password -> 400 mat_khau_hien_tai_khong_dung, session intact, no audit
    res_wrong = await client.post(
        PWD_URL,
        headers={"Authorization": f"Bearer {token_a}"},
        json={"mat_khau_hien_tai": "WrongPass123", "mat_khau_moi": "NewPassword456"},
    )
    assert res_wrong.status_code == 400, res_wrong.text
    assert res_wrong.json()["error"]["code"] == "mat_khau_hien_tai_khong_dung"

    # Both sessions still valid after wrong password attempt
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})).status_code == 200
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})).status_code == 200

    # DB unchanged
    current_hash = await scenario.scalar('SELECT mat_khau FROM "NhanVien" WHERE id=2')
    assert current_hash == old_hash
    pbdn = await scenario.scalar('SELECT phien_ban_dang_nhap FROM "NhanVien" WHERE id=2')
    assert pbdn == 0
    audits = await scenario.sql(
        'SELECT * FROM "LichSuThaoTac" WHERE nhan_vien_id=2 AND thao_tac=\'doi_mat_khau\''
    )
    assert len(audits) == 0

    # 2. Correct current password -> 204 No Content
    res_ok = await client.post(
        PWD_URL,
        headers={"Authorization": f"Bearer {token_a}"},
        json={"mat_khau_hien_tai": "OldPassword123", "mat_khau_moi": "NewPassword456"},
    )
    assert res_ok.status_code == 204

    # BOTH old sessions are now invalidated (401 Unauthorized)
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})).status_code == 401
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})).status_code == 401

    # DB verified: phien_ban_dang_nhap incremented, password updated
    new_pbdn = await scenario.scalar('SELECT phien_ban_dang_nhap FROM "NhanVien" WHERE id=2')
    assert new_pbdn == 1
    new_hash = await scenario.scalar('SELECT mat_khau FROM "NhanVien" WHERE id=2')
    assert new_hash != old_hash
    assert verify_password("NewPassword456", new_hash) is True

    # Audit verified: sanitized, no password leaked
    audits_after = await scenario.sql(
        'SELECT * FROM "LichSuThaoTac" WHERE nhan_vien_id=2 AND thao_tac=\'doi_mat_khau\''
    )
    assert len(audits_after) == 1
    assert audits_after[0]["du_lieu_sau"] == {"da_doi_mat_khau": True}
    assert audits_after[0]["du_lieu_truoc"] is None

    # Assert old-password login fails
    old_login_res = await client.post(
        "/api/v1/auth/dang_nhap",
        json={"ten_dang_nhap": "fixture2", "mat_khau": "OldPassword123"},
    )
    assert old_login_res.status_code == 401
    assert old_login_res.json()["error"]["code"] == "thong_tin_dang_nhap_khong_hop_le"

    # Login with new password succeeds and returns fresh token
    login_res = await client.post(
        "/api/v1/auth/dang_nhap",
        json={"ten_dang_nhap": "fixture2", "mat_khau": "NewPassword456"},
    )
    assert login_res.status_code == 200
    fresh_token = login_res.json()["data"]["access_token"]
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {fresh_token}"})).status_code == 200

    # Non-employee roles forbidden
    admin_token = create_access_token(
        4, ["quan_tri_vien"], credential_version=password_version("fixture-hash"), session_version=0
    )
    res_admin = await client.post(
        PWD_URL,
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"mat_khau_hien_tai": "anything", "mat_khau_moi": "NewPassword789"},
    )
    assert res_admin.status_code == 403


async def test_employee_change_password_audit_failure_rollback(
    goods_issue_client, goods_issue_scenario
):
    client, scenario = goods_issue_client, goods_issue_scenario
    PWD_URL = "/api/v1/nhan_vien/me/doi_mat_khau"

    old_hash = get_password_hash("OldPassword123")
    await scenario.sql(
        'UPDATE "NhanVien" SET mat_khau=:h, phien_ban_dang_nhap=0 WHERE id=2',
        h=old_hash,
    )
    token = create_access_token(
        2, ["nhan_vien"], credential_version=password_version(old_hash), session_version=0
    )
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})).status_code == 200

    # Install trigger that fails audit insertion for doi_mat_khau
    await scenario.sql("""
        CREATE OR REPLACE FUNCTION fail_audit() RETURNS trigger AS $$
        BEGIN
            IF NEW.thao_tac = 'doi_mat_khau' THEN
                RAISE EXCEPTION 'Simulated audit write failure';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    await scenario.sql("""
        CREATE TRIGGER trg_test_fail_audit BEFORE INSERT ON "LichSuThaoTac"
        FOR EACH ROW EXECUTE FUNCTION fail_audit();
    """)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as no_raise_client:
            res = await no_raise_client.post(
                PWD_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={"mat_khau_hien_tai": "OldPassword123", "mat_khau_moi": "NewPassword456"},
            )
            assert res.status_code == 500

        # Verify rollback: password hash and pbdn unchanged
        current_hash = await scenario.scalar('SELECT mat_khau FROM "NhanVien" WHERE id=2')
        assert current_hash == old_hash
        pbdn = await scenario.scalar('SELECT phien_ban_dang_nhap FROM "NhanVien" WHERE id=2')
        assert pbdn == 0

        # No audit entry written
        audits = await scenario.sql('SELECT * FROM "LichSuThaoTac" WHERE nhan_vien_id=2 AND thao_tac=\'doi_mat_khau\'')
        assert len(audits) == 0

        # Existing session remains valid
        assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})).status_code == 200

        # Old password login still works
        login_res = await client.post(
            "/api/v1/auth/dang_nhap",
            json={"ten_dang_nhap": "fixture2", "mat_khau": "OldPassword123"},
        )
        assert login_res.status_code == 200
    finally:
        await scenario.sql('DROP TRIGGER IF EXISTS trg_test_fail_audit ON "LichSuThaoTac"')
        await scenario.sql('DROP FUNCTION IF EXISTS fail_audit()')
