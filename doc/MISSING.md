# Các phần còn thiếu khi triển khai frontend

Theo dõi các thành phần trong thiết kế mà API hoặc thông tin đã chốt chưa đáp ứng. Tuân thủ [quy tắc frontend](./FRONTEND_RULES.md); tiếp tục các phần độc lập đã rõ, hỏi dev về phần chưa rõ và không tự bổ sung chức năng.

File được khởi tạo cùng quy tắc frontend và được cập nhật trong đợt triển khai Admin UI (`feature/UI-admin`). Các khác biệt admin đã ghi trong [đặc tả giao diện admin](./dac-ta-giao-dien-admin.md) là căn cứ để đối chiếu khi triển khai.

## Danh sách

- [x] FE-MISS-001 — Lưu lượng truy cập website theo giờ và bộ lọc khoảng thời gian
  - Màn hình / mã yêu cầu / ảnh thiết kế: ADM-01 Tổng quan (`OV-03`, `OV-04`, `OV-Q01`) — `tong_quan.png`.
  - Thành phần hoặc thao tác bị ảnh hưởng: Khối “Lưu lượng truy website”, bộ chọn `Hôm nay` / `7 ngày` / `30 ngày` và đường biểu diễn số lượng request theo giờ.
  - Thiết kế yêu cầu: Hiển thị biểu đồ đường màu cam kèm vùng tô phía dưới theo số lượng request mỗi giờ (`00h` đến `21h`) và chuyển đổi dữ liệu theo `Hôm nay`, `7 ngày`, `30 ngày`.
  - API hiện đáp ứng / còn thiếu: Backend hiện chỉ có các endpoint `/auth/*`, `/nhan_vien`, `/vai_tro`, `/audit` và các module nghiệp vụ kho/sản xuất; chưa có endpoint thống kê lưu lượng HTTP request hoặc metrics truy cập theo khung thời gian.
  - Bằng chứng: `frontend/src/lib/api/endpoints.js`, `backend/app/modules/nhan_vien/router.py`, `backend/app/modules/audit/router.py`.
  - Ảnh hưởng và phần vẫn tiếp tục làm được: Đã dựng đầy đủ khung thẻ “Lưu lượng truy website”, dòng mô tả “Tổng hợp theo số lượng request mỗi giờ”, trục tọa độ và 3 nút `Hôm nay` / `7 ngày` / `30 ngày` đúng hình thức ảnh nhưng chưa gắn hành động gọi API và không vẽ đường/số liệu giả.
  - Câu hỏi / quyết định cần dev xác nhận: Nguồn thu thập số liệu request, hợp đồng API trả về chuỗi thời gian, múi giờ tổng hợp và bước thời gian cho chế độ `7 ngày` / `30 ngày`.
  - Phản hồi của dev: Đợt UI admin trước đó, dev đã chốt trong `doc/admin-ui-plan.md` giữ khung và các nút chưa gắn hành động. Ngày 09/11/2026, dev chốt cho backend tuân theo frontend và duyệt `.handoff/plan-luu-luong-truy-cap.md`. Nội dung đã chốt (ghi tại `docs/DECISION.md` D-LL-01):
    - số liệu lưu vào bảng `"LuuLuongTruyCap"` theo từng giờ;
    - `Hôm nay` có 24 điểm theo giờ, nhãn hiện mỗi 3 giờ;
    - `7 ngày` có 7 điểm theo ngày;
    - `30 ngày` có 30 điểm theo ngày, kèm đường trung bình trượt 7 ngày và chú giải;
    - luôn hiện hôm nay với số đếm đến hiện tại;
    - trục Y tuyến tính, tối thiểu 4.000;
    - dòng mô tả đổi giữa "mỗi giờ" và "mỗi ngày" theo bộ lọc.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục:
    - Backend: thêm module `backend/app/modules/luu_luong/` (middleware đếm request, `GET /api/v1/luu_luong_truy_cap` chỉ cho `quan_tri_vien`) và bảng mới trong `infra/postgres/init.sql`. Kiểm tra bằng `backend/tests/test_luu_luong_api.py`, 14/14 test qua trên DB `xbike_mrp_test`.
    - Frontend: gắn 3 nút vào API và vẽ đường cam có vùng tô trong `DashboardPage.jsx` (`TrafficCard`). Test `frontend/tests/browser/admin-ui.spec.js` (ADM-01) qua.
    - Tài liệu: `docs/sequence/luu_luong.md`, `docs/api_contract_v3.md` §3 và §13.
    - Giới hạn: database đang chạy chưa có bảng mới cho tới khi khởi tạo lại từ `init.sql`.

