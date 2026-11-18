# Bổ sung API phiếu xuất và kiểm chứng demo — 17/11/2026

Baseline `03fb878`; các sửa đổi trong báo cáo này chưa commit/push. Dev chốt làm hai API phiếu xuất và kiểm thử trước, giữ hiện tại với avatar ảnh, badQty/note và ngưỡng tồn tối thiểu.

## Hành vi mới

- GET `/api/v1/phieu_xuat/theo_yeu_cau/{id}` trả danh sách tham chiếu phiếu thuộc đúng yêu cầu cho NV được giao hoặc QLK. Yêu cầu đã hoàn thành vẫn mở lại phiếu được; danh sách toàn bộ phiếu vẫn QLK-only.
- GET `/api/v1/phieu_xuat/xem_truoc/{id}?loai_phieu=...` cho NV được giao đọc nhu cầu đã chốt. Cùng validation nguồn/loại mặt hàng với POST, giao dịch chỉ đọc không khóa/ghi. Catalog thật bổ sung tên/mã/đơn vị trên UI. Không thay schema DB, payload tạo hoặc quyền duyệt.
- UI yêu cầu hiển thị link phiếu hiện có sau refresh. Form tạo đọc lookup trước, hiện preview với loading/error/retry; chưa tải thành công thì không lưu. Tạo cạnh tranh bị 409 tải lại nguồn/tham chiếu, mở phiếu hiện có nếu tìm được; không tự ghi lại. Nếu nguồn đã đổi trạng thái, tải lại nguồn để chặn lưu theo điều kiện mới.
- Đã thay sequence v3 cũ bằng tám endpoint thực có trên source hiện tại tại `docs/sequence/phieu_xuat.md`; không mô tả PATCH/DELETE/ve_nhap như API đang hoạt động.

## Kiểm chứng

- Backend: **75/75 pass**, 102.25 giây, exit 0; bốn file reads/api/service/postgres của phieu_xuat, dùng PostgreSQL test thật. Trong đó 4 ca mới kiểm quyền, query, lookup rỗng/đã có/yêu cầu hoàn thành, GET không ghi, preview khớp POST và thay đổi trạng thái trước tạo.
- Frontend unit: **282/282 pass**, exit 0. Lint và build cuối đạt, build 21.65 giây. Chưa render Mermaid bằng CLI; đã đối chiếu sơ đồ với router/service/repository/dependency.
- Browser phiếu xuất sau sửa: **8/8 pass**, 34.4 giây, exit 0; gồm mở lại sau refresh, 409 cạnh tranh, preview delayed/error/retry và không tạo nháp khi đóng.
- Bộ browser cuối gồm tám file employee-ui, employee-request-filters, issue-main-flow, navigation, sidebar, workflows, record-dialog và admin-ui: **86/86 pass**, 4.6 phút, exit 0. Đây là lượt sau sửa cuối, có hồi quy Admin/QLK; không cộng lượt 8/8 vào tổng này.
- Browser E2E backend thật: **1/1 pass**, 1.4 phút, exit 0. Hai NV và một QLK đăng nhập UI thật trong ba context riêng, không API mock. Đi qua preview → nháp → mở lại → gửi → duyệt linh kiện → bắt đầu SX → lập/gửi/duyệt hoàn thành → lập/gửi/duyệt thành phẩm → yêu cầu hoàn thành. NV thứ hai bị chặn phiếu không được giao.
- Đối chiếu DB test sau E2E: yêu cầu 5 hoàn thành, hai loại phiếu đều đã duyệt, chứng từ hoàn thành 7 đã duyệt; mặt hàng 1 tồn/giữ/còn dùng = 0/0/0. Số mặt hàng có số dư lệch sổ kho hoặc giữ hàng: **0**.

Lượt đầu backend có 2 lỗi dữ liệu test do chưa điền completed_at và dùng sai enum hủy; đã sửa dữ liệu test theo constraint, không nới schema/assertion. Lượt đầu 53 browser có 2 lỗi: preview thiếu đơn vị (đã bổ sung) và một lần trang trắng chưa tái hiện ở lượt kiểm riêng; không dùng lượt đó làm bằng chứng xanh. E2E thật đầu chờ popup xác nhận ở bước bắt đầu SX nhưng UI main gửi trực tiếp; đã sửa kịch bản theo handler thật và chạy lại trên database test mới. Output E2E tách khỏi output fixture để tránh lượt chạy khác dọn artifact.

## Môi trường và giới hạn

PostgreSQL test `xbike-nv-e2e-20261117`, database E2E `xbike_employee_e2e_20261117120538`; backend riêng `xbike-nv-e2e-api-20261117` tại localhost:8002, Vite test 5176. Schema/seed chỉ chạy trên DB test mới/trống; không chạy lại seed/reset DB ứng dụng trong đợt sửa missing. Các lượt backend từng ca dùng DB UUID và tự dọn qua fixture. Đợt tạo lại DB ứng dụng trước đó theo lựa chọn 3 được ghi riêng ở báo cáo DB.

Hướng dẫn chạy lại tại `frontend/tests/e2e/README.md`. Đây là một kịch bản demo thật, không phải mọi nhánh E2E hệ thống: còn browser thiếu vật tư/từ chối-gửi lại/hết phiên, accessibility đầy đủ và nghiệm thu của dev. Backend tests có kiểm rollback/cạnh tranh/từ chối-gửi lại nhưng không thay thế bằng chứng browser các nhánh đó. NV-CHECK-001/002/003 tiếp tục mở với giới hạn này.

Các file chính: module backend phieu_xuat (ports/repository/router/schemas/service); RequestsPage, MaterialIssuingPage; api-fixture/issue-main-flow; test_phieu_xuat_reads; config và test E2E riêng; MISSING, đặc tả và sequence. Không sửa Dockerfile có sẵn của dev. Không commit/push hoặc tự nghiệm thu.

Log được lưu trong [thư mục bằng chứng](./ui-nhan-vien-evidence/missing-20261117/): backend.txt (75 ca), browser-fixture.txt (86 ca), browser-live.txt (1 E2E thật), db-balances.txt (truy vấn sau E2E). Lint/build và 282 unit đã đọc kết quả thực tế qua terminal, không có log riêng trong thư mục này. Hai container test được dừng sau kiểm chứng; giữ dữ liệu test để đối chiếu, không dọn DB ứng dụng.
