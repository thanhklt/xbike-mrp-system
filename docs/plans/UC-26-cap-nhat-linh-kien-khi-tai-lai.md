# UC-26 — Hiển thị tình trạng linh kiện khi tải lại chi tiết YCSX

**Trạng thái dự thảo · Chờ dev duyệt · 18/11/2026**

## Quyết định cần duyệt

Khi nhân viên được giao mở hoặc nhấn F5 trên trang chi tiết yêu cầu sản xuất (YCSX), trang tự hiển thị tình trạng linh kiện theo tồn khả dụng ở thời điểm tải. Nhân viên chỉ cần bấm **Kiểm tra** hoặc **Kiểm tra lại** khi muốn thực hiện bước xác nhận nghiệp vụ. Ví dụ, sau khi kho nhập đủ linh kiện, trang có thể đồng thời hiển thị trạng thái YCSX **Chờ bổ sung linh kiện** và thông báo **Đã đủ linh kiện, chờ xác nhận**.

Đề xuất này điều chỉnh phần hiển thị bảng thiếu trong quyết định D5 đã duyệt ngày 16/11/2026. D5 hiện quy định bảng xuất hiện trong hộp xác nhận và ngay sau khi xác nhận. Phạm vi của đề xuất là trang chi tiết YCSX phía nhân viên. [Kế hoạch UC-26 đã duyệt](UC-26.md)

## Căn cứ từ source code

- Trang chi tiết đọc YCSX bằng `useDetail`. Bảng thiếu lấy từ `checkResult`, một biến React chỉ được gán sau khi xác nhận thành công. F5 khởi tạo lại biến này. [RequestsPage.jsx](../../frontend/src/features/production/RequestsPage.jsx)
- Backend đã có `GET /api/v1/yeu_cau_san_xuat/{id}/kiem_tra` để tính nhu cầu và số thiếu theo tồn khả dụng. Khi kiểm tra lại, backend so sánh với nhu cầu đã chốt của YCSX. `POST` trên cùng đường dẫn tính lại dưới khóa và thực hiện giữ hàng, chuyển trạng thái khi đủ điều kiện. [Service YCSX](../../backend/app/modules/san_xuat/service/yeu_cau_san_xuat.py)

## Các bước triển khai sau khi duyệt

1. **Tải kết quả xem trước theo YCSX.** Trên trang chi tiết, sau khi có bản ghi, dùng `canCheckRequest(record, manager, userId)` để bật truy vấn GET. Điều kiện là nhân viên được giao và trạng thái **Đã gửi** hoặc **Chờ bổ sung linh kiện**. Dùng khóa truy vấn theo người dùng và đường dẫn chứa ID để kết quả về muộn của yêu cầu trước không hiện trên yêu cầu đang xem. Khi mở lại cùng YCSX, lấy kết quả mới kể cả khi bộ nhớ đệm còn dữ liệu. [Điều kiện hiện có](../../frontend/src/features/production/requestForm.js) · [Hook truy vấn](../../frontend/src/lib/api/useResources.js)
2. **Hiển thị kết quả ngay trên chi tiết.** Dùng dữ liệu GET thay cho `checkResult`. Nếu thiếu, dùng bảng hiện có và chỉ hiện dòng có `so_luong_thieu > 0`. Nếu đủ, hiện **Đã đủ linh kiện, chờ xác nhận**. Với yêu cầu xuất giao có `so_luong_can_san_xuat = 0`, hiện **Đã đủ thành phẩm, không cần sản xuất**. Khi đang tải hoặc GET thất bại, hiển thị tình trạng tương ứng tại phần linh kiện. Nhãn trạng thái YCSX lấy từ bản ghi chi tiết.
3. **Xác nhận theo số liệu mới nhất.** Khi bấm nút kiểm tra, lấy lại bản xem trước để mở hộp xác nhận. Chỉ thao tác xác nhận mới gửi POST kèm `If-Match`. Sau khi thành công, tải lại chi tiết. Nếu YCSX vẫn chờ bổ sung thì cập nhật bảng thiếu. Nếu đã chuyển sang **Đang thực hiện** thì ẩn phần xem trước. Dùng kết quả POST để báo kết quả thực tế khi tồn thay đổi giữa lúc xem và xác nhận.
4. **Cập nhật test UC-26.** Thay các kiểm tra phụ thuộc vào cách lưu `checkResult` bằng kiểm tra hành vi trong bảng nghiệm thu. Chạy bộ test UC-26 frontend, build frontend và kiểm tra F5 trên trình duyệt với dữ liệu test riêng. [Test UC-26](../../frontend/tests/uc26-check-request.test.js)

## Tiêu chí nghiệm thu

| Tình huống | Kết quả cần quan sát |
|---|---|
| YCSX đang thiếu 5 linh kiện. Kho nhập thêm 2 linh kiện khả dụng, nhân viên nhấn F5. | Bảng hiện thiếu 3. Trong Network có GET xem trước cho đúng ID. Số lượng giữ và trạng thái YCSX giữ nguyên sau F5. |
| Kho nhập đủ phần còn thiếu, nhân viên mở lại chi tiết hoặc nhấn F5. | Trang báo đủ linh kiện, chờ xác nhận. Bảng thiếu cũ biến mất. Trạng thái YCSX vẫn là Chờ bổ sung linh kiện. |
| YCSX xuất giao ở trạng thái Đã gửi, tồn thành phẩm đủ đáp ứng toàn bộ yêu cầu. | Trang báo đủ thành phẩm và số cần sản xuất bằng 0. |
| Nhân viên mở hộp kiểm tra rồi đóng. Sau đó mở lại và xác nhận khi đủ linh kiện. | F5 và đóng hộp đều chỉ đọc dữ liệu. Lần xác nhận gửi một POST kèm ETag đã xem. Khi backend xác nhận đủ, trang hiển thị Đang thực hiện. |
| Chuyển nhanh từ YCSX A sang B hoặc GET xem trước thất bại. | Trang B chỉ hiện dữ liệu của B. Khi lỗi, chi tiết YCSX vẫn đọc được và phần linh kiện báo lỗi thay vì hiển thị kết luận đủ hoặc thiếu. |
| Quản lý mở chi tiết, nhân viên không được giao mở đường dẫn, hoặc YCSX đã ra khỏi hai trạng thái cho phép. | Giao diện chỉ bật truy vấn xem trước khi thỏa điều kiện quyền và trạng thái của UC-26. |

**Phạm vi file dự kiến** gồm trang chi tiết và test UC-26 frontend. Việc triển khai dùng API hiện có. Luồng duyệt chứng từ hoàn thành sản xuất thuộc ý 2 và nằm ngoài kế hoạch này.
