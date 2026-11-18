# Prototype XBike MRP theo backend hiện tại

File dùng để review: [XBike_MRP_Prototype-backend-v4.html](./XBike_MRP_Prototype-backend-v4.html).

Đối chiếu ngày **16/11/2026**, source tại commit **`7196059`** và OpenAPI sinh trực tiếp từ `app.main.app`. Đây là bản cập nhật độc lập từ `XBike_MRP_Prototype-v2.html` do dev cung cấp, giữ nền tối, màu cam, icon và logo nhúng của bản gốc. Không sửa bản gốc trong Downloads, source frontend/backend, SQL hoặc database. Không commit/push.

## Cách mở và thử

1. Mở file HTML bằng Chrome hoặc Edge; không cần chạy backend/frontend, cài thư viện hoặc kết nối mạng. Có thể sao chép riêng file HTML sang máy khác.
2. Bấm avatar/họ tên ở góc trên bên phải → **Hồ sơ** → **Tài khoản mô phỏng** để thử QLK, hai nhân viên được giao khác nhau và QTV. Đây là công cụ mô phỏng để review, không phải đăng nhập thật.
3. Mở **Luồng vận hành và hướng dẫn thử** trên Tổng quan để xem hướng dẫn và các lối thử. Tải lại trang sẽ khôi phục dữ liệu mẫu. Đóng trang sẽ mất thay đổi; không ghi vào localStorage hoặc database.

| Kịch bản | Các bước thử |
| --- | --- |
| Xuất giao hoàn toàn từ tồn | QLK gửi `YCSX-000001` → Nam xem trước và xác nhận kiểm tra → lập/gửi PX thành phẩm từ chi tiết yêu cầu → QLK duyệt PX → yêu cầu hoàn thành. Không có bước sản xuất. |
| Nhập kho cần bổ sung linh kiện | QLK gửi `YCSX-000002` → Hà kiểm tra, thiếu 4 bánh xe → QLK hoàn tất `PN-000002` (10 bánh xe) → Hà kiểm tra lại → lập/gửi PX linh kiện → QLK duyệt → Hà bắt đầu và lập/gửi chứng từ hoàn thành 6 xe → QLK duyệt → yêu cầu hoàn thành. |
| Duyệt chứng từ có sẵn | QLK mở `PX-000002` hoặc `HTSX-000001`. Duyệt làm thay đổi tồn và sổ; bấm **Kiểm tra ghi nhận** không ghi lần hai. |
| Từ chối / gửi lại | QLK từ chối phiếu chờ duyệt, nhập lý do → chuyển sang đúng NV được giao → mở phiếu trong yêu cầu và gửi lại cùng chứng từ. Không tạo phiếu thay thế. |
| Hủy và giải phóng giữ hàng | QLK xem trước hủy `YCSX-000004`, nhập lý do. Giữ hàng được giải phóng, PX chờ duyệt bị từ chối, tồn thực tế không đổi. `YCSX-000003` đã có PX duyệt nên không hủy được. |
| Phiên bản BOM | Gửi một yêu cầu, sau đó tạo phiên bản BOM mới. Phiên bản mới hoạt động ngay; chi tiết yêu cầu đã gửi vẫn giữ BOM và nhu cầu cũ. |

## Các điểm đã chỉnh so với prototype v2

