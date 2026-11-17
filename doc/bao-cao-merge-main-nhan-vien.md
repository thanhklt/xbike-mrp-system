# Xử lý conflict ưu tiên main — 17/11/2026

Baseline nhánh: `3d421e4`; main đã fetch: `b228193`. Đã chạy merge thật với `--no-commit --no-ff`; chưa tạo merge commit hoặc push. Các kết quả dưới đây áp dụng cho working tree/index sau giải quyết xung đột, không phải trạng thái PR trên GitHub.

## Cách giải quyết 20 file

- Giữ các thay đổi không xung đột từ main, gồm tài liệu/spec/sequence mới, việc xóa các tài liệu cũ, CSS khoảng cách lỗi bộ lọc và màu JSON audit Admin, cùng năm unit test audit bổ sung.
- Bốn file phieu_xuat (ports/repository/router/service): đối chiếu trực tiếp HEAD với main để xác nhận phần chênh chỉ là hai GET đã chốt và chế độ đọc không khóa. Giữ nghiệp vụ ghi, quyền, khóa/transaction main; vẫn có lookup/preview cho NV. Schema không xung đột và không thay SQL bootstrap/DB.
- Collection, ResourceFields, Dashboard, RequestsPage, MainLayout, Sidebar/CSS và routes: giữ nền main v4 cùng các tùy chỉnh Nhân viên đã được người dùng yêu cầu (bộ lọc thu gọn, bỏ mũi tên, theme/sidebar NV, đơn vị tính, lookup/preview và popup không kéo ngang). So với HEAD trước merge, production frontend chỉ thêm hai khối CSS của main nêu trên; các tính năng NV không bị dựng lại hoặc đổi nghiệp vụ.
- MyDocumentsPage tiếp tục xóa và `/nv/phieu` redirect sang yêu cầu theo quyết định đã chốt. Không phục hồi trang gọi GET danh sách phiếu QLK-only cho NV. Các URL chi tiết phiếu theo ID vẫn mở được.
- Giữ năm file test xung đột theo hành vi đã chốt, bao gồm các assertion ETag/quyền/error và test route/nhãn không mũi tên. Test audit mới từ main được nhận đầy đủ; không xóa hoặc làm yếu test để merge xanh.
- MISSING.md được giữ vì người dùng yêu cầu theo dõi phần thiếu; liên kết quy tắc chuyển sang AGENTS.md do main đã xóa FRONTEND_RULES.md. Không phục hồi các tài liệu Admin cũ bị main xóa.
- Sequence phieu_xuat dùng bản chi tiết sáu endpoint v4 của main, bổ sung hai GET mới và sửa mô tả số endpoint/auth theo code hiện tại. Giữ các nhánh khóa/ghi sổ/rollback/replay của tài liệu main.

## Kiểm chứng

- Không còn file unmerged; không còn marker conflict trong backend/app, frontend/src và frontend/tests.
- `git diff --cached --check` đạt. Chênh lệch backend/infra so main chỉ có phần bổ sung API đọc và test đã được chốt; Dockerfile cục bộ nằm ngoài index.
- Unit frontend: **287/287 pass**, exit 0; gồm năm test audit mới từ main.
- Lint frontend đạt; build đạt (24.84 giây), exit 0.
- Ruff sáu file backend/test liên quan đạt, dùng `--no-cache` trên mount chỉ đọc.
- Browser chín file (employee-ui, employee-request-filters, issue-main-flow, navigation, sidebar, workflows, record-dialog, admin-ui, request-check-layout): **90/90 pass**, 5.0 phút, exit 0.
- Backend bốn file phieu_xuat reads/api/service/postgres: **75/75 pass**, 204.42 giây, exit 0, trên PostgreSQL test thật.
- Log unit/browser/backend lưu tại [bằng chứng merge](./ui-nhan-vien-evidence/merge-main-20261117/). Đây là lượt kiểm chứng sau giải quyết conflict, không cộng dồn các lượt cũ. Chưa render Mermaid bằng CLI; đã đối chiếu sequence với code.

## Dữ liệu và trạng thái bàn giao

Đã lưu bản Dockerfile cục bộ và patch trước merge dưới thư mục backup ghi tại `%TEMP%/xbike-main-merge-location.txt`; kiểm hash xác nhận Dockerfile không đổi và không đưa vào staged merge. Các ảnh/tài liệu untracked của người dùng giữ nguyên.

Backend tests dùng PostgreSQL riêng `xbike-merge-test-20261117` cổng 55465 và database UUID của fixture; không dùng DB ứng dụng. Không reset/seed DB ứng dụng. Frontend/backend Docker được tạm dừng khi file còn conflict, sau đó bật lại; backend 8000 và frontend 5173 trả HTTP 200.

MERGE_HEAD vẫn là main `b228193`. Cần người dùng cho phép tạo merge commit rồi push để PR nhận kết quả; cho đến lúc đó, GitHub vẫn đánh giá trên commit cũ. Chưa tự accept hoặc merge PR vào main. Không chạy lại browser E2E có ghi dữ liệu thật trong lượt hợp nhất này; kết quả E2E trước merge vẫn là bằng chứng lịch sử riêng.
