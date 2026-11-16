# Rà soát trước push UI Nhân viên — 17/11/2026

Kết luận review ban đầu: chưa sẵn sàng commit/push toàn bộ index. Các phát hiện gốc được giữ bên dưới; kết quả sửa tiếp theo ghi tại mục cập nhật sau đây. Đây là review source/index, không thay cho nghiệm thu hoặc E2E backend.

## Cập nhật sau khi dev yêu cầu sửa theo main — 17/11/2026

- Đã đồng bộ source backend/infra đúng main `b228193`; `git diff --cached --name-only origin/main -- backend infra` không còn khác biệt. Working tree chỉ giữ dòng sửa `backend/Dockerfile` có sẵn của người dùng; không stage dòng này. Đã kiểm tra remote main vẫn là SHA trên.
- Đã bỏ các file backend cũ bị main xóa và stage việc xóa hai trang lệnh/hoàn thành cũ. Đồng bộ các sửa frontend mới vào index, thêm helper/test mới theo đúng phạm vi; không gom ảnh nguồn hoặc tài liệu untracked không liên quan.
- Đã bỏ nguồn danh sách QLK-only khỏi điều hướng NV, redirect các URL danh sách cũ về yêu cầu. Nhân viên vẫn mở được phiếu cụ thể qua URL có ID và sau khi tạo.
- Phiếu xuất: NV được giao tạo với body chỉ `{loai_phieu, yeu_cau_san_xuat_id}`; dòng hàng server chốt chỉ đọc; gửi/gửi lại dùng body rỗng + ETag phiếu; QLK chỉ duyệt/từ chối. Không PATCH/DELETE/ve_nhap. Điều kiện loại yêu cầu/hoàn thành theo main.
- Đã khôi phục artwork và CSS ảnh Admin từ main; giữ style Nhân viên độc lập. Popup gửi phiếu dùng bảng tối và giữ số lượng trong viewport mobile.
- Kiểm chứng cuối: **282/282 unit**, lint exit 0, build exit 0; **84/84 browser tests** trong một lượt chạy cuối (3.3 phút, exit 0), gồm 8 file admin-ui, employee-ui, employee-request-filters, issue-main-flow, navigation, sidebar, workflows, record-dialog. Log tại `doc/ui-nhan-vien-evidence/main-v4-20261117/browser.log`; lượt đầu 78/84 với 6 selector/luồng cũ được giữ trong `browser-first.log`, không dùng kết quả này làm bằng chứng lượt cuối.
- 18 ảnh mới: [mục lục main-fixed](./ui-nhan-vien-screenshots/2026-11-17-main-fixed/README.md). Đã mở xem trực tiếp ảnh đại diện; không gọi đó là kiểm tra thủ công toàn bộ 18 ảnh.
- Còn mở NV-MAIN-005/006: backend chưa có lookup ID phiếu theo yêu cầu cho NV hoặc preview dòng nhu cầu trước tạo nháp. Tạo trùng hiển thị 409, không tự đoán ID/đọc danh sách trái quyền. Không báo hai phần này đã đủ UC-34/37.
- Chưa tạo merge commit nên main chưa là ancestor của HEAD; chưa commit/push/accept. Chuẩn bị source/index không đồng nghĩa đã hợp nhất lịch sử Git. Chưa chạy API/DB thật, SQL/seed/reset hoặc backend tests dùng DB.

## Phát hiện tại thời điểm review ban đầu (lịch sử trước sửa)

Mốc: HEAD `5d6e207`, origin/main `b228193`. Tại thời điểm kiểm tra có 242 file staged và 26 file thay đổi chưa staged, ngoài ra còn các file chưa theo dõi. Không có conflict marker/unmerged path; không có MERGE_HEAD và main chưa là ancestor của HEAD. Vì vậy không được gọi trạng thái này là merge main đã hoàn tất.

## Phát hiện cần xử lý