| Phần | Luồng theo backend được thể hiện |
| --- | --- |
| Vai trò | QLK điều phối và duyệt; NV thao tác yêu cầu được giao; QTV chỉ có các màn đọc được phép trong phạm vi prototype. NV không có danh sách PX/HTSX toàn kho; mở chứng từ từ yêu cầu được giao. QLK không thấy HTSX nháp. Không bổ sung màn quản trị tài khoản. |
| Mặt hàng | Chỉ `linh_kien` / `thanh_pham`; mã `MH-…` tự cấp, SKU riêng, tiền integer VND. Tách tồn thực tế / đang giữ / khả dụng. TP mới phải kèm BOM đầu tiên. Ngừng là đổi trạng thái, không xóa tồn. |
| BOM | Một cấp TP → LK đang hoạt động, không có BTP hoặc BOM nháp. Tạo phiên bản mới kích hoạt ngay; dừng/dùng lại đồng bộ trạng thái TP. Dùng lại TP chọn BOM được kích hoạt gần nhất, không mặc định lấy số phiên bản lớn nhất. |
| Yêu cầu | `xuat_giao` / **`nhap_kho`**; bắt buộc TP, số lượng, NV được giao và hạn hoàn thành ngay khi tạo. QLK sửa/xóa nháp, gửi để chốt BOM. Không có nút “Duyệt và giao” gộp với giữ hàng; không sinh lệnh sản xuất riêng. |
| Kiểm tra / giữ hàng | NV xem trước chỉ đọc; xác nhận mới chốt nhu cầu và giữ hàng. Xuất giao dùng TP khả dụng trước; nhập kho sản xuất toàn lượng yêu cầu. Thiếu LK thì không giữ một phần LK. Kiểm tra lại vẫn thiếu không đổi trạng thái hoặc thêm audit. |
| Bổ sung LK | Có thiếu theo từng yêu cầu và tổng hợp: `max(0, tổng nhu cầu − khả dụng)`. Lập PN từ màn tổng hợp chỉ là điền trước biểu mẫu, không tạo quan hệ FK mới. |
| Phiếu nhập | QLK chọn NCC, ngày nhập thực tế và LK; số lượng nguyên dương, đơn giá nguyên không âm. Nháp chưa cộng kho; hoàn tất mới cộng tồn/ghi sổ và khóa chứng từ. **Không tự kiểm tra lại yêu cầu đang chờ.** |
| Phiếu xuất | NV lập từ yêu cầu, hệ thống lấy đúng lượng đã chốt, giá/tổng chưa chốt trước duyệt. Không sửa/xóa chi tiết hoặc đưa về nháp. QLK duyệt mới trừ tồn, tiêu thụ giữ hàng, chốt giá hiện hành và ghi sổ. Từ chối cần lý do, NV gửi lại cùng phiếu. |
| Bắt đầu / hoàn thành | Chỉ NV được giao bắt đầu sau khi PX LK đã duyệt; bắt đầu không đổi kho và vẫn ở trạng thái đang thực hiện. HTSX lấy toàn bộ lượng cần sản xuất, không nhập hoàn thành từng phần. Duyệt HTSX mới cộng TP: nhập kho kết thúc; xuất giao giữ TP, tiếp tục lập/duyệt PX TP để kết thúc. |
| Hủy | QLK xem trước, xác nhận có lý do; chỉ trước khi có bất kỳ PX đã duyệt. Giải phóng giữ hàng, xóa PX nháp nội bộ, từ chối PX chờ duyệt; không tạo biến động kho. |
| Báo cáo / lịch sử | Nhập-xuất-tồn đọc sổ, biên tháng/quý/năm giờ VN, tồn đầu/cuối từ snapshot giao dịch cuối trước biên. Không có cột Điều chỉnh. Biến động mới nhất trước, lọc AND theo mặt hàng, **nghiệp vụ**, người ghi nhận và ngày. Audit chỉ đọc, có trước/sau, 4 kiểu sắp xếp. |

## Truy vết đối chiếu

Các đường dẫn dưới đây là API thật để đối chiếu nghiệp vụ; prototype **không gọi** các API này.

