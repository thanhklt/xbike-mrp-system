# Kế hoạch và prompt AGY: chỉnh sửa tài khoản trực tiếp

## Phạm vi đã yêu cầu

- [x] Thay giao diện sửa hồ sơ cũ bằng chỉnh sửa ngay trên bố cục chi tiết tài khoản.
- [x] Giữ nút Lưu và Hủy; dựng popup “Lưu thành công” sau khi API lưu thành công.
- [x] Rút gọn popup đăng xuất: “Bạn có muốn kết thúc phiên làm việc?”, nút Hủy / Xác nhận và X đóng.
- [x] Vô hiệu hóa nút Sửa của ba vai trò hệ thống: `quan_tri_vien`, `quan_ly`, `nhan_vien`.
- [x] Codex đã đối chiếu yêu cầu, ảnh và diff; hai lần gửi prompt sửa cho AGY, rồi kiểm chứng độc lập các lỗi ETag/cache/lưu một phần và kết luận đạt phạm vi frontend ngày 08/11/2026. Giới hạn và file sửa ghi trong `doc/admin-ui-inline-edit-review.md`.

Yêu cầu mới là triển khai frontend thật theo ba ảnh mẫu đã tạo; không phải chỉ tạo thêm ảnh. Chưa được phép commit hoặc push.

## Ảnh tham chiếu

Ba ảnh mẫu cần triển khai:

1. `C:\Users\binhb\Downloads\xbike-admin-mockups-20261108-114000\01-chinh-sua-truc-tiep.png`
2. `C:\Users\binhb\Downloads\xbike-admin-mockups-20261108-114000\02-luu-thanh-cong.png`
3. `C:\Users\binhb\Downloads\xbike-admin-mockups-20261108-114000\03-xac-nhan-dang-xuat.png`

Hai ảnh dev bổ sung:

- Form sửa cũ cần thay thế: `C:\Users\binhb\AppData\Local\Temp\orca-paste-1794116651298-099ae3da-f0e7-4185-8856-e9bfa8aeda33.png`.
- Bảng vai trò: `C:\Users\binhb\AppData\Local\Temp\orca-paste-1794116742402-f17e173c-cb54-4960-8d7b-516eb07f9d6a.png`.

Ảnh chỉ quyết định cách trình bày; không được hardcode dữ liệu minh họa vào sản phẩm.

## Hai quyết định dev đã chốt

- [x] Nút Lưu lưu cả hồ sơ và vai trò qua các API hiện có. Nếu một phần thành công và phần còn lại lỗi, phải báo rõ phần đã lưu; không giả lập rollback hoặc thông báo toàn bộ thành công.
- [x] Giữ popup xác nhận trước khi gọi API lưu. Chỉ sau khi mọi phần cần lưu thành công mới hiện popup “Lưu thành công”.

Dev xác nhận hai lựa chọn trên trong cuộc trò chuyện ngày 08/11/2026. Flash tiếp tục đọc file và báo phương án; sau đó Argon triển khai theo đúng hai quyết định này. Các phần không thay đổi không cần gửi request ghi dư thừa.

## Model, skill và quy tắc

1. Dùng **Gemini 3.8 Flash** để khám phá file, luồng gọi và hợp đồng API, không sửa code trong bước này.
2. Argon đã triển khai vòng đầu nhưng dừng do quota. Theo yêu cầu tiếp theo của dev, dùng **Gemini 3.8 Flash (High)** trong chính chat AGY hiện có để hoàn tất, giữ ngữ cảnh và toàn bộ thay đổi đang có.
3. Áp dụng **Ponytail full**, **Impeccable**, **design-taste-frontend (Taste)** và **ui-ux-pro-max**. Đọc đúng SKILL.md có trên máy; user rules và ảnh đã chốt ưu tiên hơn đề xuất của skill.
4. Đọc `AGENTS.md`, `doc/FRONTEND_RULES.md`, `doc/dac-ta-giao-dien-admin.md`, `doc/MISSING.md` và kế hoạch admin trước đó. Các quyết định mới trong tác vụ này cập nhật phần tương ứng của kế hoạch cũ sau khi được chốt.
5. Giữ diff nhỏ nhất giải quyết đủ yêu cầu; tái sử dụng cấu trúc, component, hook và API hiện có. Không thêm dependency hoặc refactor ngoài phạm vi.
6. Thiếu API phải ghi `doc/MISSING.md`, tiếp tục phần độc lập đã rõ. Không tạo API thay thế, dữ liệu giả, thành công giả hoặc tự mở rộng backend/schema.
7. Không dùng database ứng dụng để thử ghi. Browser tests dùng fixture riêng; không import fixture vào UI chạy thật. Không seed/reset/xóa database hoặc volume.

