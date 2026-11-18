# Plan: UC-13 — Lọc tỉnh/phường nhà cung cấp theo một phần chuỗi

> Lập ngày 17/11/2026. **Dev đã duyệt 17/11/2026** qua ảnh chụp trước/sau (ô Tỉnh / thành và Phường / xã) và yêu cầu "tạo plan rồi gọi Codex sửa". Spec: [UC-13](../../specs/use_cases/catalog/UC-13.md).
> Người thực thi: Codex (`codex exec -s workspace-write`) trên nhánh `ui/admin`. Claude kiểm chứng trước khi báo dev.

## Goal

Ở trang tra cứu nhà cung cấp (QLK `/kho/nha-cung-cap`, QTV `/admin/nha-cung-cap`), ô **Tỉnh / thành** và **Phường / xã** tìm được khi người dùng gõ **một phần** tên. Ví dụ "Hồ Chí Minh" khớp "Thành phố Hồ Chí Minh", "Minh Họa" khớp "Phường Minh Họa" và "Phường Minh Họa Hai". Không phân biệt hoa/thường, vẫn giữ dấu, giống ô Tìm kiếm (`q`).

## Context read

- Spec UC-13: R2 (tiêu chí mã/tên, tỉnh, phường), R3 (lọc theo hai trường tỉnh, phường), AC-1 (kết hợp tỉnh và phường), AC-4 (AND filters, phân trang ổn định), A1 (không thỏa → danh sách trống). Spec không bắt so bằng; quy tắc so bằng đến từ Q3 ở `specs/use_cases/catalog/README.md:245` và `specs/use_cases/catalog/PLAN.md:128`.
- `data_model_v4.md:327`: `dia_chi`, `phuong`, `tinh` là văn bản nhập tay, lọc UC-13 theo giá trị `tinh`, `phuong` — không đổi.
- Backend: `backend/app/modules/nha_cung_cap/repository.py` `list_suppliers` — `q` dùng `icontains(..., autoescape=True)`; `tinh`/`phuong` dùng `func.lower(func.btrim(col, ws)) == value.lower()` (so bằng). `schemas.py` `NhaCungCapListQuery` đã strip input, chuỗi trống → `None`.
- Frontend: `components/Collection.jsx` gửi `tinh`/`phuong` khi bấm "Lọc"; không cần đổi.
- Test: `backend/tests/test_catalog_postgres.py` `test_uc13_cat_ac03_literal_address_and_stable_pages` (dòng ~334) và `test_uc44_ac01_ac04_ac06_new_address_filters_and_audit` (dòng ~508) — cần `TEST_DATABASE_URL`, local hiện skip.
- Tài liệu: `docs/sequence/nha_cung_cap.md:17` ghi "tinh/phuong so bằng".

## Hiện trạng so với UC

| Mục | Hiện trạng | Việc cần làm |
|---|---|---|
| R2/R3, AC-1: lọc tỉnh, phường | So bằng toàn chuỗi sau trim + lower → gõ một phần ra 0 kết quả | Đổi sang chứa chuỗi con, không phân biệt hoa/thường (D1) |
| AC-4: AND, phân trang ổn định | Đúng | Giữ nguyên; COUNT và trang dùng chung `query` |
| A1: không thỏa → [] | Đúng | Giữ nguyên |

## Quyết định (đã chốt)

| # | Điểm | Chốt |
|---|---|---|
| D1 | Cách so `tinh`/`phuong` | `NhaCungCap.tinh.icontains(params.tinh, autoescape=True)` và tương tự cho `phuong`: chuỗi con literal, không phân biệt hoa/thường, giữ dấu, `%`/`_` không phải wildcard — đồng nhất với `q`. Bỏ `func.lower(func.btrim(...)) ==`. Không sửa giá trị lưu/response. |
| D2 | Bỏ dấu ("ho chi minh" khớp "Hồ Chí Minh") | **Không làm** — cần extension `unaccent` trong `init.sql`, ngoài phạm vi. |
| D3 | Frontend | Không đổi. |
| D4 | Cập nhật quy tắc Q3 | Sửa câu tỉnh/phường ở `specs/use_cases/catalog/README.md` Q3, `specs/use_cases/catalog/PLAN.md:128`, `docs/sequence/nha_cung_cap.md:17` thành "chứa chuỗi con, không phân biệt hoa/thường, giữ dấu, `%`/`_` literal". |