| Luồng | Endpoint hiện tại | Source đã đối chiếu |
| --- | --- | --- |
| Danh mục | `GET/POST /api/v1/mat_hang`, `GET/PATCH/DELETE /mat_hang/{id}`; dùng lại qua `PATCH` với `is_active=true` | `backend/app/modules/mat_hang/{router,schemas,service}.py` |
| BOM | `GET /api/v1/bom`, `GET/DELETE /bom/{id}`, `POST /bom/{id}/phien_ban`, `POST /bom/{id}/kich_hoat` | `backend/app/modules/bom/{router,schemas,service}.py` |
| Phiếu nhập | `GET/POST /api/v1/phieu_nhap`, `GET/PATCH/DELETE /phieu_nhap/{id}`, `POST /phieu_nhap/{id}/hoan_tat` | `backend/app/modules/phieu_nhap/{router,schemas,service}.py` |
| Yêu cầu / kiểm tra / hủy / bắt đầu | `GET/POST /api/v1/yeu_cau_san_xuat`, `GET/PATCH/DELETE /{id}`, `POST /{id}/gui`, `GET/POST /{id}/kiem_tra`, `GET/POST /{id}/huy`, `POST /{id}/bat_dau` | `backend/app/modules/san_xuat/router.py`, `schemas.py`, `service/yeu_cau_san_xuat.py` |
| Thiếu LK | `GET /api/v1/nhu_cau_bo_sung_linh_kien` | `tong_hop_nhu_cau_bo_sung()` trong service yêu cầu |
| Phiếu xuất | `GET/POST /api/v1/phieu_xuat`, `GET /{id}`, `POST /{id}/gui`, `POST /{id}/duyet`, `POST /{id}/tu_choi` | `backend/app/modules/phieu_xuat/{router,schemas,service}.py` |
| Hoàn thành SX | `POST/GET /api/v1/chung_tu_hoan_thanh_sx`, `GET /{id}`, `POST /{id}/gui`, `POST /{id}/duyet`, `POST /{id}/tu_choi`; `GET /yeu_cau_san_xuat/{id}/chung_tu_hoan_thanh` | `backend/app/modules/san_xuat/service/chung_tu_hoan_thanh_sx.py` và router/schema cùng module |
| Báo cáo / biến động | `GET /api/v1/bao_cao/nhap_xuat_ton`, `GET /api/v1/bao_cao/bien_dong_kho` | `backend/app/modules/reporting/{router,schemas,service,repository}.py` |
| Audit | `GET /api/v1/audit`, `GET /api/v1/audit/{id}` | `backend/app/modules/audit/{router,schemas,service}.py` |

Schema đối chiếu: `infra/postgres/init.sql`. Nguồn quyền, trạng thái và validation là source hiện tại, không suy ra từ các ảnh checklist/contract cũ trong hội thoại.

## Kiểm chứng và giới hạn

- `node --check` trên JavaScript trích từ file HTML: đạt.
- 13 nhóm kịch bản trên Chrome headless: đạt; gồm quyền/được giao, BOM chốt bất biến, xem trước chỉ đọc, giữ hàng, thiếu và nhập bổ sung, PX cố định, từ chối/gửi lại, bắt đầu, hai loại hoàn thành yêu cầu, hủy, nháp/validation, báo cáo và thao tác bàn phím/mobile.
- Bổ sung assertion cho tổng thiếu cộng gộp, kiểm tra lại khi vẫn thiếu, không ghi kho/audit hai lần, không làm mất dữ liệu nhập khi lỗi, không render HTML người dùng thành mã chạy. Test dùng bản sao HTML có probe **chỉ đọc** state trong thư mục làm việc bị Git bỏ qua; file bàn giao không có probe.
- Đã xem ảnh desktop 1440px và mobile 390px; không có lỗi JavaScript hoặc request HTTP(S) trong lượt test. Đây là kiểm tra prototype, **không phải kiểm thử tích hợp API/database thật**.
- Trong phiên mô phỏng, thay đổi nhiều đối tượng được áp dụng cùng nhau hoặc hoàn tác khi lỗi. Có kiểm tra phiên bản tài nguyên lúc xác nhận để thể hiện tránh ghi đè. Không mô phỏng JWT, header ETag thực, khóa PostgreSQL, hai người dùng thật chạy đồng thời hoặc lỗi mạng. Không thể dùng bản này để nghiệm thu các cơ chế đó.
- Dữ liệu mẫu không lấy từ seed hoặc tài khoản đăng nhập thật. Các chứng từ lịch sử chỉ để tạo số dư đầu kịch bản; không phải toàn bộ dữ liệu hệ thống. Phân trang mặc định 20, lựa chọn 20/50/100; chỉ minh họa các bộ lọc cần cho màn đang có, chưa phải client đủ mọi query parameter của backend.
- Bản demo dùng số nguyên an toàn của JavaScript; không dùng để kiểm tra biên BIGINT hoặc sản lượng rất lớn. Ngày/thời điểm mô phỏng cố định trong tháng 11/2026.
- Ticket/điều chỉnh: giữ cửa sổ lịch sử mẫu **chỉ đọc**. Backend còn route chuyển tiếp nhưng `init.sql` hiện không có bảng `TicketLoiDieuChinh` / `PhieuDieuChinhKho`; không giả lập các thao tác ghi thành công hoặc xem đây là luồng v4 đã tích hợp.
- Chỉ tạo hai file trong `docs/prototypes/`. Không sửa trực tiếp frontend, backend, database hoặc file prototype nguồn.

