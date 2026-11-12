# Đặc tả yêu cầu UI/UX frontend Cổng Nhân viên (Employee Portal) — xBike MRP

Ngày cập nhật: **12/11/2026**. Nhánh bàn giao: `feature/UI-nhanvien`.
Căn cứ thiết kế chuẩn: **`C:\Users\binhb\Downloads\XBIKE_Employee_Portal_Preview (1).html`** (SHA256: `80582902F488AE1BD3D4E944BFAA05EE98483955D5FA002B5BFE1B82646B99CB`, lưu trong repository tại `doc/ui-nhan-vien-preview/employee-portal-preview.html`).

**Cập nhật màu theo chỉ đạo dev ngày 12/11/2026:** bố cục tham chiếu preview; màu giao diện lấy từ Admin hiện tại trong [App.css](../frontend/src/app/App.css) (khối `.admin-shell`, bảng, form, dialog, toast) và [Sidebar.module.css](../frontend/src/layouts/Sidebar.module.css) (khối `.admin`). Màu trong mục 10 và checklist của tài liệu này được ưu tiên hơn màu gốc trong HTML/ảnh preview. Frontend nhân viên đã áp dụng theme này trong đợt chỉnh sửa hiện tại; kết quả kiểm chứng được ghi ở mục 12 và `doc/MISSING.md`. Tiếp tục giữ nghiệp vụ, quyền và API hiện tại theo lựa chọn của dev; các khác biệt nghiệp vụ trong preview phải ghi riêng để chờ duyệt.

---

## 1. Phạm vi, căn cứ và nguyên tắc chuyển đổi

### 1.1. Bối cảnh và quyết định
Theo chỉ đạo trực tiếp của dev ngày **11/11/2026**, toàn bộ giao diện khu vực Nhân viên (`nhan_vien`) được chuẩn hóa và thiết kế lại theo bản mẫu prototype preview `XBIKE_Employee_Portal_Preview (1).html`. Tài liệu đặc tả này thay thế đặc tả cũ (vốn trước đây tạm giữ giao diện nền sáng) để chuyển sang **hệ giao diện công nghiệp tối ấm (Warm Industrial Dark Theme)**, đồng bộ phong cách nhận diện thương hiệu với khu vực Admin đã duyệt, đồng thời định nghĩa chi tiết từng màn hình, thông số CSS/token, luồng tương tác và ánh xạ hợp đồng API thực tế.

### 1.2. Nguyên tắc triển khai cốt lõi
1. **Làm đúng thiết kế mẫu**: Bám sát cấu trúc bố cục, typography, card thống kê, thanh tiến độ, icon, modal và responsive trong preview HTML; riêng màu sắc dùng hệ màu Admin tại mục 10 theo cập nhật ngày 12/11/2026.
2. **Bảo toàn nghiệp vụ và phân quyền backend**: Giữ đúng nghiệp vụ, phân quyền và API hiện tại theo quyết định ngày 12/11/2026 của dev ("Đổi giao diện theo mẫu, giữ nghiệp vụ/quyền/API hiện tại; ghi riêng các khác biệt cho duyệt"). UI nhân viên phục vụ ghi nhận công việc thực tế (bắt đầu lệnh sản xuất khi đủ vật tư, lập/sửa/xóa nháp chứng từ hoàn thành và gửi duyệt, tra cứu yêu cầu/phiếu xuất/tồn kho được phân công). Quyền lập phiếu xuất hiện chỉ dành cho quản lý (FE-MISS-007); các trường chưa có trong API như sản phẩm lỗi badQty, ghi chú chứng từ (FE-MISS-006) và tồn tối thiểu min_stock (FE-MISS-008) được ghi nhận là khác biệt preview chờ duyệt, không render các ô nhập không được hỗ trợ rồi âm thầm bỏ qua.
3. **Ánh xạ hợp đồng API minh bạch**: Kết nối chính xác các endpoint hiện có trong `frontend/src/lib/api/endpoints.js`. Bất kỳ trường nào preview có nhưng API chưa hỗ trợ (hoặc khác biệt về vai trò) được ghi nhận vào `doc/MISSING.md` và giải quyết theo đúng [FRONTEND_RULES.md](./FRONTEND_RULES.md).
4. **Cách đánh dấu tiến độ**:
   - `[x]`: Đã triển khai và có bằng chứng đối chiếu trong source code / kết quả test.
   - `[ ]`: Chưa được nghiệm thu, còn khác biệt chờ quyết định hoặc chưa có đủ bằng chứng kiểm chứng.

---

## 2. Vai trò và giới hạn quyền trong khu vực Nhân viên

