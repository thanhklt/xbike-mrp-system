# Phiếu điều chỉnh kho và ticket lỗi — triển khai và kiểm chứng

Nguồn đối chiếu: `docs/api_contract_v3.md` §2, §3, §12, §14 (đã đọc bản Drive trong thư mục project); `infra/postgres/init.sql`; `.handoff/plan-dieu-chinh-kho.md`; D-DCK-01 đến D-DCK-09 trong `docs/DECISION.md`. Module `backend/app/modules/dieu_chinh_kho/` gồm phiếu điều chỉnh và bốn endpoint ticket đã có; đường dẫn HTTP ticket giữ `/api/v1/ticket_loi_dieu_chinh`.

## Phạm vi đã triển khai

| Method | Endpoint | Quyền và hành vi |
|---|---|---|
| GET | `/api/v1/phieu_dieu_chinh_kho` | Q, phân trang/filter/sort; snapshot REPEATABLE READ READ ONLY, một truy vấn chi tiết cho cả trang |
| GET | `/api/v1/phieu_dieu_chinh_kho/{id}` | Q, resource và ETag; đọc snapshot không khóa |
| POST | `/api/v1/phieu_dieu_chinh_kho` | Q, nguồn phiếu nhập hoàn thành; tính lượng hiệu lực và biến động; tạo nháp, Location và ETag |
| PATCH | `/api/v1/phieu_dieu_chinh_kho/{id}` | Q, nháp và If-Match; lý do hoặc thay toàn bộ dòng; no-op không audit |
| DELETE | `/api/v1/phieu_dieu_chinh_kho/{id}` | Q, nháp và If-Match; xóa dòng/header cùng audit, 204 |
| POST | `/api/v1/phieu_dieu_chinh_kho/{id}/xac_nhan` | Q, body `{}`; ghi kho atomic; replay trước If-Match; chỉ thiếu tồn mới tạo ticket sau rollback |
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
| `backend/app/modules/dieu_chinh_kho/__init__.py` | Khai báo package của module mới |
| `backend/app/modules/dieu_chinh_kho/models.py` | Bốn ORM PascalCase, CHECK/FK/index và snapshot ticket |
| `backend/app/modules/dieu_chinh_kho/schemas.py` | Payload/resource/query/envelope cho phiếu và ticket; OpenAPI lỗi thiếu tồn |
| `backend/app/modules/dieu_chinh_kho/ports.py` | Persistence phiếu và ticket, nguồn lượng hiệu lực |
| `backend/app/modules/dieu_chinh_kho/repository.py` | SQL snapshot, khóa, lượng hiệu lực, CRUD, cấp mã và tạo ticket; không tự commit |
| `backend/app/modules/dieu_chinh_kho/service.py` | Quyền Q, ETag, nghiệp vụ phiếu/ticket; xác nhận và transaction 2 ghi lỗi |
| `backend/app/modules/dieu_chinh_kho/errors.py` | Lỗi công khai chỉ sau khi ticket đã commit |
| `backend/app/modules/dieu_chinh_kho/router.py` | Sáu endpoint phiếu và bốn endpoint ticket; guard, schema và header |
| `backend/app/modules/inventory/ports.py`, `repository.py` | Khóa/đối chiếu số dư; adjust_stock kiểm tra mọi dòng, cập nhật kho và ledger trong transaction của caller |
| `backend/app/dependencies.py` | Wiring repository, AuditService và SqlAlchemyTransaction cùng session |
| `backend/app/main.py` | Đăng ký cả router phiếu và ticket |
| `backend/app/models.py` | Đăng ký ORM của module mới |
| `backend/app/core/exceptions.py` | Envelope phiếu/ticket, public_details/public_extra và mã lỗi thiếu tồn |
| `backend/tests/test_dieu_chinh_kho_ticket_api.py` | Kiểm thử HTTP, quyền, SQL thực, đồng thời và rollback |
| `backend/tests/test_dieu_chinh_kho_phieu_api.py` | Kiểm thử phiếu, schema, ghi sổ, rollback, snapshot và race giữa hai transaction |
| `docs/sequence/dieu_chinh_kho.md` | Mười endpoint có sequence tương ứng với code |
| `docs/sequence/assets/dieu_chinh_kho/` | Bốn PNG ticket chuyển từ thư mục module cũ, giữ nguyên bytes |
| `docs/DECISION.md` | Ghi các quyết định D-DCK và giới hạn hoàn tác |

Không sửa `init.sql`, `seed.sql`, migration, `.env`, `config.yml` hoặc ORM inventory legacy. Hoàn tất tên module đã được dev chuyển, cập nhật import/wiring, chuyển tên file test ticket và sequence theo module mới. Không stage, commit hoặc push.

## Kiểm chứng ticket ban đầu