## Cập nhật nội dung giao diện theo phản hồi

- Tổng quan bỏ ô Phiên mô phỏng, bố trí lại ba ô còn lại.
- Mô tả dưới tiêu đề Tổng quan, Mặt hàng & tồn kho, Phiếu nhập, Nhu cầu bổ sung linh kiện, Yêu cầu sản xuất, Phiếu xuất và Chứng từ hoàn thành nêu chức năng của từng tab. Nhân viên có mô tả riêng cho việc được giao.
- Các dropdown loại, trạng thái, mặt hàng, nghiệp vụ và người thực hiện được yêu cầu dùng nhãn **Tất cả**; giá trị lọc vẫn giữ nguyên.
- BOM bỏ nút Xóa lọc, giữ ô tìm kiếm; nút tạo mới ghi đầy đủ **Tạo thành phẩm kèm định mức đầu tiên**.
- Sắp xếp audit hiển thị **Mới nhất / Cũ nhất / Tăng dần / Giảm dần**, lần lượt tương ứng thời điểm giảm/tăng và ID tăng/giảm.
- Kiểm chứng cập nhật: **45 mục đạt trên Chrome**, gồm bốn vai trò mô phỏng, nhãn/mô tả, hoạt động bộ lọc và tìm BOM, ánh xạ sắp xếp, các màn mobile 390px; không có lỗi JavaScript hoặc request mạng. JavaScript qua `node --check`; các hàm xử lý nghiệp vụ không đổi so với bản trước cập nhật chữ.
- Gói `XBike_MRP_Prototype-backend-v4.zip` chứa đúng file HTML mới nhất và tài liệu này. Giải nén rồi mở HTML bằng Chrome/Edge.

## Bố cục Tổng quan theo ảnh tham chiếu — 17/11/2026

- Tiêu đề và mô tả ở trái, lối mở các biểu mẫu có sẵn ở phải. Hai nút tạo của QLK dùng lại nguyên biểu mẫu nhập kho/yêu cầu sản xuất, không tự gửi hoặc ghi sổ.
- Giữ nguyên tên và cách tính ba chỉ số hiện tại, gom thành một dải thống kê có đường phân cách.
- Phía dưới là hai cột: tra cứu tồn thực tế từ dữ liệu mặt hàng đang có và hoạt động gần đây từ lịch sử mô phỏng. Tìm kiếm chỉ đọc, không cập nhật tồn, giữ hàng hoặc audit.
- QTV/QLK xem hoạt động; NV xem yêu cầu được giao ở cột phải, không được mở audit hoặc dùng các nút tạo của QLK.
- Hướng dẫn vận hành và các lối thử cũ được giữ trong mục mở rộng dưới hai cột; các màn khác và sidebar giữ nguyên.
- CSS bổ sung chỉ áp dụng trong `.xb-overview`. Toàn bộ token và bảng màu cũ giữ nguyên; không đưa màu sáng của ảnh tham chiếu vào prototype.
- Kiểm chứng: **20 mục kiểm tra bố cục/tương tác đạt**, gồm bốn vai trò, tra cứu tồn, lối mở biểu mẫu, quyền đọc lịch sử và bốn kích thước 1440/1024/768/390px. Chạy lại **13 nhóm kịch bản nghiệp vụ: đạt**. Không lỗi JavaScript hoặc request mạng; kiểm tra cú pháp JavaScript đạt. Đã xem ảnh desktop/mobile.
- Chỉ cập nhật prototype HTML, tài liệu này và ZIP bàn giao; không sửa source frontend/backend, cấu hình hoặc database.

## Thanh tài khoản — 17/11/2026

- Thông tin tài khoản nằm ở góc trên bên phải, giữ nguyên bốn lựa chọn tài khoản và cách đổi vai trò/phạm vi truy cập; bộ chọn được chuyển vào Hồ sơ trong lần cập nhật menu bên dưới.
- Bỏ hai nút Hướng dẫn và Đặt lại demo trên thanh trên cùng. Hướng dẫn theo ngữ cảnh vẫn nằm trong mục mở rộng ở Tổng quan; tải lại trang để khôi phục dữ liệu mẫu.
- Giữ nguyên màu sắc và các luồng nghiệp vụ. Chỉ thay bố cục thanh trên, bỏ thao tác reset không còn nút gọi và cập nhật tài liệu.
- **21 mục kiểm tra trên Chrome đạt**: vị trí tài khoản ở bốn kích thước 1440/1024/768/390px, bốn tài khoản/quyền, hai nút đã bỏ, cô lập header khi có hộp thoại, hướng dẫn theo ngữ cảnh; không lỗi JavaScript, tràn ngang hoặc request mạng. JavaScript qua `node --check`, đã xem ảnh desktop/mobile.

