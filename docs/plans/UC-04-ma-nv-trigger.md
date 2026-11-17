# Plan bổ sung UC-04 — Cấp mã nhân viên bằng trigger từ `id`

> Lập 15/11/2026 sau phản hồi review PR #11. Dev đồng ý 15/11/2026: dùng trigger `cap_ma_nhan_vien()` giống MH-/NCC- (quyết định #12), không dùng cột `GENERATED ALWAYS`. Spec: [UC-04](../../specs/use_cases/identity_access/UC-04.md) R6, A4. Plan gốc: [UC-04](UC-04.md) D1.
> Người thực thi: Codex (`codex exec -s workspace-write`). Claude kiểm chứng trước khi commit/push vào PR #11.

## Goal

Bỏ cấp mã `max + 1` ở tầng ứng dụng (UC-04 D1). PostgreSQL tự cấp `ma_nhan_vien = 'NV-' || lpad(id, 6, '0')` trong trigger BEFORE INSERT, báo lỗi rõ khi `id > 999999` và cấm sửa mã. Hai QTV tạo tài khoản cùng lúc không còn trùng mã. AC UC-04 giữ nguyên và vẫn pass.

## Lý do chọn trigger (thay vì cột generated)

- Thống nhất với `cap_ma_mat_hang()`, `cap_ma_nha_cung_cap()` trong `init.sql`.
- `lpad` cắt chuỗi khi `id` có 7 chữ số (`lpad('1000000', 6, '0') = '100000'`); trigger kiểm `id > 999999` và báo "Hết dải mã nhân viên NV-NNNNNN" thay vì sinh mã sai.
- Trigger chặn được việc sửa mã sau khi tạo.

## Thay đổi

| File | Thay đổi |
|---|---|
| `specs/entity_model/data_model_v4.md` | Thêm quyết định #17 (15/11/2026): `ma_nhan_vien` do trigger cấp từ `id` (`NV-` + 6 chữ số), không sửa được, giống #12; thay cho cấp `max + 1` ở ứng dụng. Ghi chú ERD `NhanVien.ma_nhan_vien`: "he thong cap tu id". |
| `specs/entity_model/entity_model.md` | Mục `NhanVien`: `ma_nhan_vien (NV-xxxxxx, duy nhất, hệ thống cấp từ id khi tạo, không sửa)`. |
| `infra/postgres/init.sql` | Thêm `cap_ma_nhan_vien()` + `trg_nhan_vien_ma BEFORE INSERT OR UPDATE ON "NhanVien"` đặt cạnh hai trigger MH/NCC, cùng khuôn: INSERT — `id > 999999` → `RAISE EXCEPTION 'Hết dải mã nhân viên NV-NNNNNN'`, gán mã; UPDATE — đổi `id` hoặc `ma_nhan_vien` → `RAISE EXCEPTION 'Không được sửa mã nhân viên'`. Sửa `COMMENT ON COLUMN "NhanVien"."ma_nhan_vien"` cho đúng. Không đổi cột, CHECK, unique. |
| `infra/postgres/seed.sql` | Bỏ cột `ma_nhan_vien` khỏi `INSERT INTO "NhanVien"` (trigger cấp `NV-000001`… từ `id` 1–4, trùng giá trị cũ); thêm comment như phần catalog. Không đổi dữ liệu khác. |
| `backend/app/modules/nhan_vien/models.py` | `ma_nhan_vien` có `server_default=FetchedValue()` (giá trị do DB sinh, ORM không gửi khi INSERT). |
| `backend/app/modules/nhan_vien/schemas.py` | `NewEmployee` bỏ `ma_nhan_vien`. |
| `backend/app/modules/nhan_vien/ports.py` | Bỏ `next_employee_code`. |
| `backend/app/modules/nhan_vien/repository.py` | Bỏ `next_employee_code`; `create()` không truyền mã, sau `flush` + `refresh` đọc mã DB sinh; bắt `DBAPIError` có `sqlstate == "P0001"` và thông điệp chứa `NV-NNNNNN` → `InvalidWorkflowState("Đã hết mã nhân viên khả dụng")` (khuôn `mat_hang` ở nhánh `feature/catalog`); bỏ nhánh "trùng mã vừa được cấp". Giữ nhánh trùng `ten_dang_nhap`. |
| `backend/app/modules/nhan_vien/service.py` | `create_employee` bỏ bước `next_employee_code`; giữ thứ tự `_lock_admin` → `_role` → kiểm tra trùng tên → `create` → `_audit`. Cập nhật comment UC-04 cho đúng (Main 5, R6: DB cấp mã). |
| `backend/tests/test_nhan_vien_create_code.py` | Viết lại các test R6 theo cơ chế mới: không có `ma_nhan_vien` trong dữ liệu insert; response và lịch sử dùng mã repository trả về; hết dải (repository ném `InvalidWorkflowState`) → 409, rollback, không lịch sử; gửi kèm `ma_nhan_vien` → 422 (giữ). Bỏ test `max + 1` và test trùng mã đồng thời. Giữ `test_can_create_second_admin`. |
| `backend/tests/test_uc04_them_tai_khoan.py` | Chỉ sửa chỗ phụ thuộc `next_employee_code` / mapping trùng mã; giữ mọi assert AC. |
| `backend/tests/test_nhan_vien_code_trigger_postgres.py` (mới) | Test PostgreSQL thật, cùng khuôn an toàn của `test_audit_postgres.py` (biến môi trường riêng, chỉ DB `*_test` cục bộ, tạo/xóa DB UUID, bootstrap từ `init.sql`; thiếu biến → skip): chèn hai `NhanVien` không có mã → `NV-` + id; `UPDATE` đổi mã → lỗi; chèn `id = 1000000` → lỗi "Hết dải". |
| `docs/sequence/nhan_vien.md` | Mục `POST /api/v1/nhan_vien`: mã do trigger DB cấp từ `id`; bỏ bước `max(...)`; 409 hết dải. |
| `specs/use_cases/identity_access/UC-04.md` | R6 nguồn: "Quyết định dev 15/11/2026 (trigger cấp từ id, data model #17)". |
| `docs/plans/UC-04.md` | Không sửa nội dung cũ; plan này ghi kết quả riêng. |