### 1. P1 — Bootstrap DB không khớp ORM đã nhập từ main

- `infra/postgres/init.sql:1` vẫn ghi schema v3.1. SQL còn mô hình `LenhSanXuat` (`:168`) và FK chứng từ theo lệnh (`:607`).
- ORM hiện tại yêu cầu `MatHang.so_luong_dang_giu`/cột tính `so_luong_con_dung` tại `backend/app/modules/mat_hang/models.py:56`, `NhanVien.phien_ban_dang_nhap` tại `backend/app/modules/nhan_vien/models.py:59`, và hạn yêu cầu tại `backend/app/modules/san_xuat/models.py:77`. Bootstrap hiện tại không đồng bộ các cột này.
- Index khác main ở cả `infra/postgres/init.sql`, `seed.sql`, `docker-compose.yml` (port mặc định 5433 thay vì 5432). Đây là source tích hợp chưa đồng nhất, không có bằng chứng DB đang chạy đã được cập nhật.
- Cần: đối chiếu và lấy đúng bộ bootstrap/config của main trong phạm vi tích hợp đã chốt; giữ riêng các thay đổi môi trường có chủ đích, không chạy SQL/seed/reset DB để sửa vấn đề này.

### 2. P1 — Chưa thể commit nguyên index: còn phiên bản cũ và thiếu thay đổi UI mới

- Hai trang `frontend/src/features/production/{ProductionPage,CompletionsPage}.jsx` đã bị xóa trong working tree nhưng việc xóa chưa staged. Commit index hiện tại sẽ còn các trang cũ.
- So với main, index còn giữ 6 file backend đã bị main xóa: 4 file `inventory/{models,router,schemas,service}.py` và 2 file `san_xuat/{repository,service}/lenh_san_xuat.py`.
- Các sửa nhãn, format đơn vị, bộ lọc, style và test mới chưa đồng bộ hết vào index. Hai test mới `employee-request-filters.spec.js`, `unit-label.test.js` còn untracked.
- Cần: hoàn tất tích hợp với lịch sử main đúng cách và rà index cuối; bảo toàn Dockerfile của người dùng, ảnh và tài liệu chưa theo dõi. Không dùng `git add .` để gom cả nội dung ngoài phạm vi.

### 3. P1 — Các đường dẫn phiếu xuất của NV gọi API danh sách bị cấm

- `frontend/src/features/dashboard/DashboardPage.jsx:617`–619 liên kết tới các trang danh sách phiếu; `production/MyDocumentsPage.jsx:33` và `material-issuing/MaterialIssuingPage.jsx:38` gọi `useCollection(API.issues)`.
- `backend/app/modules/phieu_xuat/router.py:73` yêu cầu WriteActor cho GET danh sách; WriteActor là Quản lý tại `:48`. NV được GET chi tiết, không được GET danh sách.
- Fixture hiện trả 403 đúng tại `frontend/tests/browser/api-fixture.js:519`. Đây là khoảng trống đã được ghi NV-MAIN-001, chưa có quyết định sản phẩm, không phải endpoint mới bị thiếu do sửa style.
- Cần: chốt bỏ/đổi đường dẫn danh sách cho NV hoặc mở phạm vi backend riêng. Không thay fixture thành thành công để che lỗi.

### 4. P1 — UI phiếu xuất còn quyền và request body theo hợp đồng cũ

