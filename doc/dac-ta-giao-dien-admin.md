# Đặc tả giao diện Admin — xBike MRP

Ngày lập: 07/11/2026. Phạm vi: giao diện desktop trong 5 ảnh được dev xác nhận sử dụng. Tài liệu này mô tả giao diện đích và ghi nhận phần đã có trong code; chưa phải biên bản nghiệm thu.

## 1. Nguồn và cách đọc checklist

Nguồn thiết kế: [ui-spec-admin-20261107T125526Z-1-001.zip](./ui-spec-admin-20261107T125526Z-1-001.zip). Các ảnh nằm trong thư mục `ui-spec-admin/` bên trong ZIP.

| Mã màn hình | Ảnh nguồn | Nội dung |
| --- | --- | --- |
| ADM-01 | `tong_quan.png` | Tổng quan quản trị |
| ADM-02 | `quan_ly_tai_khoan.png` | Danh sách và thao tác tài khoản |
| ADM-03 | `chi_tiet_tai_khoan.png` | Chi tiết tài khoản |
| ADM-04 | `quan_ly_vai_tro.png` | Danh sách và thao tác vai trò |
| ADM-05 | `popup_xac_nhan.png` | Xác nhận thay đổi thông tin tài khoản |

Quy ước trạng thái áp dụng cho từng yêu cầu, không đánh dấu hoàn thành toàn bộ màn hình chỉ vì đã có route:

- `[x]`: đã triển khai trong source và đã chạy kiểm thử tự động / chụp ảnh đối chiếu ở phía AGY; việc nghiệm thu cuối cùng chờ Codex review và dev xác nhận.
- `[ ]`: chưa có, mới có một phần, còn phụ thuộc API/quyết định nghiệp vụ hoặc chưa đủ căn cứ xác nhận. Ghi chú đi kèm nêu rõ trường hợp.
- Mục **cần xác nhận** giữ `[ ]` cho đến khi dev chốt; không được xem là yêu cầu nghiệp vụ đã duyệt.

Ảnh là căn cứ về bố cục, thành phần, nhãn và trạng thái nhìn thấy. Code chỉ dùng để xác định tiến độ và phụ thuộc hiện tại. Thư mục Google Drive trong `AGENTS.md` chưa truy cập được; theo xác nhận của dev, tài liệu này sử dụng 5 ảnh, không suy đoán nội dung Drive.

Các số lượng, tên người, ngày tháng và bản ghi trong ảnh là dữ liệu minh họa, không phải dữ liệu cần seed hoặc giá trị phải viết cố định vào giao diện.

## 2. Khung giao diện dùng chung

### 2.1. Bố cục và nhận diện

Thiết kế chia thành sidebar bên trái và vùng nội dung bên phải. Sidebar có logo **XBIKE MRP SYSTEM** ở đầu, menu ở giữa và hình xe đạp trong cảnh hoàng hôn ở phần dưới. Nền tổng thể đen/nâu tối, thẻ nội dung nâu tối, chữ trắng/ngà; màu cam nhấn vào menu đang chọn và hành động chính.

Vùng nội dung có breadcrumb phía trên, tên trang nổi bật bên dưới; cụm người dùng ở góc trên bên phải gồm ảnh đại diện, tên, dòng vai trò và mũi tên mở menu.

- [x] **LAY-01** — Có khung dùng chung gồm thanh điều hướng, vùng nội dung và thông tin người đăng nhập. Căn cứ: `MainLayout.jsx`, `Sidebar.jsx`.
- [x] **LAY-02** — Có điều hướng tới Tổng quan, Tài khoản và Vai trò; mục đang truy cập có trạng thái active.
- [x] **LAY-03** — Hiển thị đúng nhãn sidebar trong ảnh: “Tổng quan”, “Quản lý tài khoản”, “Quản lý vai trò”. Căn cứ: `navigation.js`, `Sidebar.jsx`.
- [x] **LAY-04** — Đặt logo, hình nền xe đạp và bố cục sidebar như ảnh. Căn cứ: `Sidebar.jsx`, `Sidebar.module.css`.
- [x] **LAY-05** — Áp dụng giao diện tối, màu cam chủ đạo, viền mảnh và góc bo như ảnh trong phạm vi `.admin-shell` (`MainLayout.jsx`, `App.css`).
- [x] **LAY-06** — Có breadcrumb kèm biểu tượng trang chủ; trang chi tiết có cấp “Quản lý tài khoản > Chi tiết tài khoản”. Căn cứ: `MainLayout.jsx`.
- [x] **LAY-07** — Cụm người dùng hiển thị tên và vai trò. Hiện avatar được tạo từ chữ cái tên.
- [ ] **LAY-08** — Hiển thị avatar dạng ảnh tròn theo mẫu; chưa có trường ảnh đại diện trong response nhân viên hiện tại (`FE-MISS-003`). Đã hiển thị avatar tròn chữ cái theo quyết định của dev.
- [x] **LAY-09** — Đã áp dụng bộ token giao diện tối nâu/đen và cam nhấn trong `.admin-shell` (`App.css`) theo 5 ảnh nguồn.

### 2.2. Thành phần và trạng thái