## Prompt triển khai cho Argon

Bạn là AGY thực thi frontend; Codex review. Tiếp tục trong project và chat được điều phối, không tự commit/push.

### A. Sửa ngay trong trang chi tiết

- Giữ trang chi tiết và bố cục hai khối: danh tính bên trái, thông tin từng hàng bên phải. Giữ sidebar, artwork, breadcrumb, avatar chữ cái và theme hiện tại.
- Bấm Chỉnh sửa ở chi tiết hoặc Sửa từ danh sách phải mở cùng chế độ chỉnh sửa trực tiếp này. URL cũ có `?mode=edit` không được dẫn tới form cũ nữa.
- Loại bỏ nhánh trình bày sửa cũ dạng form hai cột cùng các khối Phân quyền / Trạng thái tài khoản lặp riêng. Đây không phải yêu cầu xóa trang xem chi tiết hoặc form Tạo tài khoản.
- Giữ thứ tự mười hàng: Họ tên, Ngày sinh, Số điện thoại, Email, Tên đăng nhập, Mật khẩu, Vai trò, Ngày vào làm, Hệ số lương, Trạng thái.
- Sáu trường hồ sơ có thể sửa trong ô giá trị bên phải: `ho_ten`, `ngay_sinh`, `so_dien_thoai`, `email`, `ngay_vao_lam`, `he_so_luong`. Giữ label, icon, validation, nullable, định dạng và giới hạn hợp đồng hiện có.
- Vai trò nằm trong đúng hàng hiện có; cách lưu tuân theo quyết định dev ở trên. Không gộp `vai_tro_id` vào PATCH hồ sơ khi hợp đồng không hỗ trợ.
- Tên đăng nhập, mật khẩu che cố định và trạng thái giữ cách hiển thị/chặn sửa đã thống nhất. Không lấy mật khẩu thật hoặc tự thêm chức năng đổi tên đăng nhập/reset mật khẩu.
- Nút Hủy và Lưu nằm ở khu vực hành động như ảnh. Hủy không gửi request và bỏ bản nháp, quay về xem chi tiết; Lưu có trạng thái đang xử lý và chặn gửi lặp.
- Giữ phân quyền, chặn khóa chính mình/quản trị viên và chặn hạ quyền quản trị viên. Nút khóa/mở khóa hiện có vẫn dùng snapshot/ETag đã xem cùng yêu cầu lý do; không tạo hành vi ghi ẩn.

### B. Lưu và popup thành công

- Bấm Lưu mở popup xác nhận trước khi gọi API. Hủy/X không ghi dữ liệu và giữ bản nháp; Xác nhận mới bắt đầu lưu các thay đổi hồ sơ/vai trò đã được người dùng kiểm tra.
- Chỉ hiển thị popup sau khi mọi thao tác mà người dùng yêu cầu lưu đã thành công thật. Popup có dấu check, chữ “Lưu thành công” và một nút “Đóng”, đúng ảnh mẫu.
- Đóng popup không gọi API ghi lần nữa; trả focus hợp lý về trang chi tiết với dữ liệu đã lưu.
- Dùng ETag/If-Match của snapshot đã tải. Lỗi 412/428 không tự lấy ETag mới rồi gửi lại để vượt kiểm tra đồng thời. Không retry ghi tự động.
- Khi hồ sơ và vai trò cùng thay đổi, lưu qua hai API riêng; phải phân biệt ETag trả về sau lần ghi thành công với việc tải lại để vượt lỗi stale. Không tuyên bố hai API là atomic. Nếu một phần đã lưu, thông báo rõ phần đó và phần còn lỗi, không báo toàn bộ thành công, không giả lập rollback hoặc tự gửi lại phần đã lưu; giữ dữ liệu/nháp trung thực để người dùng xử lý tiếp.
- Lỗi mạng, validation, quyền và lỗi backend không hiện popup thành công; không làm mất bản nháp chưa lưu. Giữ khả năng xử lý lỗi hiện có.