## Quy ước comment UC

- Hàm được comment: **chỉ** `SqlAlchemySupplierRepository.list_suppliers` — thêm ngay trên `async def`:
  `# UC-13 Tra cứu nhà cung cấp — Main 3–4; R2, R3, A1 (specs/use_cases/catalog/UC-13.md)`. Không thêm comment UC vào hàm khác.
- Test: comment ngay trên hàm test `# UC-13 AC-n: <tên AC>` hoặc `# UC-13 A1: <tên luồng>`.

## Backend

| File | Thay đổi |
|---|---|
| `backend/app/modules/nha_cung_cap/repository.py` | `list_suppliers`: hai nhánh `tinh`/`phuong` dùng `icontains(..., autoescape=True)` (D1); thêm comment UC. Không đổi gì khác. |
| `backend/tests/test_uc13_loc_dia_chi_mot_phan.py` (mới) | Test không cần DB (xem bảng test). |
| `backend/tests/test_catalog_postgres.py` | Cập nhật 2 test postgres nêu trên theo nghĩa mới (xem bảng test). Không làm yếu các assert khác. |

## Frontend

Không đổi.

## Tài liệu

`specs/use_cases/catalog/README.md` (Q3), `specs/use_cases/catalog/PLAN.md:128`, `docs/sequence/nha_cung_cap.md:17` — theo D4, chỉ sửa câu về tỉnh/phường.

## Test ↔ AC

| AC / luồng | Test | Assert |
|---|---|---|
| UC-13 AC-1 (không DB) | `test_uc13_loc_dia_chi_mot_phan.py`: dựng `SqlAlchemySupplierRepository` với session giả ghi lại statement truyền vào `scalar`/`scalars`, gọi `list_suppliers(NhaCungCapListQuery(tinh="Hồ Chí Minh", phuong="Minh Họa"))`, compile statement với dialect `postgresql` | SQL chứa `ILIKE` cho cả cột `tinh` và `phuong`; không còn `btrim`/so `=` trên hai cột; tham số bind là `%Hồ Chí Minh%` / `%Minh Họa%` (đúng dấu) |
| UC-13 AC-4 (không DB) | cùng file: `tinh="50%_x"` | Bind đã escape `%`/`_` (literal, như `q`) |
| UC-13 AC-1 (postgres) | sửa `test_uc13_cat_ac03_literal_address_and_stable_pages` | Thêm: `tinh="nội"` khớp 2 NCC "Hà Nội"/"HÀ NỘI" (không khớp "Ha Noi" — giữ dấu); `phuong="phường"` (một phần) vẫn ra đúng tập; giữ các assert phân trang hiện có |
| UC-13 A1 (postgres) | cùng test | Giá trị không là chuỗi con của NCC nào → `data == []`, `total == 0` |
| UC-44 AC-1 lọc theo địa chỉ mới | sửa `test_uc44_ac01_ac04_ac06_new_address_filters_and_audit` | Lọc bằng một phần địa chỉ mới (vd. `tinh="province"`, `phuong="ward"`) vẫn ra 1; địa chỉ cũ (`SUPPLIER["tinh"]`) phải ra `[]` — kiểm tra lại giá trị mới/cũ không là chuỗi con của nhau, nếu có thì chọn giá trị khác để giữ nguyên ý test |

## Ràng buộc cho Codex

- Không commit, không push, không migration, không động DB/Docker/seed, không đổi dependency/lockfile.
- Chỉ sửa các file liệt kê ở trên. Buộc phải sửa file khác thì dừng và báo lý do.
- Không sửa test fail sẵn ngoài phạm vi.
- Chỉ chạy test liên quan, **không chạy toàn bộ test suite**, không đọc skill hay file ngoài danh sách.