| Thành phần | Biểu hiện trong ảnh |
| --- | --- |
| Nút chính | Nền cam, chữ sáng; có thể có icon ở đầu |
| Nút phụ | Nền tối, viền mảnh; dùng cho Quay lại, Hủy, Chi tiết, Sửa |
| Hành động vô hiệu hóa/xóa | Icon và sắc đỏ; tách biệt hành động chính |
| Hành động mở khóa | Icon khóa và sắc xanh lá |
| Badge vai trò | Quản trị viên vàng/nâu với vương miện; Quản lý kho xanh lam với icon lớp; Nhân viên nâu với icon nhóm |
| Badge trạng thái | Hoạt động xanh lá với dấu kiểm; Bị khóa đỏ với biểu tượng cấm |
| Ô tìm kiếm/bộ lọc | Nền tối, viền sáng nhẹ, icon ở đầu; select có mũi tên ở cuối |
| Bảng | Header nổi hơn nền nội dung, hàng phân cách bằng đường mảnh, thao tác nằm cuối hàng |
| Hộp thoại | Đặt giữa vùng nhìn, nền phía sau tối đi, có tiêu đề, nội dung, nút đóng và hai nút hành động |

- [x] **CMP-01** — Có component dùng chung cho nút, trường nhập, bảng, badge, trạng thái tải/lỗi và hộp thoại.
- [x] **CMP-02** — Badge hiện có nhãn “Hoạt động”, “Bị khóa” và màu trạng thái; đã bổ sung icon (`AdminStatusBadge`, `Badge.jsx`).
- [x] **CMP-03** — Hoàn thiện badge vai trò (`AdminRoleBadge`), icon trạng thái (`AdminStatusBadge`) và hình thức component theo bảng trên.
- [x] **CMP-04** — Đã chụp và đối chiếu trực quan 5 màn hình tại `1440×900` và kích thước ảnh nguồn (`1672×941` / `1670×941`) trong `frontend/test-results/`.

## 3. ADM-01 — Tổng quan

Ảnh nguồn: `tong_quan.png`. Route hiện có: `/admin`. Mục sidebar đang chọn: “Tổng quan”.

### 3.1. Nội dung và bố cục

Thứ tự từ trên xuống: breadcrumb và tiêu đề **Tổng quan**; một hàng 4 thẻ thống kê; một hàng gồm biểu đồ truy cập bên trái và phân bổ vai trò bên phải; cuối cùng là bảng **Hoạt động gần đây** chiếm chiều ngang vùng nội dung.

| Thẻ thống kê theo ảnh | Dữ liệu mẫu | Biểu hiện |
| --- | --- | --- |
| Tổng tài khoản | 24 | Icon nhóm người màu vàng |
| Tổng vai trò | 3 | Icon lớp màu xanh lam |
| Tài khoản đang hoạt động | 22 | Icon dấu kiểm màu xanh lá |
| Tài khoản đã vô hiệu hóa | 2 | Icon cấm màu đỏ |

- [x] **OV-01** — Có 4 chỉ số lấy tổng từ API: tổng tài khoản, tài khoản hoạt động, tài khoản bị khóa và vai trò. Căn cứ: `AdminDashboard`, `AdminStatCard` trong `DashboardPage.jsx`.
- [x] **OV-02** — Đặt thẻ đúng thứ tự (`Tổng tài khoản` → `Tổng vai trò` → `Tài khoản đang hoạt động` → `Tài khoản đã vô hiệu hóa`), nhãn, icon và hình thức của ảnh.
- [x] **OV-03** — Có khối “Lưu lượng truy website”. Dòng mô tả là “Tổng hợp theo số lượng request mỗi giờ” ở `Hôm nay` và “… mỗi ngày” ở `7 ngày` / `30 ngày`. Bộ chọn “Hôm nay / 7 ngày / 30 ngày” đã gắn API, có `aria-pressed` (D-LL-01).
- [x] **OV-04** — Vẽ đường cam có vùng tô phía dưới, điểm dữ liệu, trục thời gian và trục số lượng từ `GET /api/v1/luu_luong_truy_cap` (`TrafficCard` trong `DashboardPage.jsx`).
  - `Hôm nay`: 24 điểm theo giờ, nhãn `00h`–`21h`, đường dừng ở giờ hiện tại.
  - `7 ngày`: 7 điểm theo ngày, nhãn `dd/MM`.
  - `30 ngày`: 30 điểm theo ngày, 6 nhãn cách 5 ngày.
  - Khác ảnh, đã được dev duyệt (D-LL-01):
    - trục Y tuyến tính, có mốc `1.500` mà ảnh thiếu, tự giãn khi vượt 4.000;
    - tab `30 ngày` có thêm đường nét đứt “Trung bình 7 ngày” và chú giải;
    - mốc `21h` nằm ở khoảng 91% chiều ngang, vì trục có đủ 24 giờ.
