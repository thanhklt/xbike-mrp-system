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

- `[x]`: đã thấy phần triển khai tương ứng trong source hiện tại. Đây là kết quả đối chiếu tĩnh, chưa xác nhận chạy thành công hoặc giống ảnh khi mở trình duyệt.
- `[ ]`: chưa có, mới có một phần, khác thiết kế hoặc chưa đủ căn cứ xác nhận. Ghi chú đi kèm nêu rõ trường hợp.
- Mục **cần xác nhận** giữ `[ ]` cho đến khi dev chốt; không được xem là yêu cầu nghiệp vụ đã duyệt.

Ảnh là căn cứ về bố cục, thành phần, nhãn và trạng thái nhìn thấy. Code chỉ dùng để xác định tiến độ và phụ thuộc hiện tại. Thư mục Google Drive trong `AGENTS.md` chưa truy cập được; theo xác nhận của dev, tài liệu này sử dụng 5 ảnh, không suy đoán nội dung Drive.

Các số lượng, tên người, ngày tháng và bản ghi trong ảnh là dữ liệu minh họa, không phải dữ liệu cần seed hoặc giá trị phải viết cố định vào giao diện.

## 2. Khung giao diện dùng chung

### 2.1. Bố cục và nhận diện

Thiết kế chia thành sidebar bên trái và vùng nội dung bên phải. Sidebar có logo **XBIKE MRP SYSTEM** ở đầu, menu ở giữa và hình xe đạp trong cảnh hoàng hôn ở phần dưới. Nền tổng thể đen/nâu tối, thẻ nội dung nâu tối, chữ trắng/ngà; màu cam nhấn vào menu đang chọn và hành động chính.

Vùng nội dung có breadcrumb phía trên, tên trang nổi bật bên dưới; cụm người dùng ở góc trên bên phải gồm ảnh đại diện, tên, dòng vai trò và mũi tên mở menu.

- [x] **LAY-01** — Có khung dùng chung gồm thanh điều hướng, vùng nội dung và thông tin người đăng nhập. Căn cứ: `MainLayout.jsx`, `Sidebar.jsx`.
- [x] **LAY-02** — Có điều hướng tới Tổng quan, Tài khoản và Vai trò; mục đang truy cập có trạng thái active. Code hiện dùng nhãn “Tài khoản”, “Vai trò”.
- [ ] **LAY-03** — Hiển thị đúng nhãn sidebar trong ảnh: “Tổng quan”, “Quản lý tài khoản”, “Quản lý vai trò”.
- [ ] **LAY-04** — Đặt logo, hình nền xe đạp và bố cục sidebar như ảnh. Sidebar hiện tại có nền trắng và chưa có hình nền này.
- [ ] **LAY-05** — Áp dụng giao diện tối, màu cam chủ đạo, viền mảnh và góc bo như ảnh. `App.css` hiện dùng nền sáng, màu chủ đạo xanh đậm.
- [ ] **LAY-06** — Có breadcrumb kèm biểu tượng trang chủ; trang chi tiết có cấp “Quản lý tài khoản > Chi tiết tài khoản”. Chưa có breadcrumb tương ứng trong các trang admin hiện tại.
- [x] **LAY-07** — Cụm người dùng hiển thị tên và vai trò. Hiện avatar được tạo từ chữ cái tên.
- [ ] **LAY-08** — Hiển thị avatar dạng ảnh tròn theo mẫu; chưa thấy trường ảnh đại diện trong response nhân viên hiện tại.
- [ ] **LAY-09** — Chốt font, mã màu, kích thước chữ, khoảng cách và bán kính bo để triển khai nhất quán. Ảnh không cung cấp bộ token hoặc tên font; không coi các thông số ước lượng là giá trị đã duyệt.

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
- [x] **CMP-02** — Badge hiện có nhãn “Hoạt động”, “Bị khóa” và màu trạng thái; chưa có icon như ảnh.
- [ ] **CMP-03** — Hoàn thiện badge vai trò, icon trạng thái và hình thức component theo bảng trên.
- [ ] **CMP-04** — Đối chiếu trực quan toàn bộ 5 ảnh sau khi triển khai; hiện chưa có kết quả nghiệm thu hình ảnh.

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