| Phân hệ / Màn hình | Quyền hạn của Nhân viên (`nhan_vien`) | Ánh xạ Backend & Quy tắc an toàn |
| --- | --- | --- |
| **Tổng quan (`/nv`)** | Xem 4 thẻ thống kê tổng hợp (tính theo `meta.total` của API), danh sách yêu cầu cần xử lý, việc tiếp theo, cảnh báo vật tư, chứng từ hoàn thành gần đây. | Đọc dữ liệu qua các API tài nguyên: `API.requests`, `API.orders`, `API.completions`, `API.items`; liên kết tra cứu phiếu xuất dẫn sang trang riêng. Nút tạo phiếu xuất demo trong preview là khác biệt ghi nhận tại FE-MISS-007. |
| **Yêu cầu sản xuất (`/nv/yeu-cau`)** | Xem danh sách yêu cầu được giao, lọc danh sách, xem chi tiết và BOM. | Nhân viên chỉ xem yêu cầu; không có nút tạo/sửa/hủy yêu cầu. Nút tạo phiếu xuất preview ghi nhận tại FE-MISS-007 (quyền thuộc quản lý). |
| **Lệnh sản xuất (`/nv/lenh-sx`)** | Xem danh sách lệnh, lọc theo trạng thái; theo dõi tiến độ; xem chi tiết lệnh; bắt đầu sản xuất khi đủ vật tư; mở tạo chứng từ hoàn thành. | `POST /api/v1/lenh_san_xuat/{id}/bat_dau` khi lệnh đã giao và đủ vật tư (start-order material gate giữ nguyên). |
| **Chứng từ hoàn thành (`/nv/hoan-thanh`)** | Xem danh sách chứng từ của bản thân; tạo/sửa/xóa chứng từ hoàn thành nháp; gửi duyệt chứng từ nháp. | `POST /api/v1/chung_tu_hoan_thanh_sx` tạo nháp với `lenh_san_xuat_id`, `so_luong_hoan_thanh`, `finish_time`; `POST .../gui` gửi duyệt. Trường `badQty` và `note` ghi nhận tại FE-MISS-006 chờ duyệt. |
| **Tra cứu phiếu xuất (`/nv/phieu-xuat`)** | Tra cứu các phiếu xuất thành phẩm và vật tư liên quan đến công việc được giao (chỉ đọc). | Backend `WriteActor` của phiếu xuất là `quan_ly`. Quyền tạo phiếu xuất của nhân viên là khác biệt preview ghi nhận tại FE-MISS-007 chờ duyệt. |
| **Tra cứu tồn kho (`/nv/ton-kho`)** | Tra cứu số lượng tồn của thành phẩm và nguyên vật liệu. | Chỉ đọc qua `GET /api/v1/mat_hang`; hiển thị `so_luong_ton` thực tế. Cảnh báo `min_stock` là khác biệt preview ghi nhận tại FE-MISS-008 chờ duyệt. |
| **Hồ sơ & Đổi mật khẩu (`/ho-so`)** | Xem thông tin tài khoản bản thân và tự đổi mật khẩu. | `GET /api/v1/auth/me`, `POST /api/v1/auth/doi_mat_khau`. |

---

## 3. Điều hướng và Khung giao diện (Layout Shell)

### 3.1. Danh mục điều hướng Sidebar (Đúng 6 mục theo Preview)

| STT | Tên mục | Đường dẫn (Route) | Icon mẫu | Lucide Icon tương ứng | Counter / Tag |
| :---: | --- | --- | :--- | :--- | :--- |
| 1 | **Tổng quan** | `/nv` | `house` | `<Home size={18} />` | — |
| 2 | **Yêu cầu sản xuất** | `/nv/yeu-cau` | `clipboard-list` | `<ClipboardList size={18} />` | Số yêu cầu đang xử lý (badge cam) |
| 3 | **Lệnh sản xuất** | `/nv/lenh-sx` | `factory` | `<Factory size={18} />` | — |
| 4 | **Chứng từ hoàn thành** | `/nv/hoan-thanh` | `file-check` | `<FileCheck size={18} />` | — |
| 5 | **Tra cứu phiếu xuất** | `/nv/phieu-xuat` | `package` | `<Package size={18} />` | — |
| 6 | **Tra cứu tồn kho** | `/nv/ton-kho` | `boxes` | `<Boxes size={18} />` | — |

- [ ] **NAV-01**: Cập nhật `navigation.js` cho vai trò `nhan_vien` gồm đủ 6 mục trên với đúng thứ tự và nhãn hiển thị.
- [ ] **NAV-02**: Sidebar hiển thị logo thương hiệu `XBIKE` nghiêng và subline `MRP SYSTEM™` ở phần header (cao 96px); danh sách 6 link điều hướng; và ảnh xe đạp hoàng hôn ở 54% phần đáy sidebar.
- [ ] **NAV-03**: Badge số đếm trên mục "Yêu cầu sản xuất" tự động cập nhật theo số lượng bản ghi thực tế từ API.

### 3.2. Cấu trúc Topbar
- **Bên trái**:
  + Nút mở menu mobile (chỉ hiện trên màn hình nhỏ <= 700px).
  + Breadcrumb trực quan: Icon `Home` (nhà) + `ChevronRight` + Tên trang hiện tại (ví dụ: `Tổng quan`, `Lệnh sản xuất`, `Yêu cầu sản xuất`, ...).
- **Bên phải**:
  + Module pill: Tag bo tròn nền tối viền nhẹ: `Kho & sản xuất`.
  + Profile button: Avatar tròn chứa 2 chữ cái viết tắt (ví dụ `TA`), Họ tên nhân viên (in đậm) + Mã nhân viên (chữ nhỏ, ví dụ: `Trần Minh Anh` / `Nhân viên · NV-000012`), kèm icon `ChevronDown`.
  + Dropdown menu khi click profile: Thông tin người dùng, vai trò, liên kết `Hồ sơ & đổi mật khẩu` (`/ho-so`), và nút `Đăng xuất`.

---

## 4. Đặc tả Màn hình 1: Tổng quan (`/nv`)