Chạy từ `backend/`, với `TEST_DATABASE_URL` trỏ database PostgreSQL test riêng có tên kết thúc `_test`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_dieu_chinh_kho_ticket_api.py -q --tb=short
```

**72 passed, 0 failed, 0 skipped**, 18.96 giây. Các test nạp nguyên bản bootstrap/seed vào schema test tạm riêng và dọn schema sau test, không dùng DB ứng dụng.

Đã kiểm tra OpenAPI đủ bốn route; shape và ETag; query/pagination/filter/sort/ngày; strict body; quyền DB khi JWT khai quyền sai; tài khoản khóa/role đổi/password version đổi; claim/close, close từ chờ, người nhận khác không được đóng; ticket đã đóng bất biến; request đồng thời chỉ một thay đổi được ghi và request cũ nhận 412; rollback khi lỗi AuditService, audit INSERT hoặc commit; bối cảnh/snapshot/stock/ledger/phiếu nhập/điều chỉnh không đổi.

Kiểm tra độc lập trên PostgreSQL với schema tạo từ `init.sql`: hai ORM khớp toàn bộ tên cột, kiểu, nullable, default, Identity, PK/FK, CHECK và index/unique. Audit/schema giữ nguyên. App import và OpenAPI thành công; Ruff, formatter và `git diff --check` đạt. Bốn lược đồ Mermaid đã render thành công.

## Kiểm chứng kế hoạch điều chỉnh kho ngày 04/11/2026

Môi trường: image backend `xbike-auth-plan-backend:latest` có sẵn, source mount chỉ
đọc tại `/app`, bootstrap/seed chỉ đọc tại `/infra`. Dùng container PostgreSQL 16
tách riêng, database `xbike_dck_test`, dữ liệu trên tmpfs, không mount volume ứng dụng.
Mỗi test tạo schema riêng và nạp bootstrap/seed vào schema đó; fixture từ chối URL
database không kết thúc `_test`. Công cụ pytest, pytest-asyncio, aiosqlite và Ruff
được cài trong container test; không thay lockfile/dependency project.

Không có container Compose backend đang chạy, nên dùng container test thay cho
`docker compose exec backend` trong kế hoạch. Lệnh tương đương, chạy từ `/app`:

```text
poetry run python -m pytest -q -p no:cacheprovider --tb=short
poetry run ruff check --no-cache app/modules/dieu_chinh_kho app/modules/inventory app/core/exceptions.py app/main.py app/dependencies.py app/models.py tests/test_dieu_chinh_kho_phieu_api.py tests/test_dieu_chinh_kho_ticket_api.py
poetry run ruff format --check --no-cache app/modules/dieu_chinh_kho app/modules/inventory/ports.py app/modules/inventory/repository.py app/core/exceptions.py app/main.py app/dependencies.py app/models.py tests/test_dieu_chinh_kho_phieu_api.py tests/test_dieu_chinh_kho_ticket_api.py
poetry run python -c 'import app.main'
```

Kết quả:

- Toàn bộ suite hiện có trên branch: **124 passed, 0 failed, 0 skipped**, 63,45 giây;
  gồm **52 test phiếu** và **72 test ticket**. Không coi đây là E2E các module chưa có
  trong suite của branch. pytest-asyncio cảnh báo chưa đặt fixture loop scope;
  cảnh báo không làm test thất bại.
- Phiếu: CRUD nháp, strict payload, nguồn đúng phiếu, lượng hiệu lực cộng ledger,
  ETag/no-op, quyền Q/A/N và tài khoản khóa; ghi kho đúng một lần, replay bỏ qua
  If-Match; thiếu tồn rollback mọi dòng, snapshot cả dòng hợp lệ; tính lại lượng
  hiệu lực trước khi xác nhận và lưu lỗi.
- Đồng thời: cùng nguồn được tuần tự hóa; cùng phiếu thiếu tồn chỉ có một ticket;
  PATCH giữa rollback và transaction 2 trả 412; tiến trình khác đã xác nhận trả replay
  không ticket. GET không chờ khóa ghi; snapshot là repeatable read và read only.
- Lỗi: lượng tính lại bằng 0, nguồn sai, ETag, tràn tồn INT32, lệch số dư/ledger
  không tạo ticket. Inject lỗi INSERT ledger rollback kho/trạng thái/audit; inject
  lỗi INSERT ticket rollback transaction 2, giữ nháp, không tuyên bố ticket đã lưu.
- Hai ORM phiếu khớp cột, kiểu PostgreSQL, nullable/default/identity, FK deferrable,
  CHECK và index trong schema bootstrap thực. Bulk insert dòng dùng SQLAlchemy Core
  vì metadata ORM ledger PascalCase chưa thuộc phạm vi chuyển đổi; vẫn giữ nguyên
  FK và trigger của bootstrap, không thêm ORM hoặc bảng ledger thay thế.
- Ruff: **All checks passed**. Formatter: **16 files already formatted**. App import
  thành công; OpenAPI đủ 6 operation phiếu và 4 operation ticket; lỗi thiếu tồn có
  các field mở rộng trong schema response.
- `git diff --check` đạt; không còn import `app.modules.ticket_dieu_chinh`.
  Test ticket giữ nguyên nội dung so với HEAD; bốn PNG sau chuyển thư mục giữ nguyên
  SHA-256. Sequence đủ 10 mục endpoint/10 block `sequenceDiagram`, link ảnh tồn tại,
  đã đối chiếu source. **Chưa parse/render sáu sơ đồ phiếu mới** vì không có Mermaid
  parser/CLI trong môi trường; bốn PNG ticket là artifact cũ được giữ nguyên.
- Structure map không phát hiện vòng phụ thuộc trong phạm vi module. Script kiểm tra
  layer không chạy được vì repo chưa có khai báo `clean-architecture`; đã rà import
  trực tiếp: router gọi service, service dùng port, repository sở hữu SQL, dependency
  wiring dùng chung session. Không tự thêm cấu hình kiến trúc ngoài kế hoạch.

## Giới hạn

- Đã triển khai tự tạo ticket khi xác nhận thất bại vì thiếu tồn; mọi dòng đề nghị đều được chụp. Không có endpoint tạo ticket thủ công. Lỗi khác không sinh ticket hoặc cơ chế bù bền vững.
- Database đang chạy cần có schema PascalCase đã chốt; không tự nâng cấp hoặc seed lại database đã có dữ liệu.
- Không khẳng định các module legacy khác đã được đồng bộ v3 hoặc đã đạt E2E. Không commit hoặc push.
