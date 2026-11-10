# Quy tắc triển khai frontend

Áp dụng khi triển khai giao diện trong project xBike MRP, cùng với `AGENTS.md` ở gốc repository. Với giao diện admin, đọc [đặc tả giao diện admin](./dac-ta-giao-dien-admin.md) và các ảnh thiết kế được dev xác nhận trước khi sửa code.

## 1. Bắt buộc hỏi khi chưa hiểu hoặc chưa rõ

- Nếu chưa hiểu yêu cầu, chưa rõ thiết kế, luồng thao tác, dữ liệu, validation hoặc quyền truy cập, phải hỏi lại dev trước khi làm phần phụ thuộc vào thông tin đó.
- Nêu cụ thể điểm chưa rõ, màn hình/thành phần liên quan và thông tin cần xác nhận. Không tự đoán ý định hoặc tự đặt quy tắc nghiệp vụ.
- Nếu ảnh, đặc tả, code và API mâu thuẫn, trình bày khác biệt để dev chốt; không tự chọn một cách diễn giải để sửa phần liên quan.
- Trong lúc chờ trả lời, tiếp tục làm các phần độc lập đã rõ yêu cầu. Không xem việc chưa có phản hồi là đồng ý.

## 2. Làm đúng thiết kế, không tự ý thêm

- Bám sát bố cục, nội dung, button, icon, màu sắc, trường dữ liệu và trạng thái đã được duyệt trong thiết kế.
- Không tự thêm hoặc bớt button, menu, trường nhập, bộ lọc, biểu đồ, modal, thông báo hoặc tính năng khi chưa được dev yêu cầu/chấp thuận.
- Không thêm một thành phần vào UI chỉ vì API có hỗ trợ. Ngược lại, không tự xóa thành phần có trong thiết kế chỉ vì API chưa hỗ trợ.
- Không tự đổi luồng nghiệp vụ, cách phân quyền, validation hoặc dữ liệu để làm cho giao diện có vẻ hoạt động.
- Không tự chọn thông số hoặc hành vi chưa được thiết kế mô tả nếu lựa chọn đó làm thay đổi yêu cầu. Ghi rõ điểm thiếu và hỏi lại dev.
- Tái sử dụng component và cách tổ chức code hiện có khi đáp ứng được thiết kế; không tự mở rộng phạm vi sang refactor hoặc thêm dependency.

## 3. API chưa đáp ứng: ghi MISSING.md và tiếp tục phần đã rõ

Khi một thành phần trong thiết kế cần endpoint, trường dữ liệu, quyền hoặc hành vi mà API hiện tại chưa đáp ứng, phải ghi vào [MISSING.md](./MISSING.md) ngay khi phát hiện.

1. Đối chiếu hợp đồng API và source liên quan để nêu chính xác phần thiếu. Nếu chưa xác minh được thì ghi “Chưa xác minh”, không khẳng định API không có.
2. Ghi màn hình, mã yêu cầu trong đặc tả nếu có, thành phần/thao tác bị ảnh hưởng, nhu cầu từ thiết kế, khả năng API hiện tại, bằng chứng và câu hỏi cần dev chốt.
3. Tiếp tục triển khai bố cục và những phần độc lập đã rõ, dùng API hiện có cho đúng chức năng đã được hỗ trợ.
4. Giữ thành phần theo thiết kế. Không tự gắn API khác, tạo dữ liệu giả, giả lập thành công hoặc dùng thao tác khác để thay cho chức năng còn thiếu.
5. Nếu cách xử lý phần chưa hoạt động chưa được chốt, hỏi lại dev. Không tự thêm trạng thái disabled, tooltip, toast hoặc modal để xử lý khoảng trống; chỉ áp dụng khi thiết kế đã quy định hoặc dev đã đồng ý.
6. Không tự viết/sửa backend, thêm endpoint, đổi schema hoặc request/response để bù phần thiếu. Ghi phụ thuộc trong `MISSING.md` và chờ dev cho phép phạm vi tương ứng.

Ví dụ: thiết kế có button “Tạo vai trò” nhưng chưa có API tạo vai trò. Phải ghi thiếu API trong `MISSING.md`, giữ button trong phần trình bày theo thiết kế và hỏi cách xử lý tương tác chưa được hỗ trợ. Tiếp tục làm bảng, bố cục và các phần đã đủ dữ liệu; không tự thêm API, form hoặc thông báo ngoài thiết kế, không báo tạo thành công giả.

## 4. Theo dõi trạng thái và bàn giao

- Trong đặc tả và `MISSING.md`, dùng `- [ ]` cho việc chưa xong, còn thiếu hoặc đang chờ xác nhận; dùng `- [x]` cho phần đã hoàn tất, kèm bằng chứng phù hợp.
- Với mục thiếu API, chỉ đánh dấu hoàn tất khi phần thiếu đã được cung cấp, frontend đã tích hợp và kiểm tra, hoặc dev đã quyết định bỏ/đổi yêu cầu. Ghi rõ căn cứ đóng mục; không đánh dấu xong chỉ vì đã dựng hình thức button.
- Phân biệt “đã dựng giao diện”, “đã tích hợp API” và “đã kiểm thử”. Không báo toàn bộ tính năng hoàn thành nếu còn phụ thuộc chưa xử lý.
- Kiểm tra các phần đã thay đổi theo phạm vi phù hợp; báo rõ kiểm tra đã chạy, kết quả và phần chưa kiểm chứng.
- Khi bàn giao, liệt kê file sửa, phần đã làm, các mục còn thiếu trong `MISSING.md` và câu hỏi còn chờ dev trả lời.
- Không tự accept thay đổi, commit hoặc push nếu chưa có yêu cầu/cho phép rõ ràng cho thao tác và phạm vi đó.