### 4.1. Header & Hành động chính
- Tiêu đề: **Tổng quan công việc**.
- Mô tả phụ: Hiển thị tổng quan công việc được giao và các cảnh báo liên quan.
- Khối bên phải:
  + Nhãn ngày hiện tại: Icon lịch + chuỗi ngày định dạng Việt Nam (ví dụ: `11 tháng 11, 2026`).
  + Nút hành động: `Tạo chứng từ hoàn thành SX` (chuyển tới `/nv/hoan-thanh/moi`). Nút tạo phiếu xuất thành phẩm trong preview là khác biệt ghi nhận tại FE-MISS-007, không hiển thị hành động ghi vượt quyền backend.

### 4.2. Thẻ thống kê nhanh (4 Stat Cards)
Bố cục grid 4 cột (desktop), 2 cột (tablet/mobile), mỗi thẻ có nhãn, số đếm lớn (size 31–34px) lấy từ `meta.total` của API tài nguyên thực tế, dòng mô tả, icon góc trên phải:
1. **Yêu cầu phụ trách**: Tổng số yêu cầu phụ trách; mô tả: "Theo dõi từ sản xuất đến xuất kho"; icon `clipboard-list`; click chuyển tới `/nv/yeu-cau`.
2. **Lệnh đã giao**: Số lệnh chờ bắt đầu; mô tả: "Lệnh sản xuất đã được phân công"; icon `factory`; click chuyển tới `/nv/lenh-sx`.
3. **Đang thực hiện**: Số lệnh đang sản xuất; mô tả: "Đang trong quá trình gia công / lắp ráp"; icon `factory`; click chuyển tới `/nv/lenh-sx`.
4. **Hoàn thành chờ duyệt**: Số chứng từ đang chờ quản lý phê duyệt; mô tả: "Chờ quản lý ghi nhận đầu ra"; icon `file-check`; click chuyển tới `/nv/hoan-thanh`.

### 4.3. Bố cục Dashboard Grid (Tỷ lệ 3.07fr : 0.77fr)
- **Cột trái (Panel chính: Yêu cầu sản xuất được giao)**:
  + Tiêu đề panel: `Yêu cầu sản xuất được giao` kèm badge `meta.total`; mô tả yêu cầu được phân công; liên kết "Xem tất cả ->" (chuyển `/nv/yeu-cau`).
  + Ba tab chỉ lọc các dòng đang hiển thị trong panel: `Tất cả`; `Cần sản xuất` cho yêu cầu ở trạng thái `da_gui`, `cho_bo_sung_vat_tu` hoặc `dang_thuc_hien`; `Chờ duyệt chứng từ` cho yêu cầu có lệnh liên quan (`lenh_san_xuat_ids`) gắn với chứng từ `cho_duyet`. Tab không thay số đếm `meta.total` hoặc lọc toàn bộ dữ liệu phân trang. Không có tab `Sẵn sàng xuất` cho nhân viên.
  + Bảng dữ liệu Yêu cầu (Data Table):
    - Cột 1: `Yêu cầu / Thành phẩm` (Mã YCSX dạng nút bấm màu cam mở modal chi tiết + Tên thành phẩm bên dưới).
    - Cột 2: `SL yêu cầu` (Căn giữa, số to + đơn vị tính).
    - Cột 3: `Tồn hiện có` (Căn giữa, số tồn thực tế + đơn vị tính).
    - Cột 4: `Trạng thái` (Badge trạng thái màu tương ứng).
    - Cột 5: `Thao tác` (Nút "Theo dõi yêu cầu" mở modal). Nút tạo phiếu xuất preview ghi nhận tại FE-MISS-007.
- **Cột phải (Sidepanels)**:
  + Panel 1: **Việc tiếp theo**:
    - Danh sách việc cần ưu tiên dựa trên các lệnh và chứng từ thực tế của nhân viên.
  + Panel 2: **Cảnh báo / Lưu ý**:
    - Tiêu đề icon cảnh báo màu cam: `Yêu cầu chờ cấp vật tư`.
    - Nội dung: Tên sản phẩm của yêu cầu `cho_bo_sung_vat_tu` từ API, hoặc trạng thái rỗng khi không có yêu cầu cần bổ sung.
    - Link liên kết: "Xem yêu cầu ... ->" mở modal chi tiết yêu cầu đó.
- **Hàng dưới (Bottom Panel: Chứng từ gần đây)**:
  + Panel toàn chiều rộng: "Chứng từ gần đây", link "Xem tất cả ->" (chuyển `/nv/hoan-thanh`).
  + Bảng tóm tắt 6 cột: Mã chứng từ / Lệnh sản xuất | Tên thành phẩm | Ngày tạo | Số lượng | Trạng thái (badge) | Thao tác (Xem chi tiết). Sắp xếp theo `-id` (do API HoanThanhSort không hỗ trợ `-created_at`).

---

## 5. Đặc tả Màn hình 2: Lệnh sản xuất (`/nv/lenh-sx`)

### 5.1. Header & Bộ lọc thẻ Stat Filter Cards
- Tiêu đề: **Lệnh sản xuất**.
- Mô tả phụ: "Theo dõi kế hoạch, sản lượng ghi nhận và trạng thái của từng lệnh."
- 4 thẻ lọc tương tác, đếm theo `meta.total` của API lệnh và hiển thị `aria-pressed`: **Tất cả lệnh**, **Đã giao**, **Đang thực hiện**, **Hoàn thành**. Hai nhóm preview “Chờ cấp vật tư” và “Chờ duyệt chứng từ” không phải trạng thái lọc lệnh trong API hiện tại; ghi nhận khác biệt tại FE-MISS-009, không tự suy diễn từ một trang kết quả.