## Lệnh kiểm chứng

```bash
cd backend && .venv/Scripts/python -m pytest -q -p no:cacheprovider tests/test_uc13_loc_dia_chi_mot_phan.py tests/test_catalog_postgres.py tests/test_catalog_service.py tests/test_catalog_api.py
cd backend && .venv/Scripts/python -m ruff check app/modules/nha_cung_cap/repository.py tests/test_uc13_loc_dia_chi_mot_phan.py tests/test_catalog_postgres.py
cd backend && .venv/Scripts/python -m ruff format --check app/modules/nha_cung_cap/repository.py tests/test_uc13_loc_dia_chi_mot_phan.py tests/test_catalog_postgres.py
```

Baseline (17/11/2026, nhánh `ui/admin` `11476ac`): 3 file catalog → 59 pass, 92 skip (PostgreSQL), 0 fail.

## Điều kiện đạt

- Test mới pass 100%; 3 file catalog không có lỗi mới so với baseline; ruff sạch trên file đã sửa.
- Test postgres skip ở local (không có `TEST_DATABASE_URL`) — ghi rõ trong Kết quả, dev chạy khi có DB.

## Commit dự kiến

`fix(UC-13): lọc tỉnh/phường nhà cung cấp theo một phần chuỗi` — chỉ commit khi dev yêu cầu.

## Ngoài phạm vi

Bỏ dấu (D2); đổi giao diện; lọc của các trang khác.

## Kết quả

Thực thi 17/11/2026 qua hai lượt Codex. Dev dừng lượt 1 giữa chừng, rồi yêu cầu lượt 2 sửa test, chạy xong thì xóa file test mới. Claude kiểm chứng lại.

**File đã sửa:** `backend/app/modules/nha_cung_cap/repository.py`, `backend/tests/test_catalog_postgres.py`, `docs/sequence/nha_cung_cap.md`, `specs/use_cases/catalog/PLAN.md`, `specs/use_cases/catalog/README.md`.

**Lệch plan (theo yêu cầu dev):** `backend/tests/test_uc13_loc_dia_chi_mot_phan.py` đã được viết và pass (2/2), sau đó bị xóa. Repo không còn test không cần DB nào kiểm tra predicate `ILIKE` của `tinh`/`phuong`; hành vi mới chỉ còn được bảo vệ bởi các test PostgreSQL.

| Lệnh | Kết quả |
|---|---|
| pytest 3 file catalog + file test mới (trước khi xóa, Codex) | 61 pass, 92 skip, 0 fail |
| pytest 3 file catalog (sau khi xóa, Claude chạy lại) | 59 pass, 92 skip, 0 fail — đúng baseline |
| ruff check / format --check `repository.py`, `test_catalog_postgres.py` | sạch |

SQL sinh ra (đã kiểm tra bằng compile dialect postgresql): `"NhaCungCap".tinh ILIKE '%%' || %(tinh_1)s::VARCHAR || '%%' ESCAPE '/'`, tương tự cho `phuong`.

| AC | Test | Kết quả |
|---|---|---|
| UC-13 AC-1, AC-4, A1 | `test_uc13_cat_ac03_literal_address_and_stable_pages` | skip (thiếu `TEST_DATABASE_URL`) |
| UC-44 AC-1 lọc địa chỉ mới (một phần) | `test_uc44_ac01_ac04_ac06_new_address_filters_and_audit` | skip (thiếu `TEST_DATABASE_URL`) |
| UC-13 AC-1, AC-4 (SQL, không DB) | `test_uc13_loc_dia_chi_mot_phan.py` | pass 2/2 rồi xóa theo yêu cầu dev |

**Giới hạn:** chưa chạy test PostgreSQL và chưa thử trên app thật (BE do dev tự chạy). Chưa chạy toàn bộ test suite. Chưa commit.
