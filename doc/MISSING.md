# Các phần còn thiếu khi triển khai frontend

Theo dõi các thành phần trong thiết kế mà API hoặc thông tin đã chốt chưa đáp ứng. Tuân thủ [quy tắc frontend](./FRONTEND_RULES.md); tiếp tục các phần độc lập đã rõ, hỏi dev về phần chưa rõ và không tự bổ sung chức năng.

File được khởi tạo cùng quy tắc frontend và được cập nhật trong đợt triển khai Admin UI (`feature/UI-admin`). Các khác biệt admin đã ghi trong [đặc tả giao diện admin](./dac-ta-giao-dien-admin.md) là căn cứ để đối chiếu khi triển khai.

## Danh sách

- [ ] FE-MISS-001 — Lưu lượng truy cập website theo giờ và bộ lọc khoảng thời gian
  - Màn hình / mã yêu cầu / ảnh thiết kế: ADM-01 Tổng quan (`OV-03`, `OV-04`, `OV-Q01`) — `tong_quan.png`.
  - Thành phần hoặc thao tác bị ảnh hưởng: Khối “Lưu lượng truy website”, bộ chọn `Hôm nay` / `7 ngày` / `30 ngày` và đường biểu diễn số lượng request theo giờ.
  - Thiết kế yêu cầu: Hiển thị biểu đồ đường màu cam kèm vùng tô phía dưới theo số lượng request mỗi giờ (`00h` đến `21h`) và chuyển đổi dữ liệu theo `Hôm nay`, `7 ngày`, `30 ngày`.
  - API hiện đáp ứng / còn thiếu: Backend hiện chỉ có các endpoint `/auth/*`, `/nhan_vien`, `/vai_tro`, `/audit` và các module nghiệp vụ kho/sản xuất; chưa có endpoint thống kê lưu lượng HTTP request hoặc metrics truy cập theo khung thời gian.
  - Bằng chứng: `frontend/src/lib/api/endpoints.js`, `backend/app/modules/nhan_vien/router.py`, `backend/app/modules/audit/router.py`.
  - Ảnh hưởng và phần vẫn tiếp tục làm được: Đã dựng đầy đủ khung thẻ “Lưu lượng truy website”, dòng mô tả “Tổng hợp theo số lượng request mỗi giờ”, trục tọa độ và 3 nút `Hôm nay` / `7 ngày` / `30 ngày` đúng hình thức ảnh nhưng chưa gắn hành động gọi API và không vẽ đường/số liệu giả.
  - Câu hỏi / quyết định cần dev xác nhận: Nguồn thu thập số liệu request, hợp đồng API trả về chuỗi thời gian, múi giờ tổng hợp và bước thời gian cho chế độ `7 ngày` / `30 ngày`.
  - Phản hồi của dev: Dev đã chốt trong `doc/admin-ui-plan.md` giữ khung và các nút `Hôm nay / 7 ngày / 30 ngày` chưa gắn hành động, không vẽ đường/số liệu giả và không thêm banner kỹ thuật.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Đã dựng UI khung và kiểm tra click không sinh request ngoài ý muốn (`frontend/tests/browser/admin-ui.spec.js`); giữ `[ ]` vì chưa có API lưu lượng.