- [x] **OV-05** — Có biểu đồ donut “Phân bổ tài khoản theo vai trò”, tổng tài khoản ở tâm; chú giải có màu, tên vai trò, số lượng và tỷ lệ tính từ dữ liệu thật của API (bao gồm cả tài khoản bị khóa).
- [x] **OV-06** — Có khối “Hoạt động gần đây”, gọi API audit với 5 bản ghi mới nhất, sắp xếp `-created_at`.
- [x] **OV-07** — Trình bày hoạt động thành bảng 4 cột: “Thời gian”, “Người thực hiện”, “Hành động”, “Chi tiết”.
- [x] **OV-08** — Hiển thị tên người thực hiện từ danh sách nhân viên và dựng câu hành động/chi tiết từ snapshot `AuditLogResponse` theo D-HD-01; nhãn vai trò từ `ma_vai_tro` lịch sử qua `ROLE_LABELS` dùng chung. Chỉ liệt kê tên trường hồ sơ đổi, không hiện giá trị. Căn cứ: `DashboardPage.jsx`, `auditFormat.js`, `contracts.test.js` giữ nguyên theo dev chốt sau verify lần 1; pytest tạm 90/90 và Playwright ADM-01 trong suite admin 11/11 (10/11/2026, API fixture; chưa E2E DB thật).

### 3.2. Điểm cần xác nhận

- [x] **OV-Q01** — Đã chốt nguồn số liệu, cách đếm request, múi giờ, khoảng lấy mẫu cho 7/30 ngày và thời điểm làm mới (`FE-MISS-001`, `docs/DECISION.md` D-LL-01).
  - Nguồn: bảng `"LuuLuongTruyCap"`, đếm mọi request `/api/v1` trừ `OPTIONS`.
  - Múi giờ: Asia/Ho_Chi_Minh.
  - Làm mới: khi mở trang, khi đổi tab và khi quay lại cửa sổ; không tự tải định kỳ.
- [x] **OV-Q02** — Dev đã chốt phân bổ vai trò tính cả tài khoản bị khóa và lấy từ dữ liệu thật của API (`doc/admin-ui-plan.md`).
- [x] **OV-Q03** — Dev chốt 10/11/2026 theo plan FE-MISS-004: dựng câu từ snapshot D-HD-01, query Tổng quan loại `thu_hoi_quyen` trước phân trang để mỗi lần đổi vai trò còn một dòng Phân quyền; giữ 5 dòng mới nhất, không thêm thao tác xem thêm. Căn cứ: contract v3.1 §4/§13 (bản trích dev cung cấp), `docs/DECISION.md` D-HD-01 và Playwright ADM-01.

## 4. ADM-02 — Quản lý tài khoản

Ảnh nguồn: `quan_ly_tai_khoan.png`. Route hiện có: `/admin/tai-khoan`. Mục sidebar đang chọn: “Quản lý tài khoản”.

### 4.1. Thanh công cụ và bảng

Tiêu đề **Quản lý tài khoản** nằm trên thanh công cụ. Thanh công cụ lần lượt có ô **Tìm tài khoản**, bộ lọc **Vai trò**, bộ lọc **Trạng thái**, nút cam **+ Tạo tài khoản** ở bên phải.

| Cột theo ảnh | Nội dung |
| --- | --- |
| Chọn | Checkbox đầu bảng và checkbox mỗi hàng |
| STT | Số thứ tự hiển thị |
| Tên | Avatar tròn, họ tên nổi bật, mã nhân viên ở dòng dưới |
| Ngày sinh | Ngày theo dạng `dd/MM/yyyy` |
| Vai trò | Badge vai trò |
| Trạng thái | Badge Hoạt động hoặc Bị khóa |
| Thao tác | Chi tiết, Sửa và Vô hiệu hóa hoặc Mở khóa |

- [x] **ACC-01** — Có ô tìm kiếm và bộ lọc vai trò/trạng thái, gọi danh sách nhân viên qua API.
- [x] **ACC-02** — Đổi nhãn, vị trí và hình thức thanh công cụ theo ảnh: tìm kiếm khi nhấn Enter, bộ lọc áp dụng ngay khi chọn và đưa về trang 1 (`UsersPage.jsx`).
- [x] **ACC-03** — Có nút “+ Tạo tài khoản”, mở form tại `/admin/tai-khoan/moi`.
- [x] **ACC-04** — Hiển thị đủ cột và thứ tự theo bảng trên (Chọn, STT, Tên kèm avatar chữ cái và mã nhân viên, Ngày sinh `dd/MM/yyyy`, Vai trò, Trạng thái, Thao tác).
- [x] **ACC-05** — Danh sách có họ tên, mã nhân viên, badge vai trò và badge trạng thái kèm icon theo ảnh.
- [x] **ACC-06** — Có nút “Chi tiết” riêng (`/admin/tai-khoan/:id`) và nút “Sửa” riêng (`/admin/tai-khoan/:id?mode=edit`) ở mỗi hàng.
- [x] **ACC-07** — Đặt thao tác Vô hiệu hóa/Mở khóa trực tiếp trên hàng, đổi theo trạng thái và tôn trọng chặn khóa quản trị viên/chính mình.
- [x] **ACC-08** — Có chức năng khóa/mở khóa, yêu cầu xác nhận và lý do; giữ hồ sơ và tham chiếu lịch sử.

### 4.2. Phân trang và lựa chọn