### 5.2. Công cụ tìm kiếm & Bảng dữ liệu lệnh
- **Page tools**:
  + Ô tìm kiếm (Searchbox): Tìm theo mã lệnh qua tham số `q`. Tìm mã yêu cầu, tên thành phẩm và SKU trong preview chưa được API lệnh hỗ trợ; ghi nhận tại FE-MISS-009.
  + Select box lọc theo các trạng thái API hiện có: `nhap`, `da_gui`, `dang_thuc_hien`, `hoan_thanh`, `da_huy`. Hai nhóm trạng thái tổng hợp trong preview ghi nhận tại FE-MISS-009.
- **Cấu trúc bảng (Order Table)**:
  + Cột 1: `Lệnh / Yêu cầu` — Mã lệnh (nút màu cam mở chi tiết) + Mã yêu cầu nguồn bên dưới.
  + Cột 2: `Thành phẩm` — Tên thành phẩm + SKU bên dưới.
  + Cột 3: `Ghi nhận / Kế hoạch` — Dòng text `{SL đã ghi nhận} / {SL kế hoạch} chiếc` + **Thanh tiến độ trực quan** (`<progress class="order-progress">` có màu cam `--accent`).
  + Cột 4: `Bắt đầu` — hiển thị `started_at` nếu có. `Hạn hoàn thành` trong preview chưa có trong `LenhRead`; ghi nhận tại FE-MISS-009.
  + Cột 5: `Trạng thái` — Badge trạng thái với chấm tròn màu nhận diện.
  + Cột 6: `Thao tác` — Nút "Xem lệnh" kèm icon chevron-right.

### 5.3. Modal Chi tiết Lệnh sản xuất
- Header: `Chi tiết lệnh sản xuất` — Phụ đề: `{Mã lệnh} · {Tên thành phẩm}`.
- Khối Detail Grid 2 cột:
  + Yêu cầu sản xuất (Link mở chi tiết yêu cầu liên quan).
  + Trạng thái (Badge).
  + Bắt đầu lúc (`started_at`); hạn hoàn thành của preview chờ FE-MISS-009.
  + Sản lượng kế hoạch.
  + Sản lượng đã duyệt.
  + Sản lượng chờ duyệt.
- Section Chứng từ hoàn thành liên quan: Danh sách các chứng từ đã lập cho lệnh này (Mã chứng từ + Badge trạng thái).
- Footer: Nút `Đóng`; nếu lệnh ở trạng thái `Đang sản xuất` thì hiển thị nút màu cam `+ Tạo chứng từ hoàn thành` (mở ngay form lập chứng từ cho lệnh này).

---

## 6. Đặc tả Màn hình 3: Yêu cầu sản xuất (`/nv/yeu-cau`)

### 6.1. Header, Ghi chú & Bộ lọc
- Tiêu đề: **Yêu cầu sản xuất**.
- Mô tả phụ: "Theo dõi các yêu cầu được phân công, từ cấp vật tư đến xuất thành phẩm."
- Khung ghi chú hướng dẫn (Intro Note): Icon thông tin màu cam + "Nhân viên theo dõi tiến độ các yêu cầu được phân công. Quyền lập và phê duyệt phiếu xuất kho thuộc về Quản lý."
- Công cụ tìm kiếm: Ô Searchbox tìm theo mã yêu cầu (theo hỗ trợ hiện tại của backend API).
- Bộ lọc trạng thái dùng các trạng thái yêu cầu thực có trong API. Bộ lọc tổng hợp trên toàn bộ kết quả của trang này vẫn cần dữ liệu/quy tắc backend; khác với ba tab lọc cục bộ trên dashboard tại mục 4.3 và được ghi nhận tại FE-MISS-011.
- Bảng dữ liệu: Danh sách yêu cầu sản xuất của nhân viên. Thao tác "Theo dõi yêu cầu" mở modal chi tiết. Nút tạo phiếu xuất preview là khác biệt ghi nhận tại FE-MISS-007.

### 6.2. Modal Chi tiết Yêu cầu sản xuất
- Detail Grid: Mã yêu cầu, trạng thái, số lượng yêu cầu/đã xuất/còn phải xuất, tồn kho hiện có, mã hàng và thời điểm tạo/hoàn thành từ API.
- Section Lệnh sản xuất liên quan: Danh sách các lệnh sản xuất thuộc yêu cầu này.
- Ghi chú xử lý và bảng vật tư BOM tổng hợp trên chính yêu cầu trong preview chưa có trong `YeuCauRead`/`KeHoachRead`; ghi khác biệt tại FE-MISS-010. Chi tiết vật tư hiện xem theo từng lệnh được phân công qua API `/lenh_san_xuat/{id}/vat_tu`.
- Footer: Nút `Đóng`.

---

## 7. Đặc tả Màn hình 4: Chứng từ hoàn thành (`/nv/hoan-thanh`)

### 7.1. Danh sách chứng từ
- Tiêu đề: **Chứng từ hoàn thành**.
- Mô tả: "Lập và theo dõi chứng từ ghi nhận kết quả sản xuất."
- Nút hành động: `+ Tạo chứng từ hoàn thành`.
- Công cụ tìm kiếm & lọc: Ô Searchbox + Dropdown lọc trạng thái: `Tất cả trạng thái` / `Nháp` / `Chờ duyệt` / `Đã duyệt` / `Từ chối`.
- Bảng dữ liệu:
  + Cột 1: `Chứng từ / Lệnh sản xuất` (Mã chứng từ + Mã lệnh bên dưới).
  + Cột 2: `Tên thành phẩm`.
  + Cột 3: `Ngày tạo` (`dd/MM/yyyy`).
  + Cột 4: `Số lượng` (Số lượng đạt + đơn vị).
  + Cột 5: `Trạng thái` (Badge: Nháp / Chờ duyệt / Đã duyệt / Từ chối).
  + Cột 6: `Thao tác` (Xem chi tiết / Sửa nháp / Gửi duyệt / Trả về nháp nếu bị từ chối).