- [x] **OV-01** — Có 4 chỉ số lấy tổng từ API: tổng tài khoản, tài khoản hoạt động, tài khoản bị khóa và vai trò. Căn cứ: `AdminDashboard`, `Metric` trong `DashboardPage.jsx`.
- [ ] **OV-02** — Đặt thẻ đúng thứ tự, nhãn, icon và hình thức của ảnh. Code hiện xếp tổng tài khoản → hoạt động → bị khóa → vai trò.
- [ ] **OV-03** — Có khối “Lưu lượng truy website”, dòng mô tả “Tổng hợp theo số lượng request mỗi giờ” và bộ chọn “Hôm nay / 7 ngày / 30 ngày”.
- [ ] **OV-04** — Vẽ đường biểu diễn màu cam kèm vùng tô phía dưới, các điểm dữ liệu, trục thời gian và trục số lượng. Ảnh đang chọn “Hôm nay”, trục thời gian hiển thị 00h đến 21h theo bước 3 giờ.
- [ ] **OV-05** — Có biểu đồ donut “Phân bổ tài khoản theo vai trò”, tổng tài khoản ở tâm; chú giải có màu, tên vai trò, số lượng và tỷ lệ. Mẫu gồm Nhân viên 16 (66.7%), Quản lý kho 5 (20.8%), Quản trị viên 3 (12.5%).
- [x] **OV-06** — Có khối “Hoạt động gần đây”, gọi API audit với 5 bản ghi mới nhất, sắp xếp `-created_at`.
- [ ] **OV-07** — Trình bày hoạt động thành bảng 4 cột: “Thời gian”, “Người thực hiện”, “Hành động”, “Chi tiết”. Hiện code dùng danh sách ngắn, hiển thị ID nhân viên và mã thao tác/đối tượng.
- [ ] **OV-08** — Hiển thị tên người thực hiện và diễn giải hành động dễ đọc như ảnh; chưa xác nhận đủ dữ liệu để dựng các câu mô tả này.

### 3.2. Điểm cần xác nhận

- [ ] **OV-Q01** — Chốt nguồn số liệu truy cập, cách đếm request, múi giờ, khoảng lấy mẫu cho 7/30 ngày và thời điểm làm mới. Ảnh không đủ để xác định; dashboard hiện chưa có lời gọi API cho biểu đồ truy cập.
- [ ] **OV-Q02** — Chốt phân bổ vai trò có tính cả tài khoản bị khóa hay không và cách làm tròn tỷ lệ.
- [ ] **OV-Q03** — Chốt nội dung và khả năng xem thêm từ bảng hoạt động; không tự xem thao tác “Tạo vai trò” trong dữ liệu mẫu là API đã có.

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