Cuối bảng, bên trái là **Hiển thị [10] dòng/trang**; bên phải có mũi tên trước/sau, các số trang, dấu rút gọn và trang hiện tại nền cam. Các số 1, 2, 3, …, 8 trong ảnh chỉ minh họa.

- [x] **ACC-09** — Có phân trang API, số lượng kết quả và nút trước/sau.
- [x] **ACC-10** — Có selector số dòng/trang chỉ giữ mức `10` dòng/trang theo quyết định dev (`R2-04`) và điều hướng bằng số trang động từ `meta` (`AdminPagination`).
- [x] **ACC-11** — Hiển thị checkbox chọn từng hàng và checkbox chọn tất cả trên trang hiện tại.
- [x] **ACC-Q01** — Dev đã chốt chọn tất cả chỉ áp dụng trên trang hiện tại và không thêm hành động hàng loạt (`doc/admin-ui-plan.md`).
- [ ] **ACC-Q02** — Chốt tiêu chí tìm kiếm mong muốn nếu cần tìm theo tên đăng nhập/email ngoài mã nhân viên và họ tên đang được hỗ trợ.

### 4.3. Luồng thao tác

| Điểm bắt đầu | Kết quả giao diện đích | Tình trạng hiện tại |
| --- | --- | --- |
| Chọn Chi tiết | Xem ADM-03 | Mở trang chi tiết hai cột tại `/admin/tai-khoan/:id` |
| Chọn Sửa/Chỉnh sửa | Chuyển sang chế độ sửa tài khoản đã chọn | Mở chế độ sửa tại `/admin/tai-khoan/:id?mode=edit` |
| Chọn Tạo tài khoản | Mở form tạo mới | Mở form tạo mới tại `/admin/tai-khoan/moi` |
| Chọn Vô hiệu hóa | Yêu cầu xác nhận trước khi khóa | Mở hộp thoại xác nhận kèm lý do và gọi `DELETE /api/v1/nhan_vien/{id}` |
| Chọn Mở khóa | Yêu cầu xác nhận trước khi mở lại | Mở hộp thoại xác nhận kèm lý do và gọi `POST /api/v1/nhan_vien/{id}/mo_khoa` |

- [x] **ACC-Q03** — Dev đã chốt giữ các trường, validation, phân quyền, lý do và xử lý lỗi hiện tại của form tạo/sửa; đồng bộ cách trình bày với giao diện admin (`doc/admin-ui-plan.md`).

## 5. ADM-03 — Chi tiết tài khoản

Ảnh nguồn: `chi_tiet_tai_khoan.png`. Route hiện có: `/admin/tai-khoan/:id`. Ảnh đích là một trang chi tiết; triển khai hiện tại dùng modal trên danh sách.

### 5.1. Bố cục

Phía trên có breadcrumb **Quản lý tài khoản > Chi tiết tài khoản**, tiêu đề **Chi tiết tài khoản**, nút **Quay lại** bên trái; hai nút **Chỉnh sửa** và **Vô hiệu hóa** bên phải.

Bên dưới chia hai cột: thẻ nhận diện bên trái gồm avatar lớn, họ tên, mã nhân viên, badge vai trò và trạng thái; thẻ **Thông tin tài khoản** bên phải gồm các dòng nhãn và giá trị.

| Trường theo thứ tự trong ảnh | Ánh xạ code hiện tại | Ghi chú |
| --- | --- | --- |
| Họ tên | `ho_ten` | Dữ liệu hồ sơ |
| Ngày sinh | `ngay_sinh` | Ảnh hiển thị ngày/tháng/năm |
| Số điện thoại | `so_dien_thoai` | Giữ dạng chuỗi, gồm số 0 đầu |
| Email | `email` | Dữ liệu hồ sơ |
| Tên đăng nhập | `ten_dang_nhap` | Có trong response, không thuộc payload sửa hồ sơ hiện tại |
| Mật khẩu | Không có trong response công khai | Ảnh chỉ thể hiện chuỗi dấu chấm; không suy ra mật khẩu thực hoặc độ dài thực |
| Vai trò | `vai_tro_id`, `ma_vai_tro` | Hiển thị tên vai trò; cập nhật qua luồng riêng |
| Ngày vào làm | `ngay_vao_lam` | Dữ liệu hồ sơ |
| Hệ số lương | `he_so_luong` | Mẫu hiển thị `3.50`; API hiện dùng chuỗi thập phân |
| Trạng thái | `trang_thai` | `hoat_dong` / `bi_khoa` |