### 7.2. Modal Tạo/Sửa chứng từ hoàn thành
- Khung thông tin: Icon thông tin + "Nhân viên chỉ ghi nhận sản lượng thực tế. Nhập kho thành phẩm phải được quản lý duyệt/xác nhận riêng."
- Form Grid:
  + `Lệnh sản xuất *` (Dropdown chỉ hiển thị lệnh đang thực hiện của nhân viên; mở từ chi tiết lệnh thì chọn sẵn và khóa; mở từ nút chung thì cho chọn một lần rồi khóa; giá trị vẫn được gửi khi tạo chứng từ).
  + `Số lượng hoàn thành *` (Input number, min=1).
  + `Thời điểm hoàn thành` (Input datetime-local tự điền giờ Việt Nam và chỉ đọc khi tạo mới; khi sửa bản nháp hiện có vẫn cho chỉnh sửa).
  + *Ghi chú về khác biệt preview*: Ô nhập `Sản phẩm lỗi` (`badQty`) và textarea `Ghi chú sản xuất` (`docNote`) trong preview chưa có trường tương ứng trong schema backend `HoanThanhCreate` (`extra="forbid"`), được ghi nhận tại FE-MISS-006 chờ dev quyết định; không render ô nhập unsupported rồi âm thầm bỏ qua.
- Footer: Nút `Hủy` + Nút `Lưu nháp` (hoặc gửi duyệt theo luồng đã hỗ trợ).

### 7.3. Modal Chi tiết chứng từ
- Detail Grid: Mã chứng từ, Trạng thái, Lệnh sản xuất, Số lượng hoàn thành, Thời điểm hoàn thành.
- Footer: Nút `Đóng` + Nút thao tác theo trạng thái (Sửa/Gửi duyệt nếu nháp; Trả về nháp nếu từ chối).

---

## 8. Đặc tả Màn hình 5: Tra cứu phiếu xuất (`/nv/phieu-xuat`)

### 8.1. Danh sách phiếu xuất
- Tiêu đề: **Tra cứu phiếu xuất**.
- Mô tả: "Theo dõi các phiếu xuất kho liên quan đến công việc được giao."
- Khung hướng dẫn: "Chức năng chỉ xem phiếu xuất liên quan. Quản lý kho lập và duyệt phiếu xuất."
- Nút tạo phiếu xuất trong preview: Là khác biệt ghi nhận tại FE-MISS-007; backend `WriteActor` chỉ cấp quyền ghi cho `quan_ly`. Nhân viên chỉ tra cứu.
- Công cụ: Ô Searchbox + Dropdown lọc loại phiếu (`xuat_vat_tu`, `xuat_thanh_pham`) hoặc trạng thái.
- Bảng dữ liệu:
  + Cột 1: `Mã phiếu / Loại phiếu`.
  + Cột 2: `Mặt hàng / Chi tiết`.
  + Cột 3: `Ngày lập`.
  + Cột 4: `Số lượng xuất`.
  + Cột 5: `Trạng thái` (Badge).
  + Cột 6: `Thao tác` ("Xem phiếu").

### 8.2. Chi tiết phiếu xuất
- Modal/Drawer hiển thị chi tiết phiếu xuất (chỉ đọc) gồm người lập, ngày xuất, danh sách mặt hàng, trạng thái phê duyệt.

---

## 9. Đặc tả Màn hình 6: Tra cứu tồn kho (`/nv/ton-kho`)

### 9.1. Danh sách tồn kho
- Tiêu đề: **Tra cứu tồn kho**.
- Mô tả: "Kiểm tra số lượng thành phẩm và nguyên vật liệu trước khi thực hiện công việc."
- Khung hướng dẫn: "Chức năng này chỉ cho phép xem, nhân viên không thể chỉnh sửa trực tiếp tồn kho."
- Công cụ: Ô Searchbox + Dropdown lọc loại hàng: `Tất cả loại hàng` / `Thành phẩm` / `Nguyên vật liệu`.
- Bảng dữ liệu:
  + Cột 1: `Mã hàng` (SKU).
  + Cột 2: `Tên hàng`.
  + Cột 3: `Loại` (Thành phẩm / Nguyên vật liệu).
  + Cột 4: `Số lượng tồn` (Căn giữa, số lượng in đậm + đơn vị tính thực tế).
  + *Ghi chú khác biệt preview*: Mức cảnh báo tồn tối thiểu `min` và tag `Đủ tồn tối thiểu` / `Thấp / thiếu` trong preview là khác biệt ghi nhận tại FE-MISS-008 do schema `MatHang` chưa có trường này; UI hiển thị đúng số tồn thực tế từ API.
  + Cột 5: `Thao tác` (Nút "Chi tiết" mở modal chỉ đọc).

### 9.2. Modal Chi tiết tồn kho
- Detail Grid: Mã hàng, Tên hàng, Loại hàng, Số lượng tồn, Đơn vị tính.
- Thông báo quyền chỉ đọc.
- Footer: Nút `Đóng`.

---

## 10. Thông số thiết kế — bố cục Preview, hệ màu Admin