- [ ] FE-MISS-002 — Trường mô tả vai trò và các API Tạo / Sửa / Xóa vai trò
  - Màn hình / mã yêu cầu / ảnh thiết kế: ADM-04 Quản lý vai trò (`ROL-03`, `ROL-04`, `ROL-05`, `ROL-06`, `ROL-Q01`..`ROL-Q04`) — `quan_ly_vai_tro.png`.
  - Thành phần hoặc thao tác bị ảnh hưởng: Cột “Mô tả” trong bảng vai trò; nút `+ Tạo vai trò`; nút `Sửa` và nút `Xóa` trên từng dòng vai trò.
  - Thiết kế yêu cầu: Hiển thị mô tả chi tiết cho từng vai trò, cho phép tạo vai trò mới, sửa thông tin vai trò và xóa các vai trò không phải mặc định.
  - API hiện đáp ứng / còn thiếu: `GET /api/v1/vai_tro` chỉ trả về `VaiTroRead` gồm `id`, `ma_vai_tro` (`Literal["nhan_vien", "quan_ly", "quan_tri_vien"]`), `ten_vai_tro` (không có trường `mo_ta`); `vai_tro_router` chỉ có `GET ""` và chưa có `POST`, `PATCH`/`PUT`, `DELETE` cho `/api/v1/vai_tro`.
  - Bằng chứng: `backend/app/modules/nhan_vien/schemas.py` (`RoleCode`, `VaiTroRead`, dòng 32 & 191–197), `backend/app/modules/nhan_vien/router.py` (`vai_tro_router`, dòng 28 & 247–254).
  - Ảnh hưởng và phần vẫn tiếp tục làm được: Đã dựng trang ADM-04 lấy danh sách vai trò thật từ `GET /api/v1/vai_tro`, hiển thị giá trị thiếu `—` cho cột “Mô tả” khi response chưa có `mo_ta`, giữ nút `+ Tạo vai trò` và `Sửa` đúng hình thức thiết kế nhưng chưa gắn hành động, và giữ trạng thái `disabled` kèm biểu tượng thông tin cho nút `Xóa` của 3 vai trò hệ thống.
  - Câu hỏi / quyết định cần dev xác nhận: Có bổ sung trường `mo_ta` vào bảng `"VaiTro"`/`VaiTroRead` và mở rộng CRUD vai trò động hay giữ cố định 3 vai trò hệ thống.
  - Phản hồi của dev: Dev đã chốt trong `doc/admin-ui-plan.md` chỉ hiển thị danh sách vai trò thật từ API, dùng cách hiển thị giá trị thiếu của project cho cột mô tả, giữ các nút thiếu API đúng hình thức và chưa gắn hành động.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Đã dựng UI ADM-04 và kiểm tra bằng Playwright (`frontend/tests/browser/admin-ui.spec.js`); giữ `[ ]` vì backend chưa có trường `mo_ta` và endpoint ghi vai trò.

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
  - Thành phần hoặc thao tác bị ảnh hưởng: Nút “Đặt lại mật khẩu…” trong phần trạng thái tài khoản của form chỉnh sửa.
  - Thiết kế yêu cầu: Bộ 5 ảnh thiết kế không yêu cầu chức năng đặt lại mật khẩu; đây là nút đã tồn tại sẵn trong form chỉnh sửa của project được dev đồng ý giữ nguyên trạng thái disabled và hành vi bảo vệ hiện có (backend hiện chỉ có `/api/v1/auth/doi_mat_khau` yêu cầu mật khẩu hiện tại của chính người đang đăng nhập).
  - API hiện đáp ứng / còn thiếu: `backend/app/modules/nhan_vien/router.py` chưa có endpoint đặt lại mật khẩu nhân viên theo `{id}`.
  - Bằng chứng: `backend/app/modules/nhan_vien/router.py`, `frontend/src/features/auth/UsersPage.jsx`.
  - Ảnh hưởng và phần vẫn tiếp tục làm được: Giữ nguyên nút `Đặt lại mật khẩu…` ở trạng thái vô hiệu hóa kèm lý do rõ ràng như logic bảo vệ sẵn có của project.
  - Câu hỏi / quyết định cần dev xác nhận: Có bổ sung API đặt lại mật khẩu cho admin trong đợt sau hay không.
  - Phản hồi của dev: Dev đã chốt trong `doc/admin-ui-plan.md` giữ các trạng thái disabled và chặn an toàn hiện có.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Giữ nguyên trạng thái bảo vệ hiện có; giữ `[ ]` vì chưa có API.

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
