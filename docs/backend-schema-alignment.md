# Đồng bộ backend với PostgreSQL

Nguồn schema demo hiện tại là SQL v4 trong `infra/postgres/init.sql` và `infra/postgres/seed.sql`, cùng các quyết định trực tiếp của dev ngày 30/10/2026.

Refactor hiện tại đồng bộ ba ORM/bảng `NhanVien`, `VaiTro`, `LichSuThaoTac`: IDENTITY BY DEFAULT, nullability, kiểu dữ liệu, defaults, CHECK, UNIQUE, FK DEFERRABLE INITIALLY IMMEDIATE và index. Audit dùng JSONB và TIMESTAMPTZ; SQL trigger chặn sửa/xóa lịch sử. Tên cột và giá trị nghiệp vụ không đổi theo tên bảng.

Auth gọi public service nhân viên; nhân viên gọi public audit service, dùng chung session/transaction khi đổi mật khẩu. FK từ các ORM khác được cập nhật sang NhanVien, nhưng không đồng bộ toàn bộ schema nghiệp vụ trong tác vụ này. Test toàn schema còn báo thiếu mapping chi_tiet_ticket_loi_dieu_chinh và khác biệt cột/kiểu/FK/index ở các module khác; dev đã chốt giữ phạm vi auth/nhân viên/audit.

Demo chạy bằng bootstrap Docker trên database mới/trống; không có migration. Nội dung ghi nhận các lần đồng bộ cũ bên dưới là lịch sử và không chứng nhận toàn bộ ORM hiện tại khớp SQL v4.

## Vị trí sửa

Các đường dẫn dưới đây tính từ thư mục gốc dự án. Với mỗi module,
`models.py` chứa ORM, `schemas.py` chứa request/response và `router.py`
đọc/ghi PostgreSQL qua `AsyncSession`, thay cho danh sách mẫu trong bộ nhớ.

| Module trong `backend/app/modules/` | Bảng được ánh xạ |
| --- | --- |
| `nhan_vien/` | `NhanVien`, `VaiTro` |
| `catalog/` | `mat_hang` |
| `suppliers/` | `nha_cung_cap` |
| `bom/` | `bom`, `chi_tiet_bom` |
| `receiving/` | `phieu_nhap`, `chi_tiet_phieu_nhap` |
| `material_issuing/` | `phieu_xuat`, `chi_tiet_phieu_xuat` |
| `finished_goods_issuing/` | Dùng lại ORM và schema của phiếu xuất; lọc `loai_phieu = 'xuat_thanh_pham'` |
| `production/` | `yeu_cau_san_xuat`, `lenh_san_xuat`, `chi_tiet_lenh_san_xuat`, `chung_tu_hoan_thanh_sx` |
| `inventory/` | `ton_kho`, `giao_dich_kho`, `phieu_dieu_chinh_kho`, `chi_tiet_phieu_dieu_chinh_kho`, `ticket_loi_dieu_chinh` |
| `audit/` | `LichSuThaoTac` |

Các file liên quan:

- `backend/app/modules/auth/router.py`, `schemas.py`: xác thực tài khoản
  PostgreSQL bằng bcrypt; hỗ trợ tên đăng nhập hoặc email từ seed;
  `/auth/me` trả đúng nhân viên đang đăng nhập.
- `backend/app/core/security.py`: JWT lưu ID nhân viên; quyền được đọc lại
  từ database. Vai trò là `quan_tri_vien`, `quan_ly`, `nhan_vien`.
- `backend/app/shared/enums.py`: giá trị enum theo SQL.
- `backend/app/shared/database_queries.py`: phân trang, tìm kiếm, truy vấn
  bản ghi, tạo dữ liệu/chứng từ nháp và audit cùng transaction.
- `backend/app/models.py`, `backend/migrations/env.py`: đăng ký đầy đủ ORM
  trước khi Alembic đọc metadata.
- Các `backend/app/modules/*/__init__.py`: bỏ import router tự động để tránh
  vòng import khi đăng ký model.
- `backend/app/modules/reporting/router.py`, `schemas.py`: KPI lấy từ
  database; chỉ số chưa tính được trả `null`, bỏ kết quả MRP giả.
- `backend/app/core/logging.py`: đưa import `logging.config` ra khỏi hàm,
  sửa lỗi `UnboundLocalError` chặn khởi động backend.
- `backend/pyproject.toml`: SQLAlchemy có dependency asyncio, dùng bcrypt
  trực tiếp và thêm SQLite vào dependency test.
- `.github/workflows/backend-ci.yml`: cài dependency dev, khởi tạo database
  test bằng cả hai file SQL và chạy integration test.
- `infra/postgres/seed.sql`: dòng chi tiết của phiếu điều chỉnh lỗi dùng
  ID 18. Các ID cố định trước đó không tăng sequence ngay, nên để tự sinh
  ID ở dòng này làm trùng ID 1 và rollback toàn bộ seed.
- `backend/tests/test_schema_contract.py`, `test_database_api.py`,
  `test_postgres_seed.py`, `test_main.py`, `conftest.py`: kiểm tra schema,
  API đọc dữ liệu thật, phân trang, đăng nhập, quyền truy cập, mật khẩu
  Unicode, tạo nháp có audit và khởi động ứng dụng.
- Các chỉnh sửa import/format ở `backend/app/core/config.py`, `database.py`,
  `exceptions.py`, `backend/app/main.py`, `backend/app/shared/pagination.py`
  phục vụ kiểm tra Ruff.

## Thay đổi API và phạm vi

Đường dẫn endpoint được giữ lại. Request/response nghiệp vụ dùng tên cột
theo SQL, ví dụ `ma_mat_hang`, `ten_mat_hang`, `so_luong`, `trang_thai`.
Những cột thuộc schema cũ nhưng không có trong SQL đã được bỏ, gồm warehouse,
reservation, scrap, serial number và các trường thời gian không tồn tại.
Mọi API nghiệp vụ yêu cầu token hợp lệ; thông tin mật khẩu không được trả
trong response hoặc ghi vào audit.

Tạo phiếu nhập, phiếu xuất và lệnh sản xuất chỉ tạo nháp. Không thay đổi
tồn kho hoặc sổ kho khi tạo nháp. Các endpoint trước đây giả lập ghi sổ kho,
đổi trạng thái lệnh sản xuất và chạy MRP hiện trả HTTP 501; workflow hoàn
chỉnh cần được triển khai riêng theo các yêu cầu ở đầu `init.sql`.

Trigger bảo vệ lịch sử/sổ kho vẫn do `init.sql` tạo; `metadata.create_all()`
không thay thế quá trình bootstrap SQL này.

Frontend được giữ nguyên theo yêu cầu: vẫn còn dữ liệu mẫu và token giả,
nên chưa tích hợp với API mới trong lần sửa này.

## Kiểm tra

Trong thư mục `backend`:

```powershell
poetry sync --with dev
poetry run pytest -q
poetry run ruff check .
poetry run ruff format --check .
```

Integration test cần một database test riêng đã chạy `init.sql` rồi
`seed.sql`. Đặt `TEST_DATABASE_URL` tới database đó trước khi chạy pytest.
Test dùng transaction ngoài và savepoint để rollback các dữ liệu tạo thêm.
Không đặt biến này tới database ứng dụng.

Kết quả kiểm chứng của refactor hiện tại được ghi trong plan `docs/plans/2026-10-30-auth-nhan-vien-boundaries.md`. Chỉ dùng database test riêng; không seed hoặc thay đổi database ứng dụng. So sánh schema bằng inspector không phải chạy migration.