## Menu tài khoản mô phỏng theo ảnh tham chiếu — 17/11/2026

- Theo lựa chọn đã xác nhận: **chỉ mô phỏng giao diện, không bổ sung luồng đăng nhập/đăng xuất**.
- Thay dropdown trên thanh trên bằng avatar chữ cái, họ tên, vai trò, mũi tên và menu **Hồ sơ / Đăng xuất**. Giữ bảng màu tối hiện có, không thay tên/dữ liệu nhân viên theo ảnh tham chiếu.
- Hồ sơ hiển thị mã nhân viên, họ tên, vai trò và bộ chọn Tài khoản mô phỏng đã có. Không tạo/sửa hồ sơ thật hoặc gọi API.
- Đăng xuất chỉ mở thông báo về bản mô phỏng; không đổi tài khoản, xóa dữ liệu, tạo trang đăng nhập hoặc giả lập kết thúc phiên thành công.
- Hỗ trợ đóng khi nhấn ngoài/Escape, phím mũi tên/Home/End/Tab, trả focus khi đóng hộp thoại và menu không tràn màn hình điện thoại.
- **21 mục kiểm tra menu đạt trên Chrome** ở bốn kích thước và bốn tài khoản. Chạy lại **13 nhóm kiểm thử nghiệp vụ: đạt**; các kiểm thử dùng lối chọn vai trò mới trong Hồ sơ, giữ nguyên assertion nghiệp vụ. Không lỗi JavaScript hoặc request mạng. Đã kiểm tra file HTML bàn giao không có probe kiểm thử, cú pháp JavaScript và xem ảnh desktop/mobile.
- Chỉ cập nhật prototype HTML, tài liệu và ZIP; không sửa frontend/backend hoặc dữ liệu ứng dụng.

## Bố cục Mặt hàng & tồn kho theo ảnh tham chiếu — 17/11/2026

- Tiêu đề/mô tả và nút Thêm mặt hàng ở trên. Khung Danh sách chứa hàng bộ lọc, bảng và phân trang, giữ bảng màu tối của prototype.
- Hàng lọc có tìm kiếm, loại mặt hàng, trạng thái, sắp xếp, nút Lọc và lối Xóa lọc đã có. Giữ hành vi lọc trực tiếp; nút Lọc/Enter xác nhận kết quả và đưa về trang đầu. Các điều kiện kết hợp AND, không làm thay đổi dữ liệu.
- Bổ sung lọc Đang dùng/Đã ngừng và tám kiểu sắp xếp đọc tương ứng schema backend: ID, mã, tên, đơn giá tăng/giảm; không thay hợp đồng hoặc gọi API thật.
- Tách Mã và SKU thành hai cột; tên in đậm, loại nằm bên dưới; số lượng/đơn giá căn phải, trạng thái dùng badge. Vẫn giữ đủ Tồn thực tế, Đang giữ và Khả dụng; không thêm NVL/BTP từ ảnh vào mô hình v4.
- Giữ nguyên quyền và các biểu mẫu/thao tác Thêm, Sửa, Ngừng, Dùng lại. QTV/NV chỉ đọc. Tất cả cập nhật vẫn chỉ nằm trong phiên mô phỏng.
- CSS mới chỉ áp dụng trong `.xb-items`; bảng cuộn ngang bằng chuột/bàn phím trên màn nhỏ, không kéo tràn toàn trang.
- **29 mục kiểm tra trên Chrome đạt**: dữ liệu tồn/giữ/khả dụng, tám kiểu sắp xếp, lọc kết hợp/rỗng, Lọc/Enter/Xóa lọc, thao tác danh mục và quyền đọc, bốn kích thước 1440/1024/768/390px và cách ly CSS với trang khác. Chạy lại **13 nhóm kiểm thử nghiệp vụ: đạt**. Không lỗi JavaScript/request mạng; cú pháp JavaScript đạt, đã xem ảnh desktop/mobile và kiểm tra chính HTML bàn giao.
- Chỉ cập nhật HTML prototype, tài liệu và ZIP; không sửa source frontend/backend, schema hoặc database.