- [x] **ACC-01** — Có ô tìm kiếm và bộ lọc vai trò/trạng thái, gọi danh sách nhân viên qua API. Hiện áp dụng khi submit nút “Lọc”; backend tìm theo mã nhân viên hoặc họ tên.
- [ ] **ACC-02** — Đổi nhãn, vị trí và hình thức thanh công cụ theo ảnh. Ảnh không xác định tìm kiếm tức thì hay submit; cần chốt trước khi thay cơ chế hiện có.
- [x] **ACC-03** — Có nút “Tạo tài khoản”, mở form tại `/admin/tai-khoan/moi`.
- [ ] **ACC-04** — Hiển thị đủ cột và thứ tự theo bảng trên. Code hiện có Mã NV, Họ tên · tài khoản, Vai trò, Liên hệ, Trạng thái, Thao tác; chưa có STT, avatar, ngày sinh và checkbox.
- [x] **ACC-05** — Danh sách có họ tên, mã nhân viên, vai trò và trạng thái; chưa có hình thức badge vai trò theo ảnh.
- [ ] **ACC-06** — Có nút “Chi tiết” riêng và nút “Sửa” riêng ở mỗi hàng. Hiện cùng mở form tài khoản qua liên kết mã nhân viên hoặc “Sửa →”.
- [ ] **ACC-07** — Đặt thao tác Vô hiệu hóa/Mở khóa trực tiếp trên hàng, đổi theo trạng thái. Chức năng này hiện nằm bên trong form tài khoản.
- [x] **ACC-08** — Có chức năng khóa/mở khóa, yêu cầu xác nhận và lý do; giữ hồ sơ và tham chiếu lịch sử. Đây là khả năng hiện có trong form, chưa đạt vị trí và nhãn của thiết kế danh sách.

### 4.2. Phân trang và lựa chọn

Cuối bảng, bên trái là **Hiển thị [10] dòng/trang**; bên phải có mũi tên trước/sau, các số trang, dấu rút gọn và trang hiện tại nền cam. Các số 1, 2, 3, …, 8 trong ảnh chỉ minh họa.

- [x] **ACC-09** — Có phân trang API, số lượng kết quả và nút trước/sau. Mặc định trong code là 20 dòng/trang.
- [ ] **ACC-10** — Có chọn số dòng/trang, hiển thị giá trị 10 như mẫu và điều hướng bằng số trang. Các mức lựa chọn khác chưa có trong ảnh.
- [ ] **ACC-11** — Hiển thị checkbox chọn từng hàng và toàn bộ danh sách như ảnh.
- [ ] **ACC-Q01** — Chốt chọn tất cả áp dụng trên trang hiện tại hay toàn bộ kết quả và có hành động hàng loạt nào. Ảnh chỉ có checkbox, không có nút xử lý hàng loạt; không tự bổ sung nghiệp vụ.
- [ ] **ACC-Q02** — Chốt tiêu chí tìm kiếm mong muốn nếu cần tìm theo tên đăng nhập/email ngoài mã nhân viên và họ tên đang được hỗ trợ.

### 4.3. Luồng thao tác

| Điểm bắt đầu | Kết quả giao diện đích | Tình trạng hiện tại |
| --- | --- | --- |
| Chọn Chi tiết | Xem ADM-03 | Có lấy chi tiết, hiện mở modal chứa form |
| Chọn Sửa/Chỉnh sửa | Chuyển sang chế độ sửa tài khoản đã chọn | Có form sửa; ảnh chưa mô tả riêng chế độ sửa |
| Chọn Tạo tài khoản | Mở form tạo mới | Có form và API; ảnh chưa mô tả form tạo |
| Chọn Vô hiệu hóa | Yêu cầu xác nhận trước khi khóa | Có luồng khóa trong form, không xóa vật lý |
| Chọn Mở khóa | Yêu cầu xác nhận trước khi mở lại | Có luồng mở khóa trong form |