- [x] **DET-01** — Có lấy thông tin tài khoản theo ID và hiển thị các trường hồ sơ, tên đăng nhập, mã nhân viên, vai trò và trạng thái.
- [x] **DET-02** — Dựng trang chi tiết hai cột, thẻ nhận diện và đúng thứ tự 10 trường như ảnh (`AccountDetailView` trong `UsersPage.jsx`).
- [x] **DET-03** — Có breadcrumb, nút “Quay lại”, “Chỉnh sửa”, “Vô hiệu hóa”/“Mở khóa” đúng vị trí và nhãn.
- [x] **DET-04** — Có avatar tròn lớn (hiển thị chữ cái khi chưa có ảnh từ API) và badge vai trò/trạng thái kèm icon như ảnh.
- [x] **DET-05** — Chế độ xem thể hiện hàng “Mật khẩu” bằng dấu chấm cố định (`••••••••`), không lấy mật khẩu/hash từ API. Chế độ chỉnh sửa có một ô mật khẩu mới, placeholder “Để trống nếu không đổi”, nút hiện/ẩn; xóa giá trị khi Hủy, thoát sửa, đổi tài khoản hoặc lưu thành công. Mật khẩu không được lưu vào URL, query key, console hay localStorage.
- [x] **DET-06** — Response công khai không trả mật khẩu hoặc hash mật khẩu. Có thể đối chiếu `NhanVienRead` trong `schemas.py`.
- [x] **DET-07** — Chỉnh sửa trực tiếp trên 10 hàng: hồ sơ, vai trò và mật khẩu mới; tên đăng nhập và trạng thái vẫn chỉ đọc. `Lưu` dùng popup `Xác nhận thay đổi` hiện có, lần lượt gọi các bước cần ghi: `PATCH /api/v1/nhan_vien/{id}` → `PUT /api/v1/nhan_vien/{id}/vai_tro` → `POST /api/v1/nhan_vien/{id}/dat_lai_mat_khau`, nối ETag qua `If-Match`. Mật khẩu rỗng bỏ qua bước reset; có nhập thì 8–1024 ký tự, không trim. Lỗi một phần nêu bước đã lưu/bước thất bại, giữ mật khẩu nháp để thử lại, không gửi lại bước đã thành công. Tự reset thì gọi `login()` với mật khẩu mới ngay sau reset, trước mọi invalidate/refetch; thành công vẫn ở trang chi tiết và mở `Lưu thành công`. Chỉ khi đăng nhập lại lỗi mới logout với “Đã đặt lại mật khẩu. Vui lòng đăng nhập lại.”
- [x] **DET-08** — Chuẩn hóa hiển thị ngày `dd/MM/yyyy` (`formatDate`) và hệ số lương hai chữ số thập phân (`formatCoefficient`) theo ảnh ở chế độ xem chi tiết.
- [x] **DET-09** — Giao diện giữ chặn khóa tài khoản quản trị viên và tài khoản của chính người đang đăng nhập; không cho đổi vai trò của tài khoản quản trị viên.

### 5.2. Khác biệt dữ liệu cần giữ rõ

- [x] **DET-Q01** — Dev đã chốt giữ mã nhân viên do API trả về (`NV-000001`), không đổi thành `NV001` hoặc đổi validation (`doc/admin-ui-plan.md`).
- [x] **DET-Q02** — Dev chốt 10/11/2026 (`FE-MISS-005`, D-MK-01): bổ sung API và ô mật khẩu trong chế độ sửa, dùng chung nút `Lưu` và popup xác nhận, không ô lý do; áp dụng mọi tài khoản gồm chính admin và tài khoản bị khóa. Chế độ xem giữ `••••••••`; tự reset đăng nhập lại tự động để tiếp tục phiên. Quyết định này cập nhật giới hạn chỉ đọc trước đây trong `doc/admin-ui-inline-edit-plan.md`.
- [x] **DET-Q03** — Dev đã chốt dùng avatar chữ cái khi chưa có ảnh nhân viên (`FE-MISS-003`).
- [x] **DET-Q04** — Hiển thị nút hành động “Vô hiệu hóa” / “Mở khóa” và badge trạng thái “Hoạt động” / “Bị khóa” dựa trên hai trạng thái `hoat_dong` và `bi_khoa` của API.

## 6. ADM-04 — Quản lý vai trò

Ảnh nguồn: `quan_ly_vai_tro.png`. Route hiện có: `/admin/vai-tro`. Mục sidebar đang chọn: “Quản lý vai trò”.

### 6.1. Nội dung và thao tác

Tiêu đề **Quản lý vai trò**; thanh công cụ có ô **Tìm vai trò** bên trái và nút **+ Tạo vai trò** bên phải. Bảng gồm **STT**, **Tên vai trò**, **Mô tả**, **Thao tác**. Cuối bảng có chọn số dòng/trang và dãy số trang như danh sách tài khoản.

Ảnh minh họa Quản trị viên, Quản lý kho, Nhân viên, Cộng tác viên và Hỗ trợ kỹ thuật. Theo ảnh đối chiếu mới của dev (`doc/admin-ui-inline-edit-plan.md`), cả 3 vai trò hệ thống (`quan_tri_vien`, `quan_ly`, `nhan_vien`) đều có nút “Sửa” và nút “Xóa” ở trạng thái vô hiệu hóa (`disabled` + mờ).