## Màu trạng thái và thao tác mặt hàng — 17/11/2026

- Ô Đang dùng có nền xanh lá; nút Sửa có nền xám; nút Ngừng có nền đỏ. Ô Đã ngừng cũng thể hiện màu đỏ, nút Dùng lại giữ kiểu trung tính.
- Chỉ áp dụng trong bảng Mặt hàng & tồn kho, không đổi màu badge/nút của các module khác hoặc thay đổi quyền/nghiệp vụ.
- Kiểm tra Chrome đạt: màu nền thực tế và hover, mở biểu mẫu Sửa, Ngừng/Dùng lại giữ nguyên số liệu tồn, mobile không tràn ngang và màu trạng thái module khác không đổi. JavaScript qua `node --check`; không lỗi trình duyệt. Đã xem ảnh desktop.

## Phiếu nhập kho theo ảnh tham chiếu đã sửa — 17/11/2026

- Dùng ảnh Phiếu nhập kho mới nhất thay cho ảnh Mặt hàng được gửi nhầm trước đó; giữ màu tối, header tài khoản và sidebar hiện có.
- Tiêu đề, mô tả “Phiếu nháp không cộng tồn. Chỉ hoàn tất nhập kho mới ghi sổ.” và nút Tạo phiếu nhập đặt ở trên. Khung Danh sách chứa bộ lọc tìm mã phiếu, trạng thái, Từ ngày và Đến ngày; bỏ các ô NCC/sắp xếp của bản đang làm dở chưa bàn giao.
- Khoảng ngày kết hợp AND với các điều kiện khác, lọc **ngày tạo phiếu theo giờ Việt Nam** như repository backend; cột Ngày nhập vẫn là ngày nhập thực tế, hiển thị ISO. Có ghi chú rõ trong giao diện và báo lỗi nếu từ ngày sau đến ngày. Không đổi backend để lọc theo ngày nhập.
- Bảng sáu cột: Mã phiếu, Nhà cung cấp, Ngày nhập, Tổng tiền, Trạng thái, Thao tác. Mã phiếu mở cùng chi tiết đã có; nháp dùng “Mở nháp →”, hoàn tất dùng “Xem →”. Nhãn Bản nháp chỉ đổi cách hiển thị, trạng thái dữ liệu vẫn là `nhap`.
- Phân trang hiển thị khoảng kết quả bên trái, Trang/trước/sau bên phải; giữ lựa chọn 20/50/100 dòng và vô hiệu hóa mũi tên ở biên. Giữ lối Xóa lọc và chuyển nút Ticket lịch sử xuống dưới danh sách để không làm mất chức năng mẫu chỉ đọc.
- Không thay lưu/sửa/xóa nháp, hoàn tất/ghi sổ, kiểm tra phiên bản, kiểm tra quyền, ghi audit hoặc tồn kho. Hoàn tất không tự kiểm tra lại yêu cầu; gọi lại không cộng kho/ghi sổ lần hai.
- **27 mục kiểm tra Chrome đạt**: bố cục/sáu cột, dữ liệu/tổng tiền, tìm kiếm/trạng thái/ngày kết hợp, khoảng sai/không có kết quả, ngày tạo khác ngày nhập, lưu nháp/sửa/xóa/hoàn tất/gọi lại, quyền QLK, Ticket chỉ đọc, bốn kích thước 1440/1024/768/390px và kiểm tra file HTML bàn giao. Chạy lại **13 nhóm kịch bản nghiệp vụ: đạt**, không lỗi JavaScript/request mạng. Cú pháp JavaScript đạt, đã xem ảnh desktop/mobile.
- Chỉ cập nhật HTML prototype, tài liệu và ZIP; giữ nguyên frontend/backend, schema, database và prototype nguồn trong Downloads.

## Lịch sử biến động kho theo ảnh tham chiếu — 17/11/2026

