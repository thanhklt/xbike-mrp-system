# Phiếu xuất — triển khai API contract v3

Nguồn: `docs/api_contract_v3.md` §2, §3, §10, §14 và `infra/postgres/init.sql`. Dev đã chốt đủ chín API v3, giữ PascalCase, dùng BIGINT cho tiền phiếu xuất và đơn giá mặt hàng, cho phép cập nhật phần phụ thuộc mặt hàng. Giữ tên lớp `PhieuXuatService` mà dev đã đổi.

Tại thời điểm bắt đầu triển khai v3, repository không còn MERGE_HEAD hoặc file unmerged. Không tạo merge commit, commit hay push trong tác vụ này.

## Hành vi và tương thích

- Q lập/sửa/xóa/gửi/duyệt/từ chối/về nháp mọi phiếu, kể cả phiếu mình lập. Q/N đọc, N chỉ thấy phiếu thuộc công việc hiện được giao. A không có quyền nghiệp vụ phiếu xuất. Auth kiểm tra tài khoản, vai trò từ DB và phiên bản mật khẩu hiện hành.
- Chỉ có `/api/v1/phieu_xuat` và bốn action tiếng Việt. Gỡ đăng ký hai router `/material-issuing` và `/finished-goods-issuing` để không còn đường ghi theo quyền/payload cũ. Các thư mục legacy còn được giữ vì ngoài phạm vi chuyển đổi module khác.
- Người lập là `nhan_vien_id` lấy từ JWT; không dùng `ma_nhan_vien`. Client chỉ gửi loại, đúng một nguồn và chi tiết `{mat_hang_id, so_luong}`. Gửi đơn giá, tổng, mã phiếu, người lập hoặc trường lạ trả 422.
- Giá/tổng null trước duyệt. Duyệt đọc đơn giá DB dưới khóa, chốt integer VND và giữ bất biến. BIGINT tối đa 9223372036854775807; tổng vượt giới hạn trả 409 và không ghi sổ.
- Thay đổi resource dùng strong If-Match. Thiếu/rỗng 428, stale/weak/wildcard 412. Duyệt đã thành công cho retry với strong ETag cũ khi còn quyền; trả cùng ledger IDs và `da_ghi_so_truoc_do=true`, không audit hoặc trừ kho thêm.
- Khóa nguồn trước phiếu để dùng chung thứ tự với hủy sản xuất. Khóa mặt hàng tăng dần ID. Tồn phải khớp tổng ledger, không âm; tổng xuất đã duyệt không vượt nhu cầu nguồn. Vật tư dùng nhu cầu trực tiếp của lệnh, thành phẩm dùng đúng mặt hàng và lượng yêu cầu.
- Xuất thành phẩm một phần chuyển yêu cầu sang `dang_thuc_hien`; đủ lượng chuyển `hoan_thanh` và ghi `completed_at`. Yêu cầu `cho_bo_sung_vat_tu` không được xuất thành phẩm.
- Giá/trạng thái/tồn/ledger/tiến độ/audit dùng chung transaction. Lỗi rollback toàn bộ, không tạo ticket. Phiếu `da_duyet` không sửa/xóa/điều chỉnh.

## File và vai trò