- [x] **ROL-01** — Có trang lấy danh sách vai trò thật từ API (`GET /api/v1/vai_tro`).
- [x] **ROL-02** — Có tiêu đề “Quản lý vai trò”, ô tìm kiếm “Tìm vai trò”, nút “+ Tạo vai trò” và bố cục bảng đúng ảnh (`RolesPage.jsx`).
- [x] **ROL-03** — Cột STT và Mô tả hiển thị dữ liệu thật; `VaiTroRead.mo_ta` là string hoặc null, null hiển thị `—`. Mô tả seed tóm tắt SRS_v4 §2 (D-VT-01, `FE-MISS-002`).
- [x] **ROL-04** — Nút “+ Tạo vai trò” giữ nguyên vị trí/hình dạng, ở trạng thái disabled và mờ 0.55 theo D-VT-01. Không có API tạo vai trò vì bộ vai trò cố định.
- [x] **ROL-05** — Nút “Sửa” của 3 vai trò hệ thống (`quan_tri_vien`, `quan_ly`, `nhan_vien`) giữ vô hiệu hóa (`disabled` + `admin-action-muted`) theo mã vai trò, theo `doc/admin-ui-inline-edit-plan.md` và D-VT-01. Không hỗ trợ API sửa vai trò.
- [x] **ROL-06** — Nút “Xóa” của 3 vai trò hệ thống vô hiệu hóa kèm icon thông tin vai trò hệ thống; không hỗ trợ API xóa vai trò theo D-VT-01.
- [x] **ROL-07** — Có tìm kiếm (Enter đưa về trang 1), selector số dòng/trang chỉ giữ mức `10` theo quyết định dev (`R2-04`) và thanh phân trang phía client trên danh sách vai trò đã tải đầy đủ.

### 6.2. Mâu thuẫn và điểm cần xác nhận

- [x] **ROL-Q01** — D-VT-01: giữ ba mã cố định `quan_tri_vien`, `quan_ly`, `nhan_vien`, không mở vai trò động hoặc thay cơ chế phân quyền. Hai vai trò bổ sung trong ảnh chỉ minh họa.
- [x] **ROL-Q02** — Không áp dụng: D-VT-01 không tạo vai trò mới, không có UI cấu hình quyền hoặc ma trận quyền mới.
- [x] **ROL-Q03** — D-VT-01: Sửa/Xóa bị vô hiệu hóa vì đây là ba vai trò hệ thống cố định, xác định theo mã vai trò.
- [x] **ROL-Q04** — D-VT-01: không có form tạo/sửa, xác nhận xóa hoặc API ghi vai trò; mô tả chỉ đọc.
- [x] **ROL-Q05** — Dữ liệu thật có đúng ba vai trò theo SRS_v4 §2 và D-VT-01; Cộng tác viên/Hỗ trợ kỹ thuật trong ảnh chỉ minh họa, không xuất hiện trong hệ thống.

D-VT-01 (09/11/2026) thay phần tạo/sửa/xóa trong thiết kế bằng danh sách chỉ đọc có mô tả từ API. Ba khác biệt đã chốt với ảnh: Sửa vô hiệu hóa, chỉ có ba vai trò thật và Tạo vô hiệu hóa. Quyền đọc API vẫn là admin/quản lý; không hỗ trợ ghi vai trò. Các mục trên không xác nhận DB đang chạy đã có cột mới; backend mới cần DB đã bootstrap với `mo_ta`.

## 7. ADM-05 — Popup xác nhận thay đổi

Ảnh nguồn: `popup_xac_nhan.png`. Popup xuất hiện trên nền trang chi tiết tài khoản; nội dung phía sau bị làm tối và vẫn nhận diện được tài khoản đang thao tác.

| Thành phần | Nội dung theo ảnh |
| --- | --- |
| Tiêu đề | Xác nhận thay đổi |
| Nội dung | Bạn có chắc chắn muốn thay đổi thông tin tài khoản không? |
| Đóng | Nút X ở góc trên bên phải |
| Hủy | Nút phụ bên trái |
| Xác nhận | Nút cam bên phải |

- [x] **CFM-01** — Có hộp thoại xác nhận dùng chung, tiêu đề, mô tả, nút X, Hủy và Xác nhận. Dùng `dialog.showModal()` trong `FeedbackProvider.jsx`.
- [x] **CFM-02** — Đã áp dụng popup “Xác nhận thay đổi” (`Bạn có chắc chắn muốn thay đổi thông tin tài khoản không?`) trước khi gửi lưu chỉnh sửa trực tiếp, popup “Lưu thành công” (`02-luu-thanh-cong.png`, chỉ có nút `Đóng`) sau khi mọi request cập nhật thành công, và popup “Đăng xuất” rút gọn (`03-xac-nhan-dang-xuat.png`, `Bạn có muốn kết thúc phiên làm việc?`, ẩn thông báo tồn kho) khi bấm Đăng xuất.
- [x] **CFM-03** — Trình bày nền tối, viền, bo góc, kích thước tương đối và hai nút `Hủy` / `Xác nhận` như ảnh (`ADM-05`).
- [x] **CFM-04** — Cơ chế xác nhận chỉ gọi hành động ghi (`PATCH`) khi bấm Xác nhận; Hủy/X đóng mà không gọi API và giữ nguyên bản nháp đang sửa.
- [x] **CFM-05** — Khi đang xác nhận, chặn gửi lặp, đổi nhãn thành “Đang xử lý…”, vô hiệu hóa nút xác nhận/hủy/đóng và không đóng bằng Escape.
- [x] **CFM-06** — Khi hành động lỗi, hộp thoại giữ mở, hiển thị lỗi; không báo thành công. Khi thành công, hộp thoại đóng và làm mới dữ liệu.
- [x] **CFM-07** — Hộp thoại có tên truy cập được qua tiêu đề; khi đóng trả focus về phần tử mở nếu phần tử còn tồn tại.
- [x] **CFM-Q01** — Dev đã chốt áp dụng ADM-05 khi lưu sửa hồ sơ; tạo mới giữ luồng hiện có (`doc/admin-ui-plan.md`).
- [x] **CFM-Q02** — Dev đã chốt khóa/mở khóa giữ câu chữ và yêu cầu lý do hiện có (`doc/admin-ui-plan.md`).