### 10.1. Hệ màu theo Admin hiện tại

Nguồn đối chiếu là CSS đang có trong repository, không lấy màu từ bản HTML demo hoặc tự suy ra từ ảnh. Tên biến dưới đây là ánh xạ phục vụ đặc tả; frontend hiện dùng giá trị CSS trực tiếp theo theme nhân viên. Giới hạn theme nhân viên và ngữ cảnh dialog của nhân viên, không ghi đè `:root` toàn hệ thống hoặc thay màu Admin/Quản lý.

```css
.employee-shell {
  color-scheme: dark;
  --bg: #14100d;
  --sidebar: #1b1511;
  --surface: #211b17;
  --surface-2: #221c18;
  --surface-3: #2c241e;
  --line: #362c25;
  --line-soft: #2b231d;
  --text: #f4ede6;
  --muted: #b4a89c;
  --subtle: #b7aba0;
  --accent: #df6d27;
  --accent-hover: #eb7a34;
  --green: #9be54c;
  --green-bg: #233818;
  --gold: #f7b948;
  --gold-bg: #3d2a14;
  --red: #f87171;
  --red-bg: #3b1b19;
  --radius: 12px;
}
```

| Thành phần | Màu yêu cầu | Selector Admin làm căn cứ |
| --- | --- | --- |
| Nền trang và topbar | `#14100d`; chữ chính `#f4ede6`, tiêu đề `#fff` | `.admin-shell`, `html[data-admin-theme="true"]`, `.admin-page-heading h1` |
| Sidebar | Nền `#1b1511`, viền `#2b231d`, chữ `#e6ddd4`, icon `#d3c8bc` | `.admin`, `.admin .link` trong `Sidebar.module.css` |
| Menu được chọn | Nền `#df6d27`, chữ/icon `#fff`; hover menu thường `rgb(255 255 255 / 0.06)` | `.admin .link.active`, `.admin .link:hover` |
| Focus menu | Outline `#e06d2b` | `.admin .link:focus-visible` |
| Card/panel và KPI | Panel `#211b17`, KPI `#221c18`, viền cục bộ `#352b24` | `.admin-surface`, `.admin-stat-card` |
| Breadcrumb | Chữ `#cfc4b8`, trang hiện tại `#f0e7de`, home `#e38742`, dấu phân cách `#8c7f72` | `.admin-breadcrumb` và các selector con |
| Avatar và menu tài khoản | Avatar `#c86224`/`#fff`; menu `#251e19`, viền `#3c3129`; hover dòng `#312822` | `.admin-shell .user-menu .avatar`, `.user-dropdown` |
| Heading bảng | Nền `#2b231d`, chữ `#fff`, viền dưới `#382e27` | `.admin-table th` |
| Dòng bảng | Chữ `#f0e7de`, viền `#2c241e`, hover `#261f1a` | `.admin-table td`, `.admin-table tbody tr:hover` |
| Search/filter | Nền `#231d19`, viền `#493d33`, chữ `#f4ede6`, placeholder `#b5a99c` | `.admin-input-shell`, `.admin-select-shell` và input con |
| Input form | Nền `#171310`, viền `#3a312a`, chữ `#f4ede6`, label `#d6cbc0` | `.admin-shell .field`, dialog `.field` |
| Input disabled | Nền `#14110e`, chữ `#7c7166` | `.admin-shell .field input:disabled` và select/textarea |
| Input sửa inline nếu sử dụng | Nền `#2b241e`, viền `#d68a59`, chữ `#fff`; focus viền `#f06d1a`, halo `rgb(240 109 26 / 0.28)` | `.admin-inline-input`, `.admin-inline-select` |
| Nút primary / secondary | Primary `#df6d27`/`#fff`, hover `#eb7a34`; secondary `#28221d`, viền `#3d332c`, chữ `#f4ede6`, hover `#332b24` | `.admin-shell .btn-primary`, `.btn-secondary` |
| Thông báo info | Nền `#1d1815`, viền `#352d26`, chữ `#d6cbc0` | `.admin-shell .notice-info` |
| Thông báo cảnh báo | Nền `#2f2213`, viền `#543b1e`, chữ `#f8c572` | `.admin-shell .notice-warning` |
| Thông báo lỗi | Nền `#321818`, viền `#5c2828`, chữ `#fca5a5` | `.admin-shell .notice-error` |
| Modal/dialog | Nền `#231b16`, viền `#5a493c`, chữ `#f4ede6`; backdrop `rgb(8 6 5 / 0.72)`, shadow `0 24px 64px rgb(0 0 0 / 0.65)` | `html[data-admin-theme="true"] .record-dialog`, `.confirmation` và `::backdrop` |
| Toast | Nền `#26201b`, viền `#443930`, chữ `#fff` | `html[data-admin-theme="true"] .toast` |

Màu badge lấy theo nhóm `.admin-pill-*`; trạng thái vẫn ánh xạ theo enum hiện tại, không chuyển sang `pending/approved` của demo:

| Nhóm hiển thị | Nền | Viền | Chữ | Căn cứ |
| --- | --- | --- | --- | --- |
| Trung tính / nháp | `#322821` | `#493b31` | `#ece3da` | `.admin-pill-neutral` |
| Thông tin | `#172b3a` | `#25455e` | `#5bc0ff` | `.admin-pill-blue` |
| Cảnh báo / chờ duyệt | `#3d2a14` | `#5b3f1e` | `#f7b948` | `.admin-pill-amber` |
| Thành công / đã duyệt | `#233818` | `#365624` | `#9be54c` | `.admin-pill-green` |
| Lỗi / từ chối | `#3b1b19` | `#5c2926` | `#f87171` | `.admin-pill-red` |