- `frontend/src/features/auth/permissions.js:17`–19 gán quyền viết phiếu xuất cho Quản lý; backend hiện cho NV tạo/gửi (`phieu_xuat/router.py:105`, `:127`). Nhãn dashboard tại `DashboardPage.jsx:614` nói Quản lý lập phiếu, trái source backend hiện tại.
- `MaterialIssuingPage.jsx:224`–238 còn gửi `chi_tiet` khi tạo và PATCH khi sửa. `PhieuXuatCreate` tại `backend/app/modules/phieu_xuat/schemas.py:32` chỉ nhận loại phiếu + mã yêu cầu, `extra="forbid"`; router không có PATCH phiếu xuất. Tạo có thể 422 và sửa không có endpoint tương ứng.
- Các nhánh `xuat_vat_tu` tại `MaterialIssuingPage.jsx:116`, `:257` còn khác enum `xuat_linh_kien` của main, có thể gắn nhãn phiếu linh kiện thành thành phẩm.
- Cần: chốt NV-MAIN-002 rồi tích hợp đúng schema/quyền main, không tự cấp quyền duyệt NV. Đây là bất nhất hợp đồng còn sót trong mã tích hợp; không quy toàn bộ cho các sửa giao diện gần đây.

### 5. P2 — Hồi quy ảnh sidebar Admin so với main

- Main dùng `frontend/src/assets/images/admin/sidebar-artwork.webp`; working tree không có asset này.
- `frontend/src/layouts/Sidebar.jsx:28` đổi import Admin thành `doc/ui-spec-admin/tong_quan.png` và `Sidebar.module.css:309` đổi ảnh Admin thành rộng cố định 1684px/cắt vị trí. Các sửa này tác động Admin, vượt mục tiêu bảo toàn giao diện Admin khi sửa NV.
- Cần: giữ artwork và CSS Admin của main, giới hạn style ảnh xe đạp trong selector employee; kiểm lại ảnh Admin desktop/mobile.

### 6. P2 — Test xanh và tài liệu ảnh đang nói quá bằng chứng

- Chạy lại `NV-04` đạt 1/1 dù fixture chặn danh sách phiếu xuất 403. Test tại `frontend/tests/browser/employee-ui.spec.js:185` chỉ kiểm nút tab/params/request, không kiểm dữ liệu tải thành công hoặc lỗi quyền. Nó không chứng minh Phiếu của tôi hoạt động.
- Mục lục ảnh `doc/ui-nhan-vien-screenshots/2026-11-17-main-preview/README.md:3` tuyên bố hoàn thành di trú trong khi các lỗi trên còn mở; mô tả quyền/độ hoàn chỉnh cần đối chiếu lại bản fixture sau sửa.
- Cần: kiểm trạng thái giao diện/response đúng quyền, báo riêng ảnh fixture và tích hợp runtime; không xóa assertion hoặc nới quyền fixture để làm test xanh. Cập nhật MISSING và đặc tả theo quyết định đã được người dùng xác nhận.

## Kiểm chứng trong lượt review

- `npm.cmd run test`: 280/280 pass, exit 0; log `frontend/test-results/review-unit-current.log`.
- `npx.cmd playwright test tests/browser/employee-ui.spec.js --grep NV-04`: 1/1 pass, exit 0; giới hạn như phát hiện 6.
- Không còn marker conflict hoặc unmerged path. `git diff --cached --check` còn cảnh báo whitespace trong tài liệu UC và dòng trống cuối test nhập từ main; không phải nguyên nhân nghiệp vụ ở trên.
- Lint/build và bộ lọc desktop/mobile đã đạt trong lượt sửa trước; không coi đó là E2E toàn bộ main. Review này không chạy DB/API thật hoặc backend tests có thể dùng DB.

## Thứ tự sửa đề xuất

1. Đồng bộ snapshot/lịch sử main và bootstrap, bảo toàn thay đổi người dùng; rà cả index lẫn working tree.
2. Chốt các mục NV-MAIN về menu/phiếu xuất, sửa quyền và payload theo hợp đồng.
3. Khôi phục phần Admin ngoài phạm vi và bổ sung kiểm chứng hành vi cho các trang bị 403.
4. Chạy các gate frontend phù hợp, cập nhật tài liệu bằng bằng chứng mới, trình danh sách commit cụ thể để người dùng cho phép commit/push.

Không sửa source/stage, commit, push, chạy SQL hoặc thay đổi dữ liệu trong lượt review này; chỉ thêm báo cáo này.