- Đặt tiêu đề/mô tả phía trên; khung Các lần biến động kho chứa năm bộ lọc Mặt hàng, Loại nghiệp vụ, Nhân viên, Từ ngày và Đến ngày, nút Lọc/Xóa lọc, bảng và phân trang. Giữ màu tối và các dropdown Tất cả đã thống nhất.
- Bảng bảy cột theo ảnh: Thời điểm, Mặt hàng, Loại nghiệp vụ, Số lượng thay đổi, Tồn sau, Chứng từ gốc, Nhân viên. Mặt hàng/nhân viên thể hiện mã kèm tên; chứng từ gốc thêm nhãn Phiếu nhập/Phiếu xuất/Chứng từ hoàn thành SX ở dòng dưới.
- Giữ nguyên dữ liệu sổ, số lượng có dấu +/−, số dư sau giao dịch, màu tăng/giảm và cách sắp xếp thời điểm giảm dần rồi ID giảm dần. Không suy ra tồn sau từ tồn hiện tại hoặc tự tạo giao dịch để lấp bảng.
- Giữ bốn loại nghiệp vụ v4. Lọc AND theo mặt hàng, nghiệp vụ, người ghi nhận và ngày ghi sổ theo giờ Việt Nam; báo lỗi khoảng ngày đảo ngược mà không làm mất giá trị đã nhập. Lọc/Enter chỉ đọc và về trang đầu; phân trang vẫn có 20/50/100 dòng.
- Chỉ QLK truy cập theo quyền đã có, không có thao tác sửa/xóa/xuất hoặc gọi API ghi dữ liệu. Các chứng từ lịch sử giữ dạng thông tin, không tạo link chi tiết giả khi bản mẫu không có chứng từ tương ứng.
- CSS chỉ áp dụng trong `.xb-movements`; màn nhỏ cuộn ngang bên trong bảng, có vùng cuộn nhận focus bàn phím. Các trang và menu tài khoản còn lại giữ nguyên.
- **29 mục kiểm tra Chrome đạt**: bố cục, bảy cột, dấu số lượng/số dư/metadata chính xác, thứ tự giao dịch trùng thời điểm, bốn nghiệp vụ, lọc AND/ngày/rỗng/sai, trạng thái dữ liệu không đổi khi đọc, đọc giao dịch vừa ghi sổ, quyền QLK, bốn kích thước 1440/1024/768/390px, cách ly CSS và HTML bàn giao không có probe. Chạy lại **13 nhóm kịch bản nghiệp vụ: đạt**, không lỗi JavaScript/request mạng. Cú pháp JavaScript đạt; đã xem ảnh desktop/mobile. Đây là kiểm tra prototype, không phải kiểm thử tích hợp API thật.
- Chỉ cập nhật HTML prototype, tài liệu và ZIP; không sửa source frontend/backend, schema hoặc database.

## Lịch sử thao tác, báo cáo, phiếu xuất và BOM — 17/11/2026

