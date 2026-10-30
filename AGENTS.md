# Hướng dẫn làm việc trong project xBike MRP

Các hướng dẫn này áp dụng cho toàn bộ repository.
Không áp dụng skill superpowers
Không tự ý accept các sự thay đổi

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
- Chuẩn bị migration khi cần thay đổi database đã tồn tại. Riêng kế hoạch demo Docker hiện tại, dev đã chốt chưa cần migration: chỉ bootstrap database mới/trống bằng `init.sql` và `seed.sql`, không tạo hoặc chạy migration, không tự thay đổi database đã có dữ liệu. Không coi việc sửa file bootstrap `init.sql` là đã cập nhật database đang chạy.

## 7. Kiểm chứng và bàn giao

- Chạy các kiểm tra phù hợp với thay đổi trước khi báo hoàn thành, chẳng hạn test, lint, kiểm tra kiểu dữ liệu hoặc đối chiếu schema.
- Chỉ khẳng định kiểm tra thành công khi đã chạy và đọc kết quả thực tế; không dùng suy đoán thay cho bằng chứng.
- Nếu không chạy được kiểm tra hoặc có kiểm tra thất bại, báo rõ kiểm tra nào, lý do và ảnh hưởng; không bỏ qua lỗi trong báo cáo.
- Khi bàn giao, liệt kê các file đã sửa, mục đích thay đổi, kết quả kiểm tra và phần chưa triển khai hoặc giới hạn còn lại.

## 8. Tài liệu sequence cho các module

- Mỗi module backend có endpoint phải có một file Markdown tương ứng tại `docs/sequence/<ten_module>.md`; tên file khớp tên thư mục trong `backend/app/modules/` (ví dụ `users.md`).
- Trong file của module, mỗi endpoint có một mục riêng ghi rõ HTTP method, đường dẫn đầy đủ và lược đồ trong code block `mermaid` dùng `sequenceDiagram`.
- Khi thêm, sửa hoặc xóa endpoint, cập nhật tài liệu sequence của module trong cùng tác vụ để phản ánh đúng code hiện tại. Không mô tả endpoint chưa triển khai như chức năng đang có.
- Lược đồ phải thể hiện luồng thành công, xác thực/phân quyền, kiểm tra đầu vào, các lời gọi xử lý và truy cập dữ liệu liên quan, cùng các nhánh lỗi nghiệp vụ chính và mã HTTP. Chỉ thể hiện các tầng thực sự tồn tại trong code.
- Ghi chú các khác biệt về dữ liệu trả về theo vai trò, phân trang, header hoặc transaction khi có liên quan. Đối chiếu router, service, schema, model và dependency dùng chung trước khi bàn giao.
- Khi kiểm chứng, kiểm tra cú pháp Mermaid nếu có công cụ sẵn có và đối chiếu sơ đồ với code; nếu chưa render/kiểm tra được bằng Mermaid thì báo rõ giới hạn đó.

## 9. Quy ước tên bảng và ORM đã thống nhất ngày 30/10/2026

- Tên bảng khi tạo mới hoặc đổi tên theo quy ước này dùng PascalCase; tên lớp ORM phải trùng chính xác tên bảng để dễ đối chiếu và audit.
- Phạm vi đã chốt cho kế hoạch refactor auth hiện tại: đổi `nhan_vien` thành `"NhanVien"`, ORM `User` thành `NhanVien`; đổi `vai_tro` thành `"VaiTro"`, ORM `Role` thành `VaiTro`; đổi `lich_su_thao_tac` thành `"LichSuThaoTac"`, ORM `AuditTrailLog` thành `LichSuThaoTac`.
- Đổi module `backend/app/modules/users/` thành `backend/app/modules/nhan_vien/`; module này sở hữu ORM `NhanVien` và `VaiTro`. Auth giao tiếp qua service công khai của module nhân viên.
- Module `backend/app/modules/audit/` giữ nguyên tên và sở hữu ORM `LichSuThaoTac`. Ghi audit trong luồng đổi mật khẩu qua service audit và dùng chung transaction với cập nhật mật khẩu.
- Tên cột, mã vai trò, giá trị nghiệp vụ và đường dẫn API giữ nguyên snake_case. Chẳng hạn `/api/v1/nhan_vien`, `nhan_vien_id`, `vai_tro_id` và mã vai trò `nhan_vien` không đổi theo tên bảng.
- PostgreSQL phân biệt hoa/thường với tên có dấu nháy kép: SQL viết trực tiếp phải dùng `"NhanVien"`, `"VaiTro"` và `"LichSuThaoTac"`. Cập nhật đồng bộ tham chiếu FK, seed, truy vấn, index, trigger bảo vệ audit và kiểm thử liên quan khi triển khai.
- Các bảng còn lại chưa thuộc phạm vi đổi tên của tác vụ này; không tự mở rộng sang toàn bộ schema.
- Đây là quyết định cho kế hoạch triển khai, không phải xác nhận database đã được đổi tên. Phạm vi hiện tại chỉ demo Docker trên database mới/trống, chưa có migration. Volume PostgreSQL đã khởi tạo không tự cập nhật schema khi sửa `init.sql` hoặc restart/rebuild container; không tự xóa volume, chạy `make clear`/`docker compose down -v` hoặc seed lại dữ liệu để áp dụng schema mới.

## Hướng dẫn công cụ hiện có

@C:\Users\marcn\.codex\RTK.md