- [ ] **ACC-Q03** — Chốt thiết kế form tạo/sửa, trường bắt buộc và luồng sau khi lưu. Không dùng ảnh chi tiết để tự kết luận mọi trường đều được phép sửa.

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
- [ ] **DET-02** — Dựng trang chi tiết hai cột, thẻ nhận diện và thứ tự trường như ảnh; hiện là modal chỉnh sửa, chưa có trang chỉ xem theo thiết kế.
- [ ] **DET-03** — Có breadcrumb, nút “Quay lại”, “Chỉnh sửa”, “Vô hiệu hóa” đúng vị trí và nhãn. Hiện có nút đóng modal và thao tác trạng thái riêng trong form.
- [ ] **DET-04** — Có avatar lớn và badge vai trò/trạng thái kèm icon như ảnh.
- [ ] **DET-05** — Thể hiện hàng “Mật khẩu” bằng thông tin che cố định hoặc cách biểu đạt đã được dev chốt. Không gọi API để lấy mật khẩu/hash hoặc đưa thông tin bí mật vào DOM.
- [x] **DET-06** — Response công khai không trả mật khẩu hoặc hash mật khẩu. Có thể đối chiếu `NhanVienRead` trong `schemas.py`.
- [x] **DET-07** — Có sửa hồ sơ gồm họ tên, ngày sinh, điện thoại, email, ngày vào làm và hệ số lương; tách riêng cập nhật vai trò và khóa/mở khóa.
- [ ] **DET-08** — Chuẩn hóa hiển thị ngày `dd/MM/yyyy` và hệ số lương hai chữ số thập phân theo ảnh ở chế độ xem chi tiết. Hiện các giá trị nằm trong trường nhập của form.
- [x] **DET-09** — Giao diện hiện chặn khóa tài khoản quản trị viên và tài khoản của chính người đang đăng nhập; không cho đổi vai trò của tài khoản quản trị viên. Đây là chính sách hiện có, cần giữ khi thay hình thức trình bày.

### 5.2. Khác biệt dữ liệu cần giữ rõ

- [ ] **DET-Q01** — Chốt cách xử lý mã nhân viên: ảnh dùng `NV001`, API tạo mới hiện bắt buộc `NV-` và 6 chữ số, không nhận `NV-000000`. Không tự đổi validation hoặc dữ liệu để khớp dữ liệu mẫu.
- [ ] **DET-Q02** — Chốt cách biểu diễn trường mật khẩu và có cần đặt lại mật khẩu nhân viên hay không. Code hiện vô hiệu hóa nút đặt lại vì chưa có API; ảnh không mô tả luồng này.
- [ ] **DET-Q03** — Chốt nguồn avatar và cách hiển thị khi thiếu ảnh; không tự thêm API tải ảnh lên.
- [ ] **DET-Q04** — Chốt nhãn thống nhất giữa “Vô hiệu hóa”, “Bị khóa” và “Khóa tài khoản”. Code hiện có hai trạng thái `hoat_dong` và `bi_khoa`, không có trạng thái thứ ba cho vô hiệu hóa.

## 6. ADM-04 — Quản lý vai trò

Ảnh nguồn: `quan_ly_vai_tro.png`. Route hiện có: `/admin/vai-tro`. Mục sidebar đang chọn: “Quản lý vai trò”.

### 6.1. Nội dung và thao tác

Tiêu đề **Quản lý vai trò**; thanh công cụ có ô **Tìm vai trò** bên trái và nút **+ Tạo vai trò** bên phải. Bảng gồm **STT**, **Tên vai trò**, **Mô tả**, **Thao tác**. Cuối bảng có chọn số dòng/trang và dãy số trang như danh sách tài khoản.

Ảnh minh họa Quản trị viên, Quản lý kho, Nhân viên, Cộng tác viên và Hỗ trợ kỹ thuật. Ba hàng đầu có nút “Xóa” vô hiệu hóa và icon thông tin; hai hàng sau có nút “Xóa” màu đỏ. Tất cả các hàng có nút “Sửa”.

- [x] **ROL-01** — Có trang lấy danh sách vai trò từ API. Hiện hiển thị mã vai trò, tên hiển thị và phạm vi được mô tả trong frontend.
- [ ] **ROL-02** — Có tiêu đề, ô tìm kiếm, nút tạo và bố cục bảng đúng ảnh.
- [ ] **ROL-03** — Có cột STT và Mô tả tương ứng thiết kế. Response vai trò hiện chỉ có `id`, `ma_vai_tro`, `ten_vai_tro`; phần phạm vi đang là nội dung viết trong frontend.
- [ ] **ROL-04** — Có luồng tạo vai trò. Hiện không có form hoặc endpoint ghi vai trò tương ứng.
- [ ] **ROL-05** — Có luồng sửa vai trò. Nút “Sửa tên” hiện bị vô hiệu hóa với lý do chưa có API.
- [ ] **ROL-06** — Có luồng xóa vai trò và trình bày nút không được xóa kèm giải thích như ảnh. Hiện chưa có chức năng này.
- [ ] **ROL-07** — Có tìm kiếm, chọn số dòng/trang và thanh phân trang theo ảnh. Hiện trang lấy toàn bộ lựa chọn vai trò, không có các điều khiển này.