- **Lịch sử thao tác:** khung Danh sách gồm loại đối tượng, ID đối tượng, người thực hiện, thao tác, khoảng ngày và bốn kiểu sắp xếp Mới nhất/Cũ nhất/Tăng dần/Giảm dần. Giữ ô tìm mã đối tượng đã có ở đầu khung. Bảng sáu cột hiển thị thời gian, người thực hiện, đối tượng, thao tác, lý do và liên kết Mở. Cửa sổ dữ liệu trước/sau giữ nguyên, chỉ QTV/QLK đọc; không thêm sửa/xóa/xuất.
- Đối tượng audit được chiếu chỉ đọc từ mã đối tượng và snapshot có sẵn trong dữ liệu mô phỏng; không đổi cấu trúc hoặc hàm ghi audit. Đây không phải thay đổi metadata audit của backend. ID lọc là số nguyên dương trong dải INTEGER; báo lỗi mà giữ nguyên giá trị nhập. Không chèn bản ghi đăng nhập giả để làm giống dữ liệu trong ảnh.
- **Báo cáo nhập–xuất–tồn:** tách khung Kỳ thống kê và bảng kết quả theo tháng/quý/năm. Bộ lọc có năm, tháng hoặc quý khi cần, loại và mặt hàng. Bảng tám cột gồm mã, tên, loại, đơn vị tính và bốn số liệu tồn đầu/nhập/xuất/tồn cuối. Giữ nguyên tính toán từ snapshot sổ kho và biên kỳ giờ Việt Nam; không thêm cột Điều chỉnh hoặc lấy số dư hiện tại thay số dư lịch sử. Chỉ QLK xem.
- **Phiếu xuất kho:** khung Danh sách có tìm mã, trạng thái, loại phiếu, từ/đến ngày; bảng sáu cột Mã phiếu/Loại/Tham chiếu/Tạo lúc/Trạng thái/Thao tác. Giữ liên kết đến chi tiết cũ, nguồn yêu cầu, người lập và các thao tác đang có. Khoảng ngày lọc thời điểm tạo theo giờ Việt Nam. Không thêm nút tạo cho QLK: NV được giao vẫn lập phiếu từ yêu cầu, đúng luồng backend hiện tại.
- **BOM:** khung Danh sách có Mặt hàng/Hiệu lực; giữ ô tìm kiếm ở đầu khung và không thêm lại nút Xóa lọc. Bảng năm cột Sản phẩm/Phiên bản/Thành phần/Hiệu lực/Thao tác; Thành phần là số dòng định mức. Giữ nút ghi đầy đủ Tạo thành phẩm kèm định mức đầu tiên và các luồng phiên bản/ngừng/dùng lại đã có. BOM vẫn một cấp, không đổi thành nhiều cấp theo chữ trong ảnh. QLK ghi, NV chỉ đọc.
- Bốn màn dùng CSS giới hạn trong `.xb-reference`, giữ nguyên các token màu tối và menu tài khoản. Phân trang thể hiện khoảng kết quả, Trang/trước/sau và 20/50/100 dòng. Màn nhỏ xếp bộ lọc theo chiều dọc, cuộn ngang riêng trong bảng. Nút Lọc/Enter xác nhận kết quả và về trang đầu; điều kiện lọc kết hợp AND, lỗi đưa focus tới thông báo.
- **48 mục kiểm tra Chrome đạt:** bố cục, lọc kết hợp/ID/ngày, bốn kiểu sắp xếp audit và JSON trước/sau, số liệu tháng/quý/năm từ sổ, quyền ba vai trò, bất biến snapshot đã chốt, mở các biểu mẫu/chi tiết đang có, 16 lượt hiển thị ở 1440/1024/768/390px, cách ly các màn khác và kiểm tra chính HTML bàn giao. Đã xem ảnh desktop/mobile của cả bốn màn. Chạy lại **13 nhóm kịch bản nghiệp vụ: đạt**; không lỗi trình duyệt hoặc request HTTP(S). JavaScript qua `node --check`.
- Chỉ thay đổi HTML prototype, tài liệu này và ZIP chứa hai file đó. Các hàm xử lý nghiệp vụ và lưu biểu mẫu giữ nguyên so với bản trước lượt chỉnh bố cục; không sửa trực tiếp frontend, backend, SQL, database hoặc bản gốc trong Downloads. Kiểm tra trên chỉ nghiệm thu prototype ngoại tuyến, chưa phải kiểm thử tích hợp API thật.

## Đơn vị tính có dấu trong báo cáo — 17/11/2026

- Cột ĐVT của Nhập–xuất–tồn hiển thị `cai` → **cái**, `chiec` → **chiếc**, `bo` → **bộ**; `kg` giữ nguyên. Chỉ đổi nhãn hiển thị, không đổi mã đơn vị lưu trong dữ liệu hoặc cách tính báo cáo.
- Kiểm tra Chrome đạt với cả bốn đơn vị, kỳ tháng/quý/năm, đối chiếu các ô số liệu trước/sau và mã đơn vị trong biểu mẫu mặt hàng; không lỗi JavaScript hoặc request mạng. Đã xem ảnh bảng kết quả và cập nhật ZIP.

## Bỏ lời giới thiệu ở đầu trang — 17/11/2026

- Xóa hai dòng “PROTOTYPE · BACKEND V4” và “Ngoại tuyến · Dữ liệu mô phỏng trong phiên · Không gửi API” khỏi đầu trang. Giữ tài khoản ở góc phải trên cùng; không đổi màu sắc hoặc luồng thao tác.
- Kiểm tra Chrome đạt với cả bốn tài khoản mô phỏng trên desktop/mobile: không còn hai dòng chữ, menu tài khoản/Hồ sơ/phím Escape hoạt động, không tràn ngang hoặc lỗi trình duyệt. Bản HTML vẫn ngoại tuyến như hướng dẫn này; chỉ cập nhật prototype và ZIP.