- [x] FE-MISS-002 — Trường mô tả vai trò và phạm vi Tạo / Sửa / Xóa vai trò
  - Màn hình / mã yêu cầu / ảnh thiết kế: ADM-04 Quản lý vai trò (`ROL-03`, `ROL-04`, `ROL-05`, `ROL-06`, `ROL-Q01`..`ROL-Q04`) — `quan_ly_vai_tro.png`.
  - Thành phần hoặc thao tác bị ảnh hưởng: Cột “Mô tả” trong bảng vai trò; nút `+ Tạo vai trò`; nút `Sửa` và nút `Xóa` trên từng dòng vai trò.
  - Thiết kế gốc: Hiển thị mô tả cho từng vai trò và thao tác tạo/sửa/xóa. Phạm vi đã được dev điều chỉnh tại D-VT-01 (09/11/2026).
  - API hiện đáp ứng: `GET /api/v1/vai_tro` trả `VaiTroRead` gồm `id`, `ma_vai_tro`, `ten_vai_tro`, `mo_ta` (`string | null`); admin/quản lý được đọc, nhân viên nhận 403. Không hỗ trợ API ghi vai trò vì bộ vai trò cố định theo SRS_v4 §2.
  - Bằng chứng: `backend/app/modules/nhan_vien/models.py`, `schemas.py`, `router.py`; `infra/postgres/init.sql`, `seed.sql`; `docs/api_contract_v3.md` §4; `docs/sequence/nhan_vien.md`.
  - Hành vi đã triển khai: ADM-04 hiển thị mô tả từ API, null hiển thị `—`, tìm theo mô tả; nút `+ Tạo vai trò` disabled và mờ 0.55; giữ Sửa/Xóa vô hiệu hóa theo mã của ba vai trò hệ thống, kèm icon thông tin.
  - Quyết định đã chốt: Không mở CRUD vai trò động hoặc thay cơ chế phân quyền; không có form tạo/sửa/xóa.
  - Phản hồi của dev: Duyệt `.handoff/plan-vai-tro-mo-ta.md`: (1) giữ ba vai trò cố định, mô tả chỉ đọc; (2) giữ Sửa vô hiệu hóa; (3) seed theo SRS_v4 §2; (4) cột `mo_ta varchar(255) NULL`; (5) Tạo disabled và mờ; (6) đóng FE-MISS-002 và ghi D-VT-01, đóng ROL-Q01..Q04. Trong phiên triển khai, dev chọn test backend tạm và đồng ý kiểm tra UI trực tiếp thay hai skill ui-consistency không có sẵn.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: 14/14 ca backend tạm đạt trên PostgreSQL test riêng, bao gồm mô tả/null, quyền 401/403, ghi trả 405, phân trang, đăng nhập và hồ sơ; bootstrap nguyên bản init/seed thành công trên container tạm, ba mô tả dài 135/136/124 ký tự. Playwright ADM-04 đạt: mô tả đúng, tìm “BOM” còn Quản lý kho, null hiện `—`, Tạo disabled và không phát sinh request. Đóng theo D-VT-01, không phải xác nhận chức năng ghi vai trò đã được bổ sung.
  - Giới hạn triển khai: Chưa thay đổi DB ứng dụng; backend mới cần cột `mo_ta`, nếu DB cũ thiếu cột thì đăng nhập và mọi request có token có thể trả 500. Chỉ bootstrap DB mới/trống, không migration. Contract/data model trên Drive cần dev cập nhật riêng.

