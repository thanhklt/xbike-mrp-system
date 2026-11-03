# Ghi audit phiếu nhập qua AuditService

## Luồng sau thay đổi

`PhieuNhapService → AuditService.append → SqlAlchemyAuditRepository.append → lich_su_thao_tac`.

Giữ tên `PhieuNhapService` mà dev đã đổi trước tác vụ. Cập nhật import/type trong router/dependency và test để backend chạy với tên mới. Không đổi endpoint, payload, response, quyền, ETag, schema hoặc nghiệp vụ kho.

`get_receiving_service` nhận `AuditService` qua dependency `get_audit_service`. Hai dependency dùng chung `get_db` được FastAPI cache trong một request. Repository phiếu nhập, repository audit, inventory và transaction vì vậy nhận cùng AsyncSession.

`AuditService.append` gọi repository, không mở session riêng, không flush/commit/rollback hoặc nuốt lỗi. `PhieuNhapService` quản lý transaction của thao tác. Audit lỗi thì exception truyền ra transaction, rollback phiếu/chi tiết/tồn/ledger/audit. Hoàn tất lặp đã ghi sổ vẫn không tạo thêm audit. GET/list phiếu nhập không ghi audit.

`AuditService.list_entries` giữ chức năng đọc lịch sử. Các module khác chưa được chuyển luồng audit trong tác vụ này.

## File thay đổi

| File | Vai trò |
|---|---|
| `backend/app/modules/audit/ports.py` | Repository audit có cả đọc và append; giữ AuditWriter cho client chỉ ghi. |
| `backend/app/modules/audit/service.py` | Bổ sung API nội bộ append, chuyển tiếp repository trong transaction của caller. |
| `backend/app/modules/phieu_nhap/service.py` | Giữ lớp PhieuNhapService của dev; khai báo dependency ghi audit là AuditService. |
| `backend/app/dependencies.py` | Inject AuditService qua get_audit_service và cập nhật tên lớp. |
| `backend/app/modules/phieu_nhap/router.py` | Import và kiểu service theo tên PhieuNhapService. |
| `backend/tests/test_phieu_nhap_api.py`, `test_phieu_nhap_actions.py`, `test_receipt_v31_migration.py` | Các factory test khởi tạo PhieuNhapService với AuditService bọc repository thật; giữ test lỗi/transaction/concurrency. |
| `backend/tests/test_receipt_audit_service.py` | Kiểm forwarding/lỗi service, 4 thao tác ghi qua dependency thật và rollback trên PostgreSQL; regression GET audit. |
| `.gitignore` | Theo dõi test mới. |
| `docs/sequence/phieu_nhap.md`, `docs/sequence/assets/phieu_nhap/*.png` | Sơ đồ có tầng AuditService rồi AuditRepository, đúng tên service mới. |
| `docs/sequence/audit.md` | Sequence endpoint đọc audit hiện có, phân biệt phương thức append nội bộ với endpoint HTTP. |
| `docs/receipt-audit-service.md` | Bàn giao thay đổi này. |

## Kiểm chứng

Test ghi dùng PostgreSQL test riêng `xbike_receipt_audit_test` (container tmpfs, loopback 55453), schema test và rollback/cleanup; không dùng database ứng dụng. Hai test forwarding chạy đỏ trước sửa do AuditService chưa có append, rồi chạy xanh.

11 test mới đã đạt: 2 test forwarding/lỗi, 8 trường hợp tạo/sửa/xóa/hoàn tất thành công hoặc lỗi AuditService, 1 test đọc lịch sử. Test lỗi so sánh đầy đủ resource/ETag trước sau, số dòng phiếu/chi tiết/audit, ledger và số dư mặt hàng; test thành công xác nhận audit đã được persist cùng thao tác.

Kiểm tra cuối: **346 passed, 1 failed, 0 skipped** trong 54.17 giây. Lỗi còn lại có sẵn là `test_legacy_login_endpoints_issue_revocable_tokens`: test gọi `/api/v1/auth/login`, route này không tồn tại nên trả 404 thay vì 200. Không sửa/skip test auth ngoài phạm vi và không khẳng định toàn bộ suite xanh.

Ruff và formatter đạt trên các file Python thay đổi; mypy đạt trên 2 file audit service/ports với follow-imports=skip. Mermaid render thành công 9 sơ đồ phiếu nhập và 1 sơ đồ đọc audit; 9 ảnh PNG trong tài liệu đã được thay bằng bản thể hiện service mới. git diff --check đạt. Không chạy migration hay ghi vào DB ứng dụng. Không commit hoặc push.

Đã dừng và dọn container test tmpfs riêng sau khi xác minh ID/name/cổng; giữ nguyên các container và dữ liệu ứng dụng.

## Đồng bộ tên repository phiếu nhập

Dev tiếp tục đổi implementation thành `SqlAlchemyPhieuNhapRepository`. Đã tái hiện lỗi import ứng dụng do dependency còn import tên cũ, rồi cập nhật dependency, ba file test có factory/subclass repository và nhãn trong cả 9 sequence. Giữ nguyên thay đổi tên lớp của dev; không đổi nghiệp vụ, schema hoặc interface `ReceivingRepository` trong ports. Luồng ghi audit vẫn là `PhieuNhapService → AuditService → SqlAlchemyAuditRepository`.

Ứng dụng import thành công trở lại, OpenAPI giữ đủ 9 endpoint phiếu nhập/receiving. Đã render lại 9 ảnh PNG với tên repository mới và kiểm chữ ký PNG, checksum, đường dẫn ảnh. Regression sau đổi tên: **346 passed, 1 failed, 0 skipped**, 56.56 giây. Lỗi còn lại vẫn là test auth legacy gọi `/api/v1/auth/login` không tồn tại (404). Ruff, kiểm tra định dạng và git diff --check đạt. Không chạy migration, commit hoặc push.