Luồng đích cho thay đổi thông tin: nhập nội dung sửa → chọn lưu → mở popup → Hủy/X giữ nguyên dữ liệu đã lưu, quay lại nội dung đang sửa; Xác nhận thực hiện lưu → thành công làm mới thông tin, thất bại hiển thị lỗi. Việc giữ bản nháp khi hủy và cách chuyển sang chế độ sửa cần chốt cùng thiết kế form ở `ACC-Q03`.

## 8. Phụ thuộc dữ liệu và bảo vệ hành vi hiện có

Bảng dưới chỉ ghi nhận endpoint đang tồn tại để người triển khai đối chiếu. Prefix API mặc định của frontend là `/api/v1`; tài liệu này không đề xuất thay đổi request/response.

| Nhu cầu giao diện | Endpoint hiện có |
| --- | --- |
| Danh sách/tìm kiếm/lọc nhân viên và tổng số | `GET /api/v1/nhan_vien` |
| Chi tiết tài khoản | `GET /api/v1/nhan_vien/{id}` |
| Tạo tài khoản | `POST /api/v1/nhan_vien` |
| Sửa hồ sơ | `PATCH /api/v1/nhan_vien/{id}` |
| Đổi vai trò của nhân viên | `PUT /api/v1/nhan_vien/{id}/vai_tro` |
| Khóa tài khoản, không xóa vật lý | `DELETE /api/v1/nhan_vien/{id}` |
| Mở khóa | `POST /api/v1/nhan_vien/{id}/mo_khoa` |
| Danh sách vai trò | `GET /api/v1/vai_tro` |
| Hoạt động gần đây | `GET /api/v1/audit` |

- [x] **DATA-01** — Frontend có bảo vệ route admin bằng phiên đăng nhập và vai trò `quan_tri_vien`; URL không được phép chuyển tới trang 403.
- [x] **DATA-02** — Các thao tác cập nhật tài khoản có sử dụng ETag/If-Match; không tự lấy phiên bản mới để ghi đè thay đổi của người khác.
- [x] **DATA-03** — Có thông báo yêu cầu tải lại khi nhận 412/428; cần giữ hành vi này khi thay UI.
- [x] **DATA-04** — Có trạng thái tải, dữ liệu rỗng, lỗi tải và nút tải lại trong các component dữ liệu hiện tại.
- [ ] **DATA-05** — Chốt hình thức các trạng thái tải/rỗng/lỗi trong giao diện tối; 5 ảnh không minh họa các trạng thái này.

Không tự thay chính sách bảo vệ quản trị viên, định dạng mã nhân viên, hợp đồng cập nhật hồ sơ hoặc cơ chế khóa tài khoản để khớp dữ liệu mẫu trong ảnh. Không suy ra quyền hạn thực tế từ những câu mô tả vai trò hoặc bản ghi hoạt động minh họa.

## 9. Checklist nghiệm thu giao diện

Các mục dưới đây ghi nhận trạng thái đã dựng UI, đã tích hợp API hiện có và đã chạy kiểm thử tự động / chụp ảnh đối chiếu bởi AGY trong vòng 2; kết quả nghiệm thu cuối cùng chờ Codex review vòng 2.