- [ ] FE-MISS-003 — Ảnh đại diện (avatar) nhân viên
  - Màn hình / mã yêu cầu / ảnh thiết kế: Khung dùng chung (`LAY-08`), ADM-02 Quản lý tài khoản (`ACC-04`), ADM-03 Chi tiết tài khoản (`DET-04`, `DET-Q03`) — `quan_ly_tai_khoan.png`, `chi_tiet_tai_khoan.png`.
  - Thành phần hoặc thao tác bị ảnh hưởng: Avatar tròn ở góc trên bên phải, trong cột “Tên” của bảng tài khoản và trong thẻ nhận diện bên trái trang chi tiết tài khoản.
  - Thiết kế yêu cầu: Hiển thị ảnh chân dung tròn của người dùng/nhân viên.
  - API hiện đáp ứng / còn thiếu: `NhanVienRead` và `NhanVienAssignmentRead` không có trường URL/định danh ảnh đại diện và backend không có endpoint tải ảnh lên.
  - Bằng chứng: `backend/app/modules/nhan_vien/schemas.py` (`NhanVienAssignmentRead`, `NhanVienRead`, dòng 56–76).
  - Ảnh hưởng và phần vẫn tiếp tục làm được: Hiển thị avatar tròn với chữ cái viết tắt từ họ tên/tên đăng nhập (`initials`), không dùng ảnh người giả và không tự thêm tính năng upload.
  - Câu hỏi / quyết định cần dev xác nhận: Có bổ sung trường ảnh đại diện vào hồ sơ nhân viên trong các giai đoạn sau hay giữ avatar chữ cái.
  - Phản hồi của dev: Dev đã chốt trong `doc/admin-ui-plan.md` dùng avatar chữ cái hiện có khi chưa có ảnh nhân viên, không thêm upload ảnh hoặc dùng ảnh người giả.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Đã áp dụng đồng bộ trên header, danh sách và chi tiết tài khoản; giữ `[ ]` đối với trường dữ liệu ảnh đại diện từ API.

- [ ] FE-MISS-004 — Nội dung chi tiết sự kiện trong bảng Hoạt động gần đây cho vai trò Quản trị viên
  - Màn hình / mã yêu cầu / ảnh thiết kế: ADM-01 Tổng quan (`OV-07`, `OV-08`, `OV-Q03`) — `tong_quan.png`.
  - Thành phần hoặc thao tác bị ảnh hưởng: Cột “Hành động” và “Chi tiết” của bảng “Hoạt động gần đây”.
  - Thiết kế yêu cầu: Hiển thị câu mô tả giàu ngữ cảnh nghiệp vụ (ví dụ tên đối tượng được tạo/cập nhật hoặc chi tiết thay đổi cụ thể).
  - API hiện đáp ứng / còn thiếu: Với vai trò `quan_tri_vien`, `GET /api/v1/audit` trả về `AuditLogSummary` gồm `id`, `nhan_vien_id`, `loai_doi_tuong`, `doi_tuong_id`, `thao_tac`, `ly_do`, `created_at` và chủ đích lược bỏ `du_lieu_truoc`/`du_lieu_sau` để bảo mật dữ liệu nghiệp vụ kho/sản xuất.
  - Bằng chứng: `backend/app/modules/audit/schemas.py` (`AuditLogSummary`, dòng 19–60), `backend/app/modules/audit/service.py` (`list_entries`, dòng 18–25).
  - Ảnh hưởng và phần vẫn tiếp tục làm được: Đã dựng bảng 4 cột (`Thời gian`, `Người thực hiện`, `Hành động`, `Chi tiết`), kết hợp danh sách nhân viên (`GET /api/v1/nhan_vien`) để hiển thị họ tên người thực hiện và mã/tên nhân viên mục tiêu khi `loai_doi_tuong === "nhan_vien"`, kèm `ly_do` nếu có; với các đối tượng nghiệp vụ khác hiển thị loại đối tượng và `#doi_tuong_id` từ dữ liệu thật.
  - Câu hỏi / quyết định cần dev xác nhận: Có bổ sung trường tóm tắt công khai (không lộ snapshot nhạy cảm) từ backend cho bảng hoạt động gần đây hay giữ cách hiển thị từ `AuditLogSummary` hiện tại.
  - Phản hồi của dev: Dev đã chốt trong `doc/admin-ui-plan.md` dùng response thực và dữ liệu nhân viên có quyền đọc để hiển thị tên khi có, không tự bịa nội dung sự kiện hoặc lấy thêm trường bị hạn chế.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Đã triển khai và kiểm thử trên ADM-01; giữ `[ ]` cho phần mô tả chi tiết ngoài phạm vi `AuditLogSummary`.

