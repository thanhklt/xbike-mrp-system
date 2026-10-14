# Hướng dẫn làm việc trong project xBike MRP

Các hướng dẫn này áp dụng cho toàn bộ repository.

## 1. Không tự ý commit hoặc push

- Không chạy `git commit`, `git push` hoặc thao tác tương đương nếu dev chưa yêu cầu hoặc cho phép rõ ràng.
- Yêu cầu sửa code, sửa lỗi, tạo file hoặc hoàn thành một tác vụ không đồng nghĩa với cho phép commit hoặc push.
- Cho phép commit không đồng nghĩa với cho phép push. Chỉ thực hiện đúng thao tác và phạm vi dev đã cho phép.
- Khi hoàn thành, báo cáo các file đã sửa và kết quả kiểm tra; để dev quyết định việc commit hoặc push.

## 2. Hỏi lại khi chưa đủ thông tin

- Nếu yêu cầu mơ hồ và chưa có đủ thông tin để thực hiện chính xác, phải hỏi lại dev trước khi làm phần công việc phụ thuộc vào thông tin đó.
- Không tự dự đoán ý định của dev, tự đặt yêu cầu nghiệp vụ hoặc tự chọn cách diễn giải làm thay đổi phạm vi công việc.
- Câu hỏi cần nêu rõ điểm chưa xác định và thông tin cần dev cung cấp. Có thể đưa ra các lựa chọn để dev xác nhận.
- Có thể tiếp tục đọc code, kiểm tra tài liệu hoặc làm các phần độc lập đã rõ yêu cầu trong khi chờ phản hồi.
- Không xem việc dev chưa phản hồi là sự đồng ý với một giả định.

## 3. Đọc tài liệu đã thống nhất khi bắt đầu phiên mới

Nguồn tài liệu đã thống nhất của project:

[Thư mục Google Drive của project](https://drive.google.com/drive/folders/1AVkmFGSHI-zgRTCzaxAh9qyD1_FkFFd9)

- Mỗi khi bắt đầu một phiên mới mà chưa có ngữ cảnh về project, phải mở thư mục trên và đọc các tài liệu đã thống nhất để nắm yêu cầu, phạm vi, mô hình dữ liệu và các quyết định liên quan trước khi triển khai.
- Không suy đoán nội dung tài liệu từ tên file, cấu trúc code hoặc trí nhớ chưa được xác minh.
- Nếu không truy cập được thư mục hoặc tài liệu cần thiết, báo rõ cho dev và yêu cầu cấp quyền hoặc cung cấp nội dung. Không tự thay thế thông tin thiếu bằng giả định.
- Nếu tài liệu, code hiện tại và yêu cầu của dev có điểm mâu thuẫn hoặc chưa rõ, nêu cụ thể điểm đó và hỏi lại dev trước khi sửa phần liên quan.
- Khi báo cáo quyết định dựa trên tài liệu, nêu tài liệu đã đọc để dev có thể đối chiếu.

## 4. Giới hạn phạm vi thay đổi

- Chỉ sửa các phần liên quan trực tiếp đến yêu cầu đã thống nhất với dev.
- Nếu cần mở rộng phạm vi sang backend, frontend hoặc hạ tầng ngoài yêu cầu, giải thích lý do và hỏi dev trước khi thực hiện phần mở rộng.
- Không tự ý refactor, nâng cấp dependency hoặc bổ sung tính năng không liên quan.
- Giữ nguyên các thay đổi có sẵn của dev; không ghi đè hoặc hoàn tác chúng khi chưa được cho phép.

## 5. Bảo vệ dữ liệu

- Không tự ý xóa database, bảng, dữ liệu hoặc volume Docker; không chạy reset dữ liệu nếu dev chưa cho phép rõ ràng.
- Không tự ý nạp lại seed vào database có dữ liệu. Phải kiểm tra trạng thái database bằng thao tác chỉ đọc và hỏi dev trước khi thực hiện nếu database đã có dữ liệu.
- Trước thao tác có thể mất dữ liệu, xác định rõ môi trường và đối tượng bị tác động, giải thích ảnh hưởng để dev xác nhận.
- Khi cần kiểm tra thao tác ghi dữ liệu, ưu tiên database test riêng và cơ chế rollback; không dùng database ứng dụng làm nơi thử nghiệm.

## 6. Thống nhất schema và hợp đồng API

- Khi sửa ORM, đối chiếu tài liệu đã thống nhất và schema PostgreSQL, bao gồm tên bảng/cột, kiểu dữ liệu, nullable, giá trị mặc định, khóa và ràng buộc.
- Không tự chọn một nguồn làm chuẩn khi tài liệu, SQL và code mâu thuẫn; nêu điểm khác biệt và hỏi lại dev.
- Nếu thay đổi schema hoặc request/response của API, báo rõ thay đổi, ảnh hưởng tương thích và các thành phần cần cập nhật.
- Chuẩn bị migration khi cần thay đổi database đã tồn tại. Không coi việc sửa file bootstrap `init.sql` là đã cập nhật database đang chạy.

## 7. Kiểm chứng và bàn giao

- Chạy các kiểm tra phù hợp với thay đổi trước khi báo hoàn thành, chẳng hạn test, lint, kiểm tra kiểu dữ liệu hoặc đối chiếu schema.
- Chỉ khẳng định kiểm tra thành công khi đã chạy và đọc kết quả thực tế; không dùng suy đoán thay cho bằng chứng.
- Nếu không chạy được kiểm tra hoặc có kiểm tra thất bại, báo rõ kiểm tra nào, lý do và ảnh hưởng; không bỏ qua lỗi trong báo cáo.
- Khi bàn giao, liệt kê các file đã sửa, mục đích thay đổi, kết quả kiểm tra và phần chưa triển khai hoặc giới hạn còn lại.

## Hướng dẫn công cụ hiện có

@C:\Users\marcn\.codex\RTK.md