### 6.2. Mâu thuẫn và điểm cần xác nhận

- [ ] **ROL-Q01** — Chốt có mở rộng từ ba mã vai trò cố định sang vai trò tạo động hay không. Code hiện chỉ nhận `quan_tri_vien`, `quan_ly`, `nhan_vien`; frontend cũng kiểm tra quyền theo ba mã này. Hai vai trò bổ sung trong ảnh chưa phải vai trò được hệ thống hỗ trợ.
- [ ] **ROL-Q02** — Chốt quyền nào được gán cho vai trò mới, phạm vi thao tác của từng vai trò và UI cấu hình quyền. Ảnh chỉ có danh sách và mô tả, không có ma trận phân quyền.
- [ ] **ROL-Q03** — Chốt lý do ba nút Xóa bị vô hiệu hóa: vai trò hệ thống, đang có tài khoản sử dụng hay quy tắc khác. Icon thông tin trong ảnh không đủ để kết luận.
- [ ] **ROL-Q04** — Chốt form tạo/sửa, yêu cầu tên/mô tả, kiểm tra trùng, điều kiện xóa và nội dung xác nhận xóa. Chưa có ảnh các form này.
- [ ] **ROL-Q05** — Làm rõ số liệu minh họa: tổng quan ghi 3 vai trò nhưng danh sách vai trò có 5 hàng. Dữ liệu thật giữa các màn hình phải nhất quán, không sao chép các số minh họa thành quy tắc.

Các mục tạo/sửa/xóa vai trò được ghi nhận là thành phần trong thiết kế đích. Triển khai chúng sẽ ảnh hưởng hợp đồng API và cơ chế phân quyền, cần dev chốt phạm vi riêng; tác vụ tài liệu này không sửa các phần đó.

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
- [ ] **CFM-02** — Áp dụng popup “Xác nhận thay đổi” vào bước lưu chỉnh sửa thông tin tài khoản. Form hiện gọi lưu trực tiếp; popup hiện dùng cho đổi vai trò và khóa/mở khóa.
- [ ] **CFM-03** — Trình bày nền tối, viền, bo góc, kích thước tương đối và hai nút như ảnh.
- [x] **CFM-04** — Cơ chế xác nhận hiện chỉ gọi hành động ghi khi bấm Xác nhận; Hủy/X đóng mà không gọi hành động đó.
- [x] **CFM-05** — Khi đang xác nhận, chặn gửi lặp, đổi nhãn thành “Đang xử lý…”, vô hiệu hóa nút xác nhận/hủy/đóng và không đóng bằng Escape.
- [x] **CFM-06** — Khi hành động lỗi, hộp thoại hiện giữ mở, hiển thị lỗi; không báo thành công. Khi thành công, hộp thoại đóng.
- [x] **CFM-07** — Hộp thoại hiện có tên truy cập được qua tiêu đề; khi đóng trả focus về phần tử mở nếu phần tử còn tồn tại.
- [ ] **CFM-Q01** — Chốt popup áp dụng cho lưu hồ sơ, tạo mới hay cả hai. Ảnh thể hiện thay đổi thông tin trên trang chi tiết, không xác định quy tắc cho tạo mới.
- [ ] **CFM-Q02** — Chốt nội dung riêng cho vô hiệu hóa/mở khóa và xóa vai trò; không mặc nhiên dùng câu “thay đổi thông tin” cho mọi hành động.

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