Thanh tiến độ, đường nhấn tab và icon hành động dùng `--accent`; icon phụ và mô tả dùng màu phụ tương ứng trong bảng. Hình thức active/hover/focus/disabled phải phân biệt được bằng trạng thái, nhãn hoặc outline, không chỉ đổi màu. Các màu trên được đối chiếu source; chưa có kết luận đạt tương phản WCAG khi render trên UI nhân viên. Kiểm tra tương phản trên kích thước chữ thực tế, đặc biệt nút cam/chữ trắng và trạng thái disabled, trong đợt triển khai.

### 10.2. Typography & Font chữ
- Font hệ thống chính: `'Segoe UI', Inter, Arial, sans-serif`, fallback `IBM Plex Sans`.
- Base font size: `13px`, line-height `1.5`.
- Heading `h1` trang: `26px` (weight 750, line-height 1.2), mobile `22px`.
- Heading `h2` panel: `16px` (weight 700).
- Stat card number: `34px` (weight 800), mobile `31px`.
- Brand Logo: `Arial Black, Impact, sans-serif`, size `37px`, italic, transform `skew(-9deg)`.

### 10.3. Component Tokens
- **Stat Card**: background `var(--surface)`, border `1px solid var(--line)`, radius `12px`, padding `20px 22px`.
- **Panel / Card**: background `var(--surface)`, border `1px solid var(--line)`, radius `12px`.
- **Data Table**:
  + Th: font size `10px`, weight `500`, nền `#2b231d`, chữ `#fff`, padding `8px 20px 10px`, uppercase.
  + Td: padding `14px 20px`, chữ `#f0e7de`, border-top `1px solid #2c241e`; hover nền `#261f1a`.
- **Buttons**:
  + Primary: background `var(--accent)` (`#df6d27`), color `#fff`, radius `7px`, hover `#eb7a34`.
  + Secondary / Neutral: background `#28221d`, border `1px solid #3d332c`, color `#f4ede6`, hover `#332b24`.
- **Form Inputs / Selects**: form background `#171310`, border `1px solid #3a312a`, color `#f4ede6`, radius `6px`, min-height `40px`; search/filter dùng màu riêng tại mục 10.1.
- **Modals**: Record dialog rộng `min(640px, calc(100vw - 32px))`; confirmation giữ biến thể Admin tối đa 492px. Cả hai dùng nền `#231b16`, viền `#5a493c`, backdrop `rgb(8 6 5 / 0.72)`, shadow `0 24px 64px rgb(0 0 0 / 0.65)`.
- **Toasts**: background `#26201b`, border `1px solid #443930`, color `#fff`, shadow `0 12px 45px #0008`, radius `8px`.

### 10.4. Responsive Breakpoints
- **> 1450px**: Layout grid rộng rãi (3.07fr : 0.77fr).
- **<= 1450px**: Thu hẹp dashboard grid (2.2fr : 0.75fr), padding main `26px 24px 55px`.
- **<= 1160px**: Dashboard grid chuyển về 1 cột dọc; Sidepanels chuyển sang grid 2 cột ngang.
- **<= 920px**: Sidebar co về 220px; Stats grid chuyển sang 2 cột.
- **<= 700px**:
  + Sidebar ẩn sang trái (`transform: translateX(-100%)`), mở dạng trượt drawer (rộng 248px) kèm backdrop Admin `rgb(0 0 0 / 0.55)` (`.admin-sidebar-backdrop`).
  + Nút menu hamburger hiển thị trên Topbar.
  + Module pill ẩn, profile button thu gọn chỉ giữ avatar tròn 33px.
  + Padding main thu hẹp còn `21px 14px 45px`.

---

## 11. Kế hoạch sửa đổi file Source Code Frontend

Để chuyển đổi toàn bộ giao diện nhân viên hiện tại sang đúng mẫu preview HTML, các file sau đây cần được chỉnh sửa:

