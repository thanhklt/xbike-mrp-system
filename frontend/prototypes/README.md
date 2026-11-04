# xBike — HTML prototype

Bốn màn hình HTML độc lập, theo `DESIGN.md` trong Downloads và `api_contract_v3.md` do dev cung cấp. Bản này sử dụng HTML/CSS/JavaScript thuần, không cần cài dependency. Font IBM Plex Sans được lưu tại `assets/fonts/`, kèm giấy phép OFL.

## Mở bản thiết kế

Từ thư mục gốc repository:

```powershell
python -m http.server 4173 --bind 127.0.0.1 --directory frontend/prototypes
```

- [Mặt hàng và tồn kho](http://127.0.0.1:4173/mathang/)
- [Lệnh sản xuất](http://127.0.0.1:4173/lenhsanxuat/)
- [Giao dịch kho](http://127.0.0.1:4173/giaodichkho/)
- [Điều chỉnh kho](http://127.0.0.1:4173/dieuchinhkho/)

Cũng có thể mở trực tiếp từng `index.html`. Để các màn hình dùng chung dữ liệu phiên, nên mở qua HTTP như trên; cơ chế lưu phiên của `file://` tùy thuộc trình duyệt.

## Phạm vi

- **Mặt hàng:** tìm kiếm, lọc, sắp xếp, phân trang, xem/thêm/sửa, ngừng hoạt động, kích hoạt lại. Số dư chỉ đọc. Mã và SKU duy nhất, giá nguyên VND, kiểm tra trường bắt buộc và danh mục snake_case. Mã/SKU/loại/đơn vị đã được tham chiếu bị khóa khi sửa.
- **Lệnh sản xuất:** xem lệnh, vật tư, đầu ra, cha/con; giao người, gửi, bắt đầu và hủy theo trạng thái và vai trò. Không tạo lệnh hoặc hoàn tất thủ công. Nhân viên minh họa là Trần Minh Tuấn (ID 21).
- **Giao dịch kho:** chỉ đọc, lọc theo mặt hàng/loại/người/ngày, truy vết nguồn và các điều chỉnh đã xác nhận. Ô tìm kiếm là tìm cục bộ trong dữ liệu mẫu, không mô tả thêm query API `q` cho endpoint này.
- **Điều chỉnh kho:** tạo/sửa/xóa nháp, chọn dòng nhập gốc, tính chênh lệch dự kiến, xác nhận toàn bộ; cập nhật ledger và tồn khi thành công. Âm tồn: giữ nguyên ledger, chuyển phiếu sang lỗi và tạo ticket minh họa. Phiếu lỗi bất biến, muốn thử lại phải tạo phiếu mới. Mã chứng từ đã xóa không được tái sử dụng trong phiên.
- **Trạng thái:** có dữ liệu, chưa có dữ liệu, tìm không thấy, đang tải, lỗi tải/503 danh mục, 403 theo vai trò và xung đột 412 khi gửi form. Bộ chọn nằm ở cuối màn hình và chỉ dùng để duyệt prototype.

Dữ liệu mẫu xBike gồm 14 mặt hàng, 9 lệnh, 3 phiếu điều chỉnh, một phiếu nhập nguồn đã hoàn thành và một ticket ban đầu. Giá và số lượng chỉ có mục đích minh họa. Tồn được tính từ ledger; tiến độ và lượng cấp vật tư có dữ liệu đối ứng. Các thao tác chỉ lưu trong `sessionStorage` với key `xbike-html-prototype-v1`; không gọi backend và không ghi vào database. Chọn **Về bản thiết kế → Khôi phục dữ liệu mẫu** để bắt đầu lại.

## Quyết định thiết kế

- Ưu tiên hệ `03 — Chuyên nghiệp` của DESIGN.md: navy, nền xám xanh, IBM Plex Sans, viền mảnh, góc bo 4–6 px, không shadow.
- Taste-skill áp dụng quy trình app screens: bảng và công việc làm trọng tâm, số liệu có đơn vị, số căn phải, dữ liệu cộng khớp, không KPI trang trí. Palette/font/bố cục shell trong tài liệu được giữ khi khác với mẫu style của skill.
- Impeccable áp dụng chế độ Operate: thứ bậc thông tin, xác nhận thao tác ghi sổ, thông báo phục hồi lỗi, focus và các trạng thái giao diện.
- UI-UX Pro Max hỗ trợ kiểm tra bàn phím, nhãn form, modal, tương phản và bảng trên viewport hẹp.
- Trên điện thoại, bảng nghiệp vụ cuộn bên trong khung và giữ cột định danh; trang không cuộn ngang. Sidebar mở qua nút menu và đóng bằng Escape. Các tab hỗ trợ phím mũi tên/Home/End; dialog sử dụng hành vi modal của trình duyệt.

## Đối chiếu API khi tích hợp thật

Đường dẫn giao diện không phải đường dẫn backend. API tương ứng là `/api/v1/mat_hang`, `/api/v1/lenh_san_xuat`, `/api/v1/giao_dich_kho`, `/api/v1/phieu_dieu_chinh_kho`. Backend chịu trách nhiệm xác thực, phân quyền, transaction, sinh mã, tính số dư/tiến độ và kiểm tra toàn bộ ràng buộc.

Theo schema `MatHangCreate` ở §5.1, form prototype có `ma_mat_hang` bắt buộc. Contract cũng có quy ước mã danh mục ở §2.5; khi nối API cần đối chiếu cơ chế sinh mã thực tế với backend. Các trường phiên bản/ETag, If-Match, envelope, idempotency và lỗi mạng chỉ được minh họa ở mức giao diện, chưa có tích hợp HTTP. Ngày mới dùng đồng hồ trình duyệt; dữ liệu nền mang ngày 02–04/11/2026.

Không bao gồm CRUD phiếu nhập, phiếu xuất, yêu cầu sản xuất, chứng từ hoàn thành hoặc quy trình nhận/đóng ticket. Khung chi tiết chỉ hiển thị nguồn và thông tin ticket có liên quan; không có liên kết giả tới các màn hình chưa dựng.