Các mục dưới đây là việc cần kiểm tra trên ứng dụng sau khi triển khai. Tất cả để trống vì tác vụ hiện tại chỉ lập tài liệu và đối chiếu source.

- [ ] **QA-01** — Đối chiếu cả 5 màn hình desktop với ảnh nguồn: bố cục, nền, logo, hình sidebar, chữ, icon, badge và khoảng cách.
- [ ] **QA-02** — Menu chuyển đúng trang, active đúng; breadcrumb và Quay lại từ chi tiết trở về danh sách.
- [ ] **QA-03** — Tổng số tài khoản, số hoạt động/bị khóa và phân bổ vai trò nhất quán với dữ liệu thực, không dùng số cố định từ ảnh.
- [ ] **QA-04** — Tìm kiếm và phối hợp bộ lọc hoạt động đúng; đổi bộ lọc đưa về trang đầu; dữ liệu rỗng có thông báo rõ ràng.
- [ ] **QA-05** — Phân trang không vượt giới hạn; đổi số dòng/trang và số thứ tự hàng đúng theo quy tắc đã chốt.
- [ ] **QA-06** — Chi tiết mở đúng tài khoản; trường trống, ngày tháng, số điện thoại và hệ số lương hiển thị hợp lệ; không lộ thông tin mật khẩu.
- [ ] **QA-07** — Tạo/sửa hồ sơ và đổi vai trò gửi đúng nhóm trường; nhập sai hoặc trùng dữ liệu có phản hồi, không báo lưu thành công khi API lỗi.
- [ ] **QA-08** — Vô hiệu hóa/mở khóa yêu cầu xác nhận; sau thành công badge và thao tác thay đổi đúng; hồ sơ và lịch sử được giữ nguyên.
- [ ] **QA-09** — Hủy/X popup không ghi dữ liệu; bấm Xác nhận nhiều lần chỉ gửi một hành động; lỗi giữ đủ thông tin để người dùng xử lý.
- [ ] **QA-10** — Tạo/sửa/xóa vai trò chỉ nghiệm thu sau khi các mục `ROL-Q01` đến `ROL-Q04` được chốt và có API tương ứng.
- [ ] **QA-11** — Kiểm tra truy cập URL trực tiếp khi chưa đăng nhập/sai quyền và khi phiên hết hạn; giữ phản hồi 401/403 của hệ thống.
- [ ] **QA-12** — Kiểm tra cập nhật đồng thời: lỗi 412/428 không ghi đè dữ liệu; người dùng được hướng dẫn tải lại.
- [ ] **QA-13** — Dùng bàn phím truy cập được bộ lọc, bảng, nút và popup; focus nhìn thấy, nằm trong popup khi mở và trở về nơi mở khi đóng; icon thao tác có tên dễ hiểu.
- [ ] **QA-14** — Kiểm tra độ tương phản chữ/nền và khả năng đọc trạng thái bằng nhãn/icon, không chỉ bằng màu sau khi đổi sang giao diện tối.
- [ ] **QA-Q01** — Chốt yêu cầu tablet/mobile và hành vi co giãn. Bộ ảnh hiện chỉ đặc tả desktop, chưa đủ căn cứ nghiệm thu responsive theo thiết kế.

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
| Kiểm thử hiện có đã đọc | `frontend/tests/browser/mutations.spec.js`, `navigation.spec.js`, `record-dialog.spec.js` |

Đã xem trực tiếp đủ 5 ảnh và đọc các source nêu trên. Chưa chạy ứng dụng, chưa chạy lại các kiểm thử frontend/backend hoặc E2E, chưa kiểm tra hình ảnh trên trình duyệt và chưa xác minh database đang chạy. Việc tồn tại test trong source không được coi là test đã chạy đạt. Tác vụ này chỉ tạo tài liệu; không triển khai UI, thay API/schema hoặc thay dữ liệu.