- [x] **QA-01** — Đã dựng và chụp ảnh đối chiếu cả 5 màn hình desktop với ảnh nguồn tại kích thước gốc (`1672×941` / `1670×941`) và `1440×900` (`frontend/test-results/adm-01..05-*.png`); chờ Codex review nghiệm thu vòng 2.
- [x] **QA-02** — Đã kiểm chứng tự động: menu chuyển đúng trang, active đúng; breadcrumb và Quay lại từ chi tiết trở về danh sách (`navigation.spec.js`, `sidebar.spec.js`, `record-dialog.spec.js`).
- [x] **QA-03** — Đã kiểm chứng tự động: tổng số tài khoản, số hoạt động/bị khóa và phân bổ vai trò nhất quán với dữ liệu thực, không dùng số cố định từ ảnh (`admin-ui.spec.js`).
- [x] **QA-04** — Đã kiểm chứng tự động: tìm kiếm và phối hợp bộ lọc hoạt động đúng; đổi bộ lọc đưa về trang đầu; dữ liệu rỗng có thông báo rõ ràng (`admin-ui.spec.js`).
- [x] **QA-05** — Đã kiểm chứng tự động: phân trang không vượt giới hạn; selector số dòng/trang chỉ giữ mức `10` và số thứ tự hàng đúng theo quy tắc đã chốt (`admin-ui.spec.js`).
- [x] **QA-06** — Đã kiểm chứng tự động: chi tiết mở đúng tài khoản; trường trống, ngày tháng (`dd/MM/yyyy`), số điện thoại và hệ số lương (`2 chữ số thập phân`) hiển thị hợp lệ; không lộ thông tin mật khẩu (`admin-ui.spec.js`).
- [x] **QA-07** — Đã kiểm chứng tự động: tạo/sửa hồ sơ và đổi vai trò gửi đúng nhóm trường; nhập sai hoặc trùng dữ liệu có phản hồi, không báo lưu thành công khi API lỗi (`mutations.spec.js`, `admin-ui.spec.js`).
- [x] **QA-08** — Đã kiểm chứng tự động: vô hiệu hóa/mở khóa yêu cầu xác nhận trên snapshot đã duyệt; sau thành công badge và thao tác thay đổi đúng; hồ sơ và lịch sử được giữ nguyên (`mutations.spec.js`, `admin-ui.spec.js`).
- [x] **QA-09** — Đã kiểm chứng tự động: Hủy/X popup không ghi dữ liệu và giữ bản nháp; bấm Xác nhận nhiều lần chỉ gửi một hành động; lỗi giữ đủ thông tin để người dùng xử lý (`mutations.spec.js`, `admin-ui.spec.js`).
- [x] **QA-10** — Nghiệm thu theo D-VT-01: danh sách có mô tả, tìm theo mô tả, null hiển thị `—`, Tạo/Sửa/Xóa vô hiệu hóa; không có chức năng ghi vai trò để nghiệm thu (`FE-MISS-002`).
- [x] **QA-11** — Đã kiểm chứng tự động: truy cập URL trực tiếp khi chưa đăng nhập/sai quyền và khi phiên hết hạn giữ phản hồi 401/403 của hệ thống (`navigation.spec.js`, `workflows.spec.js`).
- [x] **QA-12** — Đã kiểm chứng tự động cập nhật đồng thời cả ở trang chi tiết và thao tác khóa/mở khóa trực tiếp trên hàng danh sách (`R2-01`): lấy snapshot + ETag trước khi mở popup xác nhận, khi xác nhận chỉ gửi ETag đã duyệt, nhận 412/428 không tự lấy ETag mới để ghi đè và hiển thị hướng dẫn tải lại (`contracts.test.js`, `admin-ui.spec.js`, `workflows.spec.js`).
- [x] **QA-13** — Đã kiểm chứng tự động: dùng bàn phím truy cập được bộ lọc, bảng, nút và popup; focus nhìn thấy, nằm trong popup khi mở và trở về nơi mở khi đóng; icon thao tác có tên dễ hiểu.
- [x] **QA-14** — Đã kiểm tra độ tương phản chữ/nền và khả năng đọc trạng thái bằng nhãn/icon, không chỉ bằng màu sau khi đổi sang giao diện tối.
- [ ] **QA-Q01** — Chốt yêu cầu tablet/mobile và hành vi co giãn. Đã kiểm tra không tràn ngang ở `375px` (`navigation.spec.js`); bộ ảnh hiện chỉ đặc tả desktop.

## 10. Căn cứ đối chiếu và giới hạn kiểm chứng

Những đường dẫn dưới đây tính từ gốc repository; chúng là bằng chứng cho trạng thái triển khai ghi ở checklist:

| Nhóm | Source đã đọc |
| --- | --- |
| Route và quyền admin | `frontend/src/routes/index.jsx`, `frontend/src/features/auth/permissions.js` |
| Khung và điều hướng | `frontend/src/layouts/MainLayout.jsx`, `Sidebar.jsx`, `Sidebar.module.css`, `navigation.js` |
| Tổng quan | `frontend/src/features/dashboard/DashboardPage.jsx` |
| Tài khoản và vai trò | `frontend/src/features/auth/UsersPage.jsx`, `RolesPage.jsx` |
| Thành phần dùng chung | `frontend/src/components/Collection.jsx`, `DataTable.jsx`, `RecordPanel.jsx`, `FeedbackProvider.jsx`, `Badge.jsx`, `QueryState.jsx` |
| Dữ liệu và hình thức hiện tại | `frontend/src/lib/api/useResources.js`, `endpoints.js`, `client.js`, `frontend/src/lib/useSave.js`, `format.js`, `frontend/src/app/App.css` |
| Hợp đồng tài khoản/vai trò hiện tại | `backend/app/modules/nhan_vien/router.py`, `schemas.py`, `service.py`, `repository.py` |
| Kiểm thử hiện có đã đọc & cập nhật | `frontend/tests/browser/admin-ui.spec.js`, `mutations.spec.js`, `navigation.spec.js`, `record-dialog.spec.js`, `sidebar.spec.js` |

Đã xem trực tiếp đủ 5 ảnh thiết kế nguồn, chụp và kiểm tra trực quan 10 ảnh screenshot (`1672×941`/`1670×941` và `1440×900`) trong `frontend/test-results/`, chạy đạt `npm run lint`, `npm test` (27/27) và `npm run build` cùng các bộ kiểm thử trình duyệt liên quan. Các kiểm thử trình duyệt dùng API fixture mock trên trình duyệt, chưa chạy E2E chống lại backend/database thật đang chạy. Kết quả nghiệm thu cuối cùng chờ Codex review vòng 2.