| File | Vai trò / thay đổi |
|---|---|
| `backend/app/modules/phieu_xuat/router.py` | Chín endpoint, quyền đọc/ghi, validation, response schema, ETag và Location |
| `backend/app/modules/phieu_xuat/schemas.py` | Create/Patch chỉ có số lượng; Read integer VND; query whitelist, body rỗng/lý do và envelope |
| `backend/app/modules/phieu_xuat/service.py` | Nghiệp vụ, phạm vi đọc, ETag, chuyển trạng thái, duyệt lặp, tính tiền/tiến độ và gọi AuditService; giữ helper phục vụ sản xuất |
| `backend/app/modules/phieu_xuat/ports.py` | Interface persistence và snapshot rời ORM cho service |
| `backend/app/modules/phieu_xuat/repository.py` | SQL/ORM nguồn và phiếu, cấp mã có khóa, nhu cầu đã xuất, snapshot, giá và tiến độ; không commit riêng |
| `backend/app/modules/phieu_xuat/models.py` | ORM PascalCase; ba cột tiền BIGINT nullable trước duyệt |
| `backend/app/modules/phieu_xuat/errors.py` | Lỗi vượt nhu cầu, phụ thuộc và mặt hàng ngừng hoạt động |
| `backend/app/modules/inventory/ports.py`, `repository.py` | Port ghi xuất, kiểm tra số dư với ledger, ghi giao dịch âm có FK nguồn và trừ tồn; không đổi ORM tồn kho legacy |
| `backend/app/modules/mat_hang/models.py`, `schemas.py` | `don_gia` BIGINT NOT NULL, API integer VND bắt buộc, PATCH không cho null |
| `backend/app/modules/mat_hang/router.py`, `service.py`, `cache.py` | Đồng bộ kiểu giá/bộ lọc giá từ Decimal sang integer |
| `backend/app/dependencies.py`, `main.py` | Wiring service/audit/inventory cùng session, giữ helper sản xuất, đăng ký router tiếng Việt và gỡ hai router xuất cũ |
| `backend/app/core/errors.py`, `exceptions.py` | Lỗi thiếu tồn có quantity details an toàn; envelope và status cho phiếu xuất |
| `infra/postgres/init.sql` | Bootstrap BIGINT cho đơn giá mặt hàng và ba cột tiền xuất, không sửa các cột tiền module khác |
| `backend/tests/test_phieu_xuat_api.py` | Kiểm thử HTTP và PostgreSQL thực, dùng bootstrap/seed trong schema test riêng |
| `docs/sequence/phieu_xuat.md`, `mat_hang.md` | Sequence từng endpoint và mô tả kiểu giá mới |
| `docs/sequence/material_issuing.md`, `finished_goods_issuing.md` | Ghi rõ hai router cũ không còn được đăng ký |

`seed.sql` hiện đã có đơn giá integer cho 17 mặt hàng và giá phiếu xuất mẫu theo v3; đã dùng nguyên bản để kiểm thử, không cần sửa hoặc seed lại database ứng dụng.

## Kiểm chứng

Chạy từ `backend/`, dùng `TEST_DATABASE_URL` trỏ tới database PostgreSQL riêng có tên kết thúc `_test`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q --tb=short
```

Kết quả: **55 passed, 0 failed, 0 skipped**, 17.29 giây. Đây là toàn bộ test được pytest thu thập trong checkout hiện tại, không phải khẳng định mọi module của hệ thống đã có kiểm thử hoặc đã nâng v3.

Các nhóm đã kiểm tra: đủ 9 route/OpenAPI; tạo/sửa/xóa/gửi/từ chối/về nháp; Q tự duyệt và Q khác xử lý; N/A không được ghi dù JWT tự khai quyền Q; N đọc theo người được giao hiện tại; khóa tài khoản và đổi phiên bản mật khẩu; input/query/If-Match; tiền trên 2,1 tỷ; chốt giá theo thời điểm duyệt và bất biến về sau; tồn và ledger khớp; tiến độ thành phẩm; chống gọi duyệt lặp và đồng thời; hai phiếu vượt nhu cầu; hai nguồn tranh cùng tồn; rollback lỗi ledger/balance/audit và tiến độ yêu cầu; hủy phiếu từ service sản xuất; mã phiếu đã xóa không tái sử dụng; API mặt hàng trả giá integer, không nhận null/fraction/string/bool; đối chiếu bốn cột BIGINT trong PostgreSQL thực.

Ruff và formatter đạt trên các file Python thay đổi, `git diff --check` đạt. Mermaid render thành công **9 sơ đồ phiếu xuất và 7 sơ đồ mặt hàng**. App import và OpenAPI thành công. Không có file unmerged hoặc marker conflict trong phần code đã thay đổi.

## Giới hạn triển khai

- Chỉ cập nhật bootstrap cho database mới/trống. Database/volume đã khởi tạo không tự đổi kiểu cột khi rebuild hoặc restart. Không chạy migration, không thay `.env`/`config.yml`, không sửa/seed/xóa database ứng dụng.
- Client dùng payload v2 phải đổi quyền ghi N → Q, bỏ đơn giá input, chuyển `ma_nhan_vien` sang `nhan_vien_id` ở Read/filter và nhận tiền JSON integer. Frontend chưa được cập nhật trong tác vụ này.
- Các cột tiền và module legacy khác chưa chuyển toàn bộ sang v3. Không chuyển đổi ORM tồn kho cũ hoặc khẳng định các endpoint inventory legacy đã tương thích SQL hiện tại.
