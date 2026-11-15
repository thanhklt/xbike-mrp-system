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

Giới hạn: trigger chưa chạy trên PostgreSQL thật. `init.sql`/`seed.sql` chỉ áp dụng cho DB mới/trống; volume đang chạy không tự cập nhật (AGENTS.md §6).