- [ ] FE-MISS-005 — Đặt lại mật khẩu nhân viên dành cho Quản trị viên
  - Màn hình / mã yêu cầu / ảnh thiết kế: ADM-03 Chi tiết tài khoản / Chế độ chỉnh sửa (`DET-Q02`).
  - Thành phần hoặc thao tác bị ảnh hưởng: Hàng “Mật khẩu” ở trang chi tiết tài khoản khi ở chế độ xem và chế độ chỉnh sửa trực tiếp.
  - Thiết kế yêu cầu: Bộ ảnh thiết kế (`chi_tiet_tai_khoan.png`, `01-chinh-sua-truc-tiep.png`) hiển thị hàng “Mật khẩu” chỉ đọc bằng dấu chấm cố định (`••••••••`) và không có chức năng đặt lại mật khẩu nhân viên (backend hiện chỉ có `/api/v1/auth/doi_mat_khau` yêu cầu mật khẩu hiện tại của chính người đang đăng nhập).
  - API hiện đáp ứng / còn thiếu: `backend/app/modules/nhan_vien/router.py` chưa có endpoint đặt lại mật khẩu nhân viên theo `{id}`.
  - Bằng chứng: `backend/app/modules/nhan_vien/router.py`, `frontend/src/features/auth/UsersPage.jsx`.
  - Ảnh hưởng và phần vẫn tiếp tục làm được: Theo thiết kế chỉnh sửa trực tiếp (`doc/admin-ui-inline-edit-plan.md`), đã bỏ khối form phụ bên dưới và giữ hàng `Mật khẩu` ở trạng thái chỉ đọc (`••••••••`) trong cả chế độ xem lẫn chỉnh sửa trực tiếp, không tạo thao tác đặt lại mật khẩu khi chưa có API.
  - Câu hỏi / quyết định cần dev xác nhận: Có bổ sung API đặt lại mật khẩu cho admin trong đợt sau hay không.
  - Phản hồi của dev: Dev đã chốt trong `doc/admin-ui-plan.md` và `doc/admin-ui-inline-edit-plan.md` giữ hàng mật khẩu chỉ đọc `••••••••` và thay khối form phụ bằng chỉnh sửa trực tiếp trên 10 hàng chi tiết.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Đã kiểm tra bằng Playwright (`frontend/tests/browser/admin-ui.spec.js`); giữ `[ ]` vì chưa có API đặt lại mật khẩu nhân viên cho admin.

## Mẫu ghi nhận

Mẫu sau chưa phải một vấn đề đã được xác minh:

```markdown
- [ ] FE-MISS-<số> — <Tên phần thiếu>
  - Màn hình / mã yêu cầu / ảnh thiết kế: ...
  - Thành phần hoặc thao tác bị ảnh hưởng: ...
  - Thiết kế yêu cầu: ...
  - API hiện đáp ứng / còn thiếu: ...
  - Bằng chứng: <method + endpoint, trường dữ liệu, đường dẫn source hoặc hợp đồng API; ghi Chưa xác minh nếu chưa đủ căn cứ>
  - Ảnh hưởng và phần vẫn tiếp tục làm được: ...
  - Câu hỏi / quyết định cần dev xác nhận: ...
  - Phản hồi của dev: Chưa có.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Chưa hoàn tất.
```

Giữ `[ ]` khi còn thiếu hoặc đang chờ phản hồi. Chỉ đổi thành `[x]` theo điều kiện bàn giao trong quy tắc frontend và giữ lại nội dung để đối chiếu.
