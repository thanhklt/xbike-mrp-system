# Ticket lỗi điều chỉnh — triển khai và kiểm chứng

Nguồn đối chiếu: `docs/api_contract_v3.md` §2, §3, §12.2, §14; `infra/postgres/init.sql`; bốn ảnh API-076 đến API-079 do dev cung cấp. Module được triển khai trong `backend/app/modules/ticket_dieu_chinh/` theo yêu cầu, đường dẫn HTTP giữ `/api/v1/ticket_loi_dieu_chinh`.

## Phạm vi đã triển khai

| Method | Endpoint | Quyền và hành vi |
|---|---|---|
| GET | `/api/v1/ticket_loi_dieu_chinh` | Q, danh sách phân trang và lọc/sort theo contract |
| GET | `/api/v1/ticket_loi_dieu_chinh/{id}` | Q, TicketRead với snapshot chi tiết và strong ETag |
| POST | `/api/v1/ticket_loi_dieu_chinh/{id}/nhan_xu_ly` | Q, body `{}`, If-Match; `cho_xu_ly → dang_xu_ly`, người xử lý lấy từ JWT |
| POST | `/api/v1/ticket_loi_dieu_chinh/{id}/giai_quyet` | Q, `{ket_qua_xu_ly}` trim không rỗng, If-Match; đóng trực tiếp ticket chờ hoặc đóng ticket do chính mình đang xử lý |

A/N không có quyền; mọi request kiểm tra tài khoản, vai trò hiện tại từ DB và phiên bản mật khẩu. Danh sách nhận `page`, `page_size`, `trang_thai`, `phieu_nhap_id`, `nguoi_tao_id`, `nguoi_xu_ly_id`, `tu_ngay`, `den_ngay`, `sort`; không có `q` hoặc query legacy. Sort ±id/created_at/ma_ticket, ID là tiêu chí phụ; ngày theo Asia/Ho_Chi_Minh và tính cả hai đầu.

Action khóa ticket FOR UPDATE, kiểm tra If-Match rồi trạng thái/người xử lý. Thiếu/rỗng 428; stale/weak/wildcard 412; ngoài quyền/người xử lý 403; không tồn tại 404; sai trạng thái 409; input/query/header lặp 422. Ticket đã đóng không sửa/mở lại và không có ngoại lệ retry bỏ qua ETag. GET/action trả envelope `{data,meta}`; lỗi `{error,meta}`; GET chi tiết và action có ETag.

Bối cảnh và chi tiết được đọc từ bảng PascalCase `TicketLoiDieuChinh`, `ChiTietTicketLoiDieuChinh`; không dùng ORM ticket legacy của inventory. Các snapshot không bị cập nhật. Nhận/đóng không thay đổi tồn kho, ledger, phiếu nhập hoặc phiếu điều chỉnh. Đóng ticket không yêu cầu có phiếu điều chỉnh mới thành công.

Luồng ghi: `TicketDieuChinhService → SqlAlchemyTicketDieuChinhRepository` và `TicketDieuChinhService → AuditService → SqlAlchemyAuditRepository`. Ticket và audit dùng chung session/transaction; lỗi ở service, flush hoặc commit rollback cả hai. Audit ghi `nhan_xu_ly`/`giai_quyet`, người thực hiện từ JWT và snapshot trước/sau.

## File và vai trò

| File | Vai trò |
|---|---|
| `backend/app/modules/ticket_dieu_chinh/__init__.py` | Khai báo package của module mới |
| `backend/app/modules/ticket_dieu_chinh/models.py` | Hai ORM PascalCase khớp schema đã chốt, FK và snapshot bất biến |
| `backend/app/modules/ticket_dieu_chinh/schemas.py` | TicketRead, query, hai body action, envelope và validation |
| `backend/app/modules/ticket_dieu_chinh/ports.py` | Interface persistence của use case ticket |
| `backend/app/modules/ticket_dieu_chinh/repository.py` | SQL đọc/khóa/cập nhật ticket, không commit hoặc ghi kho riêng |
| `backend/app/modules/ticket_dieu_chinh/service.py` | Quyền Q, ETag, trạng thái, chủ xử lý, đóng và audit chung transaction |
| `backend/app/modules/ticket_dieu_chinh/router.py` | Bốn endpoint, dependency quyền, schema OpenAPI và header ETag |
| `backend/app/dependencies.py` | Wiring repository, AuditService và SqlAlchemyTransaction cùng session |
| `backend/app/main.py` | Đăng ký router ticket |
| `backend/app/models.py` | Đăng ký ORM của module mới |
| `backend/app/core/exceptions.py` | Áp dụng error envelope contract cho đường dẫn ticket |
| `backend/tests/test_ticket_dieu_chinh_api.py` | Kiểm thử HTTP, quyền, SQL thực, đồng thời và rollback |
| `docs/sequence/ticket_dieu_chinh.md` | Bốn endpoint có sequence tương ứng với code |

Không sửa `init.sql`, `seed.sql`, migration, `.env`, `config.yml` hoặc ORM inventory legacy. Dev đã đưa tên thư mục `Inventory` về `inventory`; không cần sửa import ngoài module ticket.

## Kết quả kiểm chứng

Chạy từ `backend/`, với `TEST_DATABASE_URL` trỏ database PostgreSQL test riêng có tên kết thúc `_test`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_ticket_dieu_chinh_api.py -q --tb=short
```

**72 passed, 0 failed, 0 skipped**, 18.96 giây. Các test nạp nguyên bản bootstrap/seed vào schema test tạm riêng và dọn schema sau test, không dùng DB ứng dụng.

Đã kiểm tra OpenAPI đủ bốn route; shape và ETag; query/pagination/filter/sort/ngày; strict body; quyền DB khi JWT khai quyền sai; tài khoản khóa/role đổi/password version đổi; claim/close, close từ chờ, người nhận khác không được đóng; ticket đã đóng bất biến; request đồng thời chỉ một thay đổi được ghi và request cũ nhận 412; rollback khi lỗi AuditService, audit INSERT hoặc commit; bối cảnh/snapshot/stock/ledger/phiếu nhập/điều chỉnh không đổi.

Kiểm tra độc lập trên PostgreSQL với schema tạo từ `init.sql`: hai ORM khớp toàn bộ tên cột, kiểu, nullable, default, Identity, PK/FK, CHECK và index/unique. Audit/schema giữ nguyên. App import và OpenAPI thành công; Ruff, formatter và `git diff --check` đạt. Bốn lược đồ Mermaid đã render thành công.

## Giới hạn

- Đây là bốn endpoint đọc/nhận/đóng ticket đã có. Luồng tự tạo ticket khi xác nhận phiếu điều chỉnh thất bại thuộc tác vụ phiếu điều chỉnh, chưa triển khai trong module này. Không có endpoint tạo ticket thủ công.
- Database đang chạy cần có schema PascalCase đã chốt; không tự nâng cấp hoặc seed lại database đã có dữ liệu.
- Không khẳng định các module legacy khác đã được đồng bộ v3 hoặc đã đạt E2E. Không commit hoặc push.