| File nguồn | Nội dung cần sửa đổi |
| --- | --- |
| `frontend/src/layouts/navigation.js` | Cập nhật danh sách menu nhân viên gồm đúng 6 mục: Tổng quan, Yêu cầu sản xuất, Lệnh sản xuất, Chứng từ hoàn thành, Tra cứu phiếu xuất, Tra cứu tồn kho. |
| `frontend/src/layouts/MainLayout.jsx` | Thêm chế độ theme dark cho nhân viên (`employeeTheme`), cấu hình Topbar có breadcrumb Home, module pill `Kho & sản xuất`, và menu profile theo style mới. |
| `frontend/src/layouts/Sidebar.jsx` & `Sidebar.module.css` | Áp dụng style dark cho sidebar nhân viên: header thương hiệu XBIKE MRP SYSTEM, 6 menu items, và ảnh xe đạp hoàng hôn. |
| `frontend/src/app/App.css` | Bổ sung biến CSS và các class phục vụ giao diện Employee Portal: `.dashboard-grid`, `.stat-card`, `.sidepanels`, `.next-task`, `.order-stats`, `.order-progress`, `.steps`, `.step-dot`, `.detail-grid`, v.v. |
| `frontend/src/features/dashboard/DashboardPage.jsx` | Bố cục 4 Stat Cards, Panel Yêu cầu sản xuất, Sidepanels "Việc tiếp theo" + "Cảnh báo vật tư", và Panel Chứng từ gần đây; tab tổng hợp preview ghi tại FE-MISS-011. |
| `frontend/src/features/production/ProductionPage.jsx` | Thiết kế lại trang Lệnh sản xuất với 4 thẻ Stat Filter, thanh tiến độ `<progress>`, bảng dữ liệu và modal chi tiết. |
| `frontend/src/features/production/RequestsPage.jsx` | Đồng bộ trang Yêu cầu sản xuất với intro note, lọc trạng thái API, bảng và modal chi tiết hiện có; tab tổng hợp ghi tại FE-MISS-011, BOM tổng hợp tại FE-MISS-010. |
| `frontend/src/features/production/CompletionsPage.jsx` | Cập nhật bảng chứng từ, modal tạo/sửa chứng từ hoàn thành theo API hiện tại, modal chi tiết; ghi nhận badQty/note tại FE-MISS-006. |
| `frontend/src/features/material-issuing/MaterialIssuingPage.jsx` | Bổ sung route alias `/nv/phieu-xuat` tra cứu phiếu xuất kho được giao cho nhân viên (chỉ đọc); quyền tạo phiếu ghi nhận tại FE-MISS-007. |
| `frontend/src/features/materials/MaterialsPage.jsx` | Đồng bộ trang Tra cứu tồn kho hiển thị số tồn thực tế và modal chi tiết chỉ đọc; cảnh báo min_stock ghi nhận tại FE-MISS-008. |

---

## 12. Checklist Nghiệm thu Giao diện đích (UI Acceptance Checklist)

Đánh dấu theo dõi quá trình hiện thực hóa code UI theo thiết kế mẫu:

- [ ] **UI-NV-01**: Áp dụng hệ màu Admin tại mục 10.1 trên toàn bộ UI nhân viên (nền `#14100d`, card `#211b17`, viền token `#362c25`, text `#f4ede6`, accent `#df6d27`), gồm sidebar, topbar, bảng, badge, form, trạng thái tương tác và toast; không làm thay đổi màu Admin/Quản lý. Kiểm chứng tương phản khi render, không xem việc sao chép token là đã đạt accessibility.
- [ ] **UI-NV-02**: Sidebar đủ đúng 6 mục, đúng thứ tự, có logo thương hiệu nghiêng và hình ảnh xe đạp hoàng hôn ở chân sidebar.
- [ ] **UI-NV-03**: Topbar có nút hamburger mobile, breadcrumb `Home > Tiêu đề trang`, module pill `Kho & sản xuất` và profile avatar kèm dropdown menu.
- [ ] **UI-NV-04**: Trang Tổng quan hiển thị đầy đủ 4 thẻ Stat Cards, grid 2 cột (Yêu cầu / Việc tiếp theo & Cảnh báo), và bảng Chứng từ gần đây.
- [ ] **UI-NV-05**: Trang Lệnh sản xuất có 4 thẻ lọc theo trạng thái API hiện có, thanh tiến độ trực quan trên từng dòng lệnh, và modal chi tiết lệnh; khác biệt preview về hạn hoàn thành/tìm kiếm/trạng thái ghi tại FE-MISS-009.
- [ ] **UI-NV-06**: Trang Yêu cầu sản xuất có intro note, bảng danh sách và modal chi tiết.
- [ ] **UI-NV-07**: Trang Chứng từ hoàn thành có form tạo/sửa theo API hiện tại, bảng chứng từ và modal chi tiết; badQty/note ghi nhận FE-MISS-006.
- [ ] **UI-NV-08**: Trang Tra cứu phiếu xuất hiển thị danh sách phiếu xuất liên quan (chỉ đọc) và chi tiết phiếu; quyền tạo phiếu ghi nhận FE-MISS-007.
- [ ] **UI-NV-09**: Trang Tra cứu tồn kho có lọc loại hàng, số tồn thực tế và modal chi tiết chỉ đọc; cảnh báo min_stock ghi nhận FE-MISS-008.
- [ ] **UI-NV-10**: Record dialog rộng `min(640px, calc(100vw - 32px))`, confirmation dùng biến thể Admin tối đa 492px; nền `#231b16`, viền `#5a493c`, chữ `#f4ede6`, backdrop `rgb(8 6 5 / 0.72)`; cuộn nội bộ khi màn hình thấp; cả modal xác nhận lẫn modal chi tiết/form đều nhận đúng theme nhân viên.
- [ ] **UI-NV-11**: Responsive chuẩn xác trên các kích thước 1440px, 1024px, 768px, và mobile 375px; drawer sidebar trượt mượt mà trên mobile.
- [ ] **UI-NV-12**: Kiểm thử tự động (Unit test, Lint, Build và Playwright browser suite) đạt chuẩn; không phá vỡ hồi quy của phân hệ Admin hay Quản lý kho.
- [ ] **UI-NV-13**: Báo cáo đầy đủ file sửa đổi, kết quả kiểm tra và chờ dev nghiệm thu (không tự commit hoặc push).

Bằng chứng tự động: 46 unit tests đạt trước thay đổi nhãn ngày dashboard; lint, build và 18/18 ca browser (`test-employee-redesign-current.log`: 11 nhân viên + 7 điều hướng ba vai trò) đạt ở bản hiện tại. Các mục checklist còn `[ ]` để dev đối chiếu UI với preview và nghiệm thu; browser fixture không thay cho thử nghiệm API/PostgreSQL thật hoặc kiểm tra tương phản/zoom đầy đủ.