## Quy ước comment

Giữ comment UC-04 ở `create_entry`, `create_employee`, `create`; sửa nội dung cho đúng cơ chế mới. Không thêm comment UC ở hàm khác. Test: `# UC-04 R6: ...` / `# UC-04 A4: ...` / `# UC-04 AC-n: ...` ngay trên hàm test (trên decorator).

## Ràng buộc cho Codex

- Không commit/push, không migration, không động DB/Docker/volume đang chạy, không seed lại DB. Sửa `init.sql`/`seed.sql` chỉ là bootstrap cho DB mới/trống (AGENTS.md §6).
- Không đổi dependency/lockfile. Không đụng `frontend/`.
- Python: `backend/.venv/Scripts/python`.

## Kiểm chứng

```bash
cd backend && .venv/Scripts/python -m pytest -q -p no:cacheprovider tests/test_nhan_vien_create_code.py tests/test_uc04_them_tai_khoan.py tests/test_nhan_vien_code_trigger_postgres.py
cd backend && .venv/Scripts/python -m pytest -q -p no:cacheprovider
cd backend && .venv/Scripts/python -m ruff check app tests
```

Đạt khi: test UC-04 pass (test PostgreSQL được phép skip nếu không có DB test); backend không lỗi mới so với 326 pass / 22 skip / 0 fail (số skip tăng thêm đúng số test PostgreSQL mới); ruff sạch.

