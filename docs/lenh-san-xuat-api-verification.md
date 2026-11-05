# Bảy API lệnh sản xuất — kiểm chứng ngày 04/11/2026

Nguồn: [API contract v3 §9](https://drive.google.com/file/d/1yznre1rfIK6IIp8UTWb_D842r8vrNTIE/view), bản data model v3.1 đã cung cấp và schema `infra/postgres/init.sql`. ORM `LenhSanXuat`/`ChiTietLenhSanXuat` thuộc `lenh_san_xuat/models.py`, được chuyển nguyên định nghĩa từ `san_xuat`. Không đổi bảng/cột/kiểu/ràng buộc, bootstrap, migration hoặc database ứng dụng.

| Method | Path | Quyền | Hành vi |
|---|---|---|---|
| GET | `/api/v1/lenh_san_xuat` | Q/N | Phân trang, tìm mã, filter/sort, N chỉ thấy lệnh của mình |
| GET | `/api/v1/lenh_san_xuat/{id}` | Q/N được giao | Nhu cầu/BOM đã chốt, tiến độ, ID con, ETag |
| PATCH | `/api/v1/lenh_san_xuat/{id}` | Q | Chỉ `nhan_vien_id: int|null`, chỉ nháp |
| GET | `/api/v1/lenh_san_xuat/{id}/vat_tu` | Q/N được giao | Cần/đã cấp/còn cấp/tồn hiện tại và điều kiện bắt đầu, ETag |
| POST | `/api/v1/lenh_san_xuat/{id}/gui` | Q | Body `{}`, nháp → đã gửi, cần N hợp lệ, không cần đủ tồn |
| POST | `/api/v1/lenh_san_xuat/{id}/bat_dau` | N được giao | Body `{}`, đã gửi → đang làm, cần cấp đủ qua phiếu xuất đã duyệt |
| POST | `/api/v1/lenh_san_xuat/{id}/huy` | Q | Body `{ly_do}`, chưa ghi sổ vật tư/đầu ra và không con hoạt động |

Lệnh vẫn được sinh từ gửi yêu cầu. Không thêm POST tạo lệnh thủ công hay endpoint hoàn tất trực tiếp. Duyệt đầu ra qua chứng từ hoàn thành hiện có tiếp tục tự hoàn thành lệnh khi đạt lượng. Không có endpoint mới nào ghi tồn/ledger. Nhân viên bị khóa, vai trò hiện tại, phiên bản mật khẩu đều kiểm tra từ DB qua auth dùng chung.

Filter: `q`, `yeu_cau_san_xuat_id`, `lenh_san_xuat_cha_id`, `nhan_vien_id`, `mat_hang_id`, `trang_thai`, `tu_ngay`, `den_ngay`. Sort: `id`, `created_at`, `ma_lenh_san_xuat` với tiền tố `-` để giảm dần; thêm ID phụ. Ngày theo Asia/Ho_Chi_Minh, cả hai đầu. Query lạ/lặp, ngày không đúng YYYY-MM-DD, ngày đảo, enum/sort/ID sai trả 422.

GET chi tiết và vật tư dùng cùng strong ETag của lệnh, nguồn và snapshot vật tư. PATCH/actions so dưới khóa yêu cầu → lệnh: thiếu/blank 428, cũ/weak/wildcard/list 412. Quyền/phạm vi được kiểm tra trước so phiên bản. Hủy lưu lý do trong audit, giữ các chứng từ nháp/chờ duyệt liên quan; chúng vẫn chịu kiểm tra nguồn khi thao tác sau này. Phân công không thay đổi là no-op, không ghi audit trùng.

Luồng: `san_xuat.router (lenh_sx_router) → LenhSanXuatService → SqlAlchemyLenhSanXuatRepository → PostgreSQL`; audit: `LenhSanXuatService → AuditService → SqlAlchemyAuditRepository`. Cùng `SqlAlchemyTransaction`, lỗi audit/commit rollback cả lệnh/yêu cầu/audit. Bắt đầu chỉ đưa yêu cầu `da_gui` sang `dang_thuc_hien`, giữ `cho_bo_sung_vat_tu`.

## File bổ sung và cập nhật

| File | Vai trò |
|---|---|
| `backend/app/modules/san_xuat/router.py` (`lenh_sx_router`) | Bảy endpoint, role guard, validation, request_id và ETag |
| `backend/app/modules/san_xuat/service/lenh_san_xuat.py` | Quyền/phạm vi, trạng thái, If-Match, điều kiện gửi/bắt đầu/hủy, audit |
| `backend/app/modules/san_xuat/repository/lenh_san_xuat.py` | Query và snapshot, khóa yêu cầu/lệnh, tổng đã cấp/hoàn thành, truy cập DB |
| `backend/app/modules/san_xuat/models.py` | Sở hữu ORM LenhSanXuat và ChiTietLenhSanXuat, FK/Identity/CHECK/index/relationship đúng bootstrap |
| `backend/app/modules/san_xuat/ports.py` | LenhContext, port repository và kiểm tra nhân viên, không phụ thuộc ORM |
| `backend/app/modules/san_xuat/schemas.py` | PATCH/query/read/vật tư/envelope/lỗi/action body và enum trạng thái |
| `backend/app/modules/san_xuat/models.py`, `schemas.py` | Bỏ khai báo ORM/LenhRead trùng; kế hoạch yêu cầu dùng LenhRead từ module lệnh |
| `backend/app/modules/san_xuat/ports.py`, `repository.py`, `service.py` | Cập nhật import model/schema mới cho luồng sinh lệnh và hoàn thành |
| `backend/app/modules/phieu_xuat/repository.py` | Dùng ORM lệnh từ module sở hữu mới khi kiểm tra nguồn/cấp vật tư |
| `backend/app/models.py` | Đăng ký ORM mới vào metadata dùng chung, không tạo bảng trùng |
| `backend/app/dependencies.py` | Gắn repository, service nhân viên, AuditService và transaction cùng session |
| `backend/app/main.py` | Đăng ký router lệnh |
| `backend/app/core/exceptions.py` | Thêm lệnh vào envelope lỗi contract v3 |
| `backend/tests/test_lenh_san_xuat_api.py` | Kiểm thử HTTP với PostgreSQL, dùng fixture schema tạm từ test phiếu xuất |
| `backend/tests/test_lenh_san_xuat_contract.py` | Khởi động, đăng ký mapper/FK một lần, module/schema sở hữu endpoint và validation |
| `docs/sequence/san_xuat.md` (mục Lệnh sản xuất) | Bảy sequence của lệnh, cùng file với sequence yêu cầu/hoàn thành |
| `docs/sequence/assets/san_xuat/lenh-*.png` | Bảy ảnh PNG đã render Mermaid và xem lại |
| `docs/examples/lenh-san-xuat-http.json` | Tám request/response HTTP thực tế, không lưu JWT/mật khẩu |

## Kết quả thực chạy

- Riêng lệnh: **90 ca đều pass**, gồm 71 ca HTTP/PostgreSQL và 19 ca khởi động/schema. Các ca này được chạy trong toàn bộ suite, không skip. Có test hai request gửi/bắt đầu cùng ETag → 200/412 và chỉ một audit.
- Đối chiếu hai ORM với PostgreSQL bootstrap thật: tên/kiểu/nullable/default/Identity/PK/FK/deferrable/chế độ IMMEDIATE, CHECK, unique và index. Kiểm tra mapper chỉ đăng ký một lần, FK/relationship trỏ đúng class. Luồng tạo yêu cầu → tính/gửi kế hoạch → sinh cây lệnh → GET/PATCH lệnh dùng chung đúng các model/schema mới.
- Có kiểm tra JWT thiếu/hết hạn/sai pwdv, quyền từ DB thay vì JWT giả role, khóa tài khoản, N ngoài phạm vi, nullable/invalid assignee, nguồn đóng, strict body/query/header, đủ/thiếu/chưa duyệt vật tư, giới hạn hủy do con/ghi sổ, giữ BOM/nhu cầu, không đổi tồn, commit/audit rollback, và bắt đầu → duyệt đầu ra → tự hoàn thành lệnh.
- Toàn bộ test backend sau khi hoàn thiện module: **213 passed, 3 failed trong 44,74 giây**, không skip. Không báo toàn hệ thống đã pass.
- Xác minh baseline: xuất code `HEAD` chưa có thay đổi lần này sang thư mục tạm, chạy module `test_hoan_thanh_postgres.py` độc lập: **18 passed, đúng 3 failed giống hệt**. Không sửa/giảm kiểm thử cũ để làm xanh.
- Ba lỗi baseline: `test_roles_scope_and_reassignment_are_enforced` (`password_version(None)`), `test_local_date_filter_null_history_and_literal_search` (ID cuối 18 so với 19), `test_approval_business_failures_leave_pending_without_posting[balance-trang_thai_khong_hop_le]` (tồn 0 so với 123). Nằm ngoài phần lệnh mới.
- Ruff check và format trong phạm vi đạt; mypy cả 7 file của module mới đạt với `--follow-imports=silent` (không phải chứng nhận mypy toàn backend). `git diff --check` đạt.
- Bảy block Mermaid mới render thành PNG thành công và đã kiểm tra ảnh.

## Tái chạy và thử trên Swagger

`TEST_DATABASE_URL` bắt buộc trỏ PostgreSQL test riêng có tên DB kết thúc `_test`. Fixture chỉ tạo/drop schema UUID do chính test sở hữu. Không trỏ đến database ứng dụng. Container chạy kiểm chứng dùng tmpfs/cổng 55461, được dừng và tự xóa sau bàn giao; URL của lần test này không còn dùng để kết nối khi container đã dừng.

```powershell
cd D:\xbike-mrp-system\backend
# Thiết lập TEST_DATABASE_URL của database test riêng trước.
..\.venv\Scripts\python.exe -m pytest tests/test_lenh_san_xuat_api.py tests/test_lenh_san_xuat_contract.py -q
```

Chạy backend bằng cấu hình DB hiện có rồi mở `/docs`, tìm tag `lenh_san_xuat`. Dùng Q xem/gán N/gửi/hủy. Dùng N được giao xem vật tư và bắt đầu. Trước PATCH/action lấy `ETag` từ GET chi tiết hoặc vật tư, gửi nguyên token có dấu ngoặc kép qua `If-Match`. Chỉ cấp đủ vật tư bằng phiếu xuất đã duyệt mới bắt đầu được. Trạng thái đã thay đổi phải GET lại ETag; action này không phải action ghi sổ retry có ngoại lệ ETag cũ.

Thay đổi request/response hiện có duy nhất: `LenhRead.trang_thai` được mô tả bằng enum chính xác của SQL thay vì string tự do, cả trong kế hoạch yêu cầu. Các giá trị JSON hợp lệ không đổi. Không thay frontend, dependency hay schema DB. Chưa commit/push.

Kế hoạch quay lại nếu cần: bỏ đăng ký `lenh_sx_router` và các thay đổi thuộc tác vụ này sau khi review diff. Không có migration xuống hoặc reset/seed lại DB. Các trạng thái đã ghi qua API mới đều thuộc enum hiện có của SQL; không tự hoàn tác dữ liệu nghiệp vụ đã được người dùng xác nhận.

## Tách module theo yêu cầu

Module `lenh_san_xuat` đã có đủ `__init__.py`, `models.py`, `ports.py`, `schemas.py`, `router.py`, `service.py`, `repository.py`. Ba file trước đây rỗng nay có triển khai thực sự, không chỉ re-export từ `san_xuat`. Sửa lỗi khởi động `ImportError: LenhContext` do import tới khai báo không còn tồn tại. Schema/port lệnh được đặt tại module sở hữu và router dùng `LenhEmptyInput`, `LyDoInput`, `LenhErrorResponse` của chính module.

Yêu cầu/kế hoạch và chứng từ hoàn thành vẫn thuộc `san_xuat`. Các phần đó và phiếu xuất import model/schema lệnh từ `lenh_san_xuat`; chỉ có một khai báo ORM cho mỗi bảng. Không đổi URL hoặc dữ liệu JSON hợp lệ của bảy endpoint. Kế hoạch cũng dùng chung đúng LenhRead mới. Không còn import `san_xuat.lenh_*`. Ba lỗi baseline đã ghi ở trên vẫn ngoài phạm vi.

## Gộp vào module `san_xuat` (05/11/2026)

Module lệnh đã được gộp vào `san_xuat`, API không đổi (theo `.handoff/plan-gop-lenh-san-xuat.md`). Mục "Tách module theo yêu cầu" ở trên chỉ còn giá trị lịch sử. Hiện ORM lệnh chỉ khai báo trong `san_xuat/models.py`. Router lệnh là `lenh_sx_router` trong `san_xuat/router.py`, cạnh `yeu_cau_sx_router` và `chung_tu_router`. Service và repository tách theo chứng từ trong `san_xuat/service/` và `san_xuat/repository/`. Thay đổi duy nhất trên OpenAPI là `operationId` của bảy endpoint lệnh và tên component ngắn. Path, method, body và response giữ nguyên.