### C. Popup đăng xuất

- Giữ tiêu đề “Đăng xuất”, X đóng, Hủy và Xác nhận.
- Nội dung duy nhất: “Bạn có muốn kết thúc phiên làm việc?”. Bỏ câu nhắc lưu thay đổi và khung ảnh hưởng tồn kho ở popup này.
- Chỉ Xác nhận mới kết thúc phiên và xóa cache theo luồng hiện tại; Hủy/X giữ phiên và dữ liệu bản nháp.
- Không xóa thông báo ảnh hưởng hay xác nhận của các thao tác khác. Không triển khai tự động lưu hoặc tự động bỏ thay đổi để phục vụ đăng xuất.

### D. Ba nút Sửa vai trò

- Giữ cả ba nút hiển thị nhưng dùng `disabled` thật cho ba mã vai trò hệ thống `quan_tri_vien`, `quan_ly`, `nhan_vien`. Đồng bộ kiểu hiển thị với nút Xóa đang bị vô hiệu hóa.
- Không dựa vào chỉ số ba dòng đầu; tìm kiếm/sắp xếp/phân trang không làm mất bảo vệ theo mã vai trò.
- Nút disabled không nhận kích hoạt bằng click hoặc bàn phím, không mở modal hay gửi request.
- Giữ hành vi hiện tại của các vai trò khác và các nút Tạo/Xóa. Đây không phải quyền bổ sung API vai trò.

## Điều kiện kiểm chứng và vòng review

- [x] Flash đã đối chiếu `UsersPage`, `EmployeeForm`, hai API hồ sơ/vai trò, `FeedbackProvider`, `MainLayout`, `RolesPage` và browser tests; xác nhận hai API yêu cầu ETag tuần tự và có rủi ro thành công một phần. Không sửa file hoặc database trong bước khám phá.
- [x] AGY cập nhật caller/fixture/test thực sự bị ảnh hưởng; không xóa hoặc làm yếu assertion để có kết quả xanh.
- [x] Kiểm tra browser cho chuyển xem/sửa trực tiếp, Hủy không ghi, payload/ETag, chống gửi lặp, thành công/lỗi và hai quyết định lưu đã chốt.
- [x] Kiểm tra browser cho ba vai trò hệ thống bị disabled kể cả sau tìm kiếm và không có request khi cố kích hoạt.
- [x] Kiểm tra đăng xuất Hủy/X/Xác nhận và bảo toàn các popup nghiệp vụ khác.
- [x] Kiểm tra keyboard/focus cho input, dropdown và dialog, cùng responsive hiện có.
- [x] Chạy lint, unit tests, build và browser tests có liên quan; báo nguyên lỗi và giới hạn, không mở rộng sửa lỗi ngoài phạm vi.
- [x] Chụp và xem ảnh thật của chế độ xem, sửa trực tiếp, popup thành công, popup đăng xuất và bảng vai trò. Không dùng ảnh AI thay bằng chứng triển khai.
- [x] Cập nhật checklist/đặc tả/MISSING đúng trạng thái; không đóng các mục API còn thiếu.
- [x] AGY trả `worker_done` kèm danh sách file, lệnh/kết quả, ảnh và giới hạn. Codex đọc diff, đối chiếu ảnh và kiểm tra bằng chứng; chỉ kết luận đạt phần đã có bằng chứng.
- [x] Nếu chưa đạt, Codex gửi prompt mới cho cùng AGY chỉ rõ lỗi, vị trí, kết quả mong đợi và cách xác minh; lặp lại review sau khi sửa.

Trạng thái hiện tại: Codex review cuối đã đạt phạm vi frontend. Đã hoàn tất sửa ETag freeze khi refetch nền, ApiError constructor, cache isolation và baseline sau partial save, mở menu logout/layout footer và vô hiệu hóa sửa vai trò hệ thống. Lint, 27/27 unit tests, build, 10/10 admin-ui và 10/10 mutations browser tests đạt ở vòng sửa cuối; Codex đã kiểm chứng độc lập các trường hợp từng lỗi và xem ảnh thực. Chưa kiểm chứng E2E ghi với backend/database thật, chưa commit hoặc push; các API còn thiếu vẫn theo dõi trong `MISSING.md`.