Commit: `feat(UC-04): cấp mã nhân viên bằng trigger từ id thay cho max+1`, push `origin identity_access` (vào PR #11).

## Kết quả

Thực thi 15/11/2026 bằng Codex, Claude kiểm chứng lại diff và tự chạy toàn bộ lệnh. Chỉnh sau kiểm chứng: khôi phục comment UC-04 ở `find_by_username` (A3), `_lock_admin` (A6), `_audit` (R5) — Codex đã gỡ do plan chỉ liệt kê ba hàm cần giữ.

File đã sửa: `infra/postgres/{init,seed}.sql`, `backend/app/modules/nhan_vien/{models,schemas,ports,repository,service}.py`, `backend/tests/{test_nhan_vien_create_code,test_uc04_them_tai_khoan}.py`, `specs/entity_model/{data_model_v4,entity_model}.md` (quyết định #17), spec UC-04 (nguồn R6), `docs/sequence/nhan_vien.md`. File mới: `backend/tests/test_nhan_vien_code_trigger_postgres.py`.

| Lệnh | Kết quả |
|---|---|
| `pytest` 3 file UC-04 | 42 pass, 4 skip (PostgreSQL) |
| `pytest` toàn backend | 328 pass, 26 skip, 0 fail |
| `ruff check app tests` | Đạt |
| `npm test` (không đổi FE trong bước này) | 139 pass |

| Mục | Test | Kết quả |
|---|---|---|
| R6 – không gửi mã khi INSERT, dùng mã DB trả về | `test_nhan_vien_create_code.py` | Đạt |
| R6 – hết dải (P0001 `NV-NNNNNN`) → 409, rollback, không lịch sử | `test_nhan_vien_create_code.py` | Đạt |
| A4 – gửi kèm `ma_nhan_vien` → 422 | `test_nhan_vien_create_code.py` | Đạt |
| AC-1 – AC-5 UC-04 | `test_uc04_them_tai_khoan.py` | Đạt |
| Trigger: mã = `NV-` + id, cấm sửa mã/id, `id = 1000000` báo hết dải | `test_nhan_vien_code_trigger_postgres.py` | **Skip** — cần `NHAN_VIEN_CODE_TEST_DATABASE_URL` trỏ tới DB `*_test` cục bộ |

Giới hạn ở lần kiểm chứng trên: trigger chưa chạy trên PostgreSQL thật; đã được
kiểm chứng bổ sung bên dưới. `init.sql`/`seed.sql` chỉ áp dụng cho DB mới/trống;
volume đang chạy không tự cập nhật (AGENTS.md §6).

## Kiểm chứng bổ sung UC-04 trên PostgreSQL thật — 15/11/2026

### Khảo sát và phạm vi

Checkout `identity_access`, HEAD `7fd30f3`, sạch trước tác vụ. Trigger, FetchedValue,
mapping P0001, seed và việc bỏ next_employee_code đã có trong commit này, đúng quyết
định #17 và yêu cầu dev; không viết lại hoặc thay nghiệp vụ đã chạy đúng.
Baseline trước bổ sung: 42 test service/API hiện có pass; 4 test trigger hiện có
cũng đã chạy thật và pass trên PostgreSQL riêng.

Phần bổ sung theo yêu cầu dev làm UC-04 trước rồi test:

| Task | File / kết quả | UC / AC |
|---|---|---|
| T1 | `test_nhan_vien_code_trigger_postgres.py`: tách fixture DB đã bootstrap nhưng còn trống để kiểm seed; không dùng DB ứng dụng | UC-04 R6 |
| T2 | Thêm test API với auth/JWT, service, repository, ORM, audit và transaction thật; chỉ override get_db sang UUID DB | AC-1/2/5/6 |
| T3 | Hai QTV/hai backend PID, barrier sau precheck: tên khác cả hai 201/mã khác; cùng tên chỉ một 201, bên kia 409 đúng lỗi | AC-3/7 |
| T4 | Identity 999999/1000000 qua HTTP; failure injection sau append và sau flush trước commit, rollback cả account/audit và không reuse mã đã tiêu thụ | AC-5/8, A7 |
| T5 | Kiểm seed trên UUID DB mới/trống: mã id 1–4 đúng, INSERT tiếp theo nhận NV-000005; chạy toàn backend, Ruff | R6, AC-6 |
| T6 | Spec UC-04 bổ sung AC-6–AC-9 và truy vết; sequence UC-04 render PNG; sửa comment cũ còn nói hai QTV có thể trùng mã | AC-6–AC-9 |

Không đổi logic runtime, API hoặc DDL đã có. File runtime duy nhất sửa trong lượt
này là comment `_lock_admin` tại `nhan_vien/service.py`, bỏ mô tả max+1 đã lỗi thời.
Không đổi UC-01/02/03/05–08, audit/dashboard, frontend, dependency, config hay migration.

### Môi trường và lệnh thực chạy

- Container test riêng `xbike-uc04-test-20261115`, PostgreSQL **16-alpine**, user
  `uc04_test`, cổng **127.0.0.1:55467**, data tmpfs, không mount volume ứng dụng.
- `NHAN_VIEN_CODE_TEST_DATABASE_URL` trỏ DB khởi điểm `xbike_uc04_test`. Fixture
  chỉ chấp nhận user uc04_test/local/*_test, tạo DB `uc04_<uuid>_test`, kiểm trống,
  bootstrap bằng init.sql thật; đóng engine/connection rồi drop đúng UUID DB đã tạo.
- Test seed chỉ chạy trên UUID DB trống vừa bootstrap; không seed DB ứng dụng.
- ASGI app test riêng không lifespan/cache/traffic recorder; get_db dùng session
  test, cùng session cho account và audit. Không mock auth/service/repository của
  luồng thành công. Barrier/failure injection chỉ phục vụ cạnh tranh/rollback.

```powershell
# Tại backend, cấu hình NHAN_VIEN_CODE_TEST_DATABASE_URL cho server test riêng trước.
..\.venv\Scripts\python.exe -m pytest tests/test_nhan_vien_code_trigger_postgres.py -q -p no:cacheprovider --tb=short
..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short --junitxml=../.venv/uc04-20261115-result.xml
..\.venv\Scripts\python.exe -m ruff check app tests
..\.venv\Scripts\ruff.exe format --check app/modules/nhan_vien/service.py tests/test_nhan_vien_code_trigger_postgres.py
```

| Kiểm tra thực tế | Kết quả |
|---|---|
| PostgreSQL UC-04 | **14 pass, 0 skip**, 3.89s; gồm 4 case có sẵn + 10 case bổ sung |
| Nhóm UC-04 trong lần chạy toàn suite | **56 pass**: create_code 11, them_tai_khoan 31, PostgreSQL 14 |
| Toàn backend | **342 pass, 22 skip, 0 fail**, 13.41s |
| 22 skip | Chỉ `test_audit_postgres.py`, thiếu AUDIT_TEST_DATABASE_URL; chưa nghiệm thu PostgreSQL UC-43 trong lượt UC-04 |
| Ruff check app tests | Pass |
| Ruff format --check hai file Python thay đổi | Pass |
| Sequence UC-04 | Mermaid render thành PNG, kiểm hình; [ảnh](../sequence/assets/nhan_vien/uc04-tao-tai-khoan.png) |
| Kiến trúc | Đối chiếu layer/import và structure map; chưa có architecture declaration nên boundary checker không kết luận tự động; không refactor các cảnh báo code có sẵn |
| Kiểm tra cuối | git diff --check pass; 23 liên kết file hợp lệ, UTF-8/PNG hợp lệ; AST service không đổi (chỉ sửa comment) |
| Cleanup | Không còn UUID DB uc04 sau fixture; xác minh ID/nhãn/tmpfs/cổng rồi dừng container test 5d863a262560. Container ứng dụng 484c7efeb50c vẫn chạy cổng 5432 |

### Truy vết test PostgreSQL

Owner HTTP/service: `POST /api/v1/nhan_vien → NhanVienService.create_employee`.
Spec: [UC-04](../../specs/use_cases/identity_access/UC-04.md).
File test: [test_nhan_vien_code_trigger_postgres.py](../../backend/tests/test_nhan_vien_code_trigger_postgres.py).

| AC / quy tắc | Test thực tế | Kết quả |
|---|---|---|
| AC-1/2/5/6 | `test_api_returns_database_code_and_account_can_login` × 3 vai trò | Đạt backend: 201, Location/ETag, mã DB/audit khớp, đăng nhập được, không lộ mật khẩu |
| AC-6 | `test_insert_without_code_uses_identity`, `test_trigger_overrides_supplied_code` | Đạt |
| AC-7/AC-3 | `test_two_administrators_create_concurrently` × tên khác/cùng tên | Đạt với hai PostgreSQL connection thực, không dựa vào sleep |
| AC-8 | `test_insert_rejects_exhausted_code_range`, `test_api_identity_exhaustion_rolls_back` | Đạt: 999999 hợp lệ, mặc định identity 1000000 -> P0001 -> 409, không ghi account/audit mới |
| AC-5/8, A7 | `test_create_and_audit_roll_back_together` × audit/commit | Đạt; rollback thật, retry id 3/NV-000003 sau khi id 2 đã tiêu thụ |
| AC-9 | `test_update_cannot_change_code_or_identity` × id/mã | Đạt; hồ sơ vẫn sửa được |
| R6 / bootstrap | `test_fresh_bootstrap_seed_preserves_employee_codes` | Đạt seed trên DB trống, sequence tiếp tục từ 5 |

AC-4 và các nhánh validation/phân quyền còn lại được kiểm bằng bộ service/API đã
có trong lần chạy toàn suite; không xóa, skip hoặc làm yếu các assertion cũ.

### Giới hạn và vận hành

- Không sửa DB ứng dụng, không migration, không reset/xóa volume hoặc seed lại.
  DB đã tồn tại vẫn cần dev chọn phương án cập nhật riêng trước khi dùng trigger;
  không hiểu việc kiểm chứng bootstrap test là đã nâng DB đang chạy.
- Không Playwright/giao diện hoặc frontend/dashboard audit trong bước UC-04.
- Commit failure được kiểm bằng injection sau flush, không giả định đã kiểm mất
  điện/mất kết nối PostgreSQL thật. Các UC khác chỉ chạy regression, không đổi nghiệp vụ.
- Chỉ thêm test/tài liệu và sửa comment; không commit/push.
- Rollback lượt bổ sung này chỉ cần dev hoàn tác đúng test/tài liệu/comment nếu
  muốn; không có migration down hoặc thay đổi dữ liệu cần hoàn tác. Không tự gỡ
  trigger ở database đã có tài khoản hoặc reset identity để lấp khoảng trống.
