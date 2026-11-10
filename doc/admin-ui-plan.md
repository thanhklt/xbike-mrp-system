# Kế hoạch triển khai và review Admin UI

Ngày: 07/11/2026. Nhánh làm việc: `feature/UI-admin`.

Codex lập kế hoạch và review; AGY thực thi trong cùng workspace. Dev đã yêu cầu lặp triển khai → kiểm tra → sửa đến khi các phần được phép triển khai đạt tiêu chí bên dưới. Không tự accept, stage, commit hoặc push.

## 1. Nguồn và phạm vi

- Đọc `AGENTS.md`, [quy tắc frontend](./FRONTEND_RULES.md), [đặc tả admin](./dac-ta-giao-dien-admin.md), [MISSING.md](./MISSING.md) trước khi sửa.
- Dùng đúng 5 ảnh trong [ZIP thiết kế](./ui-spec-admin-20261107T125526Z-1-001.zip). Dev đã xác nhận chỉ sử dụng bộ ảnh này cho đặc tả, không chờ tài liệu Drive.
- Dựng đủ ADM-01 Tổng quan, ADM-02 Quản lý tài khoản, ADM-03 Chi tiết tài khoản, ADM-04 Quản lý vai trò và ADM-05 Popup xác nhận.
- Chỉ thay frontend admin và tài liệu/kiểm thử trực tiếp liên quan. Không đổi backend, database, API, phân quyền hoặc dependency. Không đổi theme và luồng của kho/nhân viên/đăng nhập.
- Giữ các file untracked có sẵn: `doc/FRONTEND_RULES.md`, `doc/MISSING.md`, ZIP nguồn. Không ghi đè/hoàn tác thay đổi của dev hoặc agent khác.

## 2. Quyết định dev đã chốt trong phiên

- [x] “incap” là **Impeccable**. Cả Codex lẫn AGY phải đọc và áp dụng Impeccable, Taste và UI/UX Pro Max.
- [x] Button có trong thiết kế nhưng thiếu API vẫn giữ đúng hình thức, **chưa gắn hành động**. Không tự disabled, thêm tooltip/toast/modal hoặc báo thành công giả. Trạng thái disabled vốn đã được ảnh quy định và các chặn an toàn hiện có vẫn được giữ.
- [x] Form tạo/sửa và luồng khóa/mở khóa giữ trường, validation, phân quyền, lý do và xử lý lỗi hiện tại; đồng bộ cách trình bày với giao diện admin.
- [x] Giữ mã nhân viên do API trả về, không biến `NV-000001` thành `NV001` hoặc đổi validation.
- [x] Khi chưa có ảnh nhân viên, dùng avatar chữ cái theo cách hiện có; không thêm upload ảnh hoặc dùng ảnh người giả.
- [x] Hàng mật khẩu trong chi tiết dùng dấu chấm cố định, không lấy hoặc suy ra mật khẩu/hash/độ dài thật.
- [x] Tìm kiếm bằng Enter; bộ lọc áp dụng khi chọn; đổi tìm kiếm/lọc đưa về trang đầu.
- [x] Checkbox chọn tất cả chỉ trên trang hiện tại; không thêm hành động hàng loạt.
- [x] Phân bổ vai trò tính cả tài khoản bị khóa. Số liệu lấy từ API hiện có, không dùng số mẫu trong ảnh.
- [x] Quyết định khi review vòng 1: selector số dòng/trang chỉ giữ **10** như ảnh; không thêm 20/50.

Nếu xuất hiện điểm chưa rõ khác, AGY hỏi Codex bằng cơ chế orchestration; Codex hỏi dev khi quyết định chưa có trong các nguồn trên. Tiếp tục phần độc lập đã rõ, không tự suy diễn.

## 3. Áp dụng ba skill trên cả hai CLI

### Impeccable

Codex đã đọc `C:/Users/binhb/.agents/skills/impeccable/SKILL.md` và chạy `scripts/impeccable.cmd context --target frontend/src/features/auth/UsersPage.jsx` trong root project. Đây là thay đổi có phạm vi theo thiết kế đã cung cấp; không tự mở rộng sang khám phá thương hiệu hoặc dựng hướng thiết kế mới.

AGY phải đọc `C:/Users/binhb/.gemini/config/skills/impeccable/SKILL.md`, chạy launcher `scripts/impeccable.cmd context` một lần cho phiên của mình, đọc `reference/craft-floor.md` ngay trước khi sửa UI và dùng các tham chiếu Operate/audit/critique phù hợp. Nếu launcher không chạy, báo lỗi và đọc ngữ cảnh project trực tiếp theo hướng dẫn fallback của skill; không tự cài/nâng cấp công cụ.

### Taste

Cả hai đọc `.agents/skills/design-taste-frontend/SKILL.md` và `references/app-screens.md`. Áp dụng kiểm tra khoảng cách, căn chỉnh, số liệu, focus và xem screenshot thực. Dùng các script app lint/inspect phù hợp khi chạy được; công cụ tự động không thay thế review trực quan.

### UI/UX Pro Max

Cả hai đọc `.agents/skills/ui-ux-pro-max/SKILL.md`. Codex đã tra cứu `keyboard focus modal --domain ux` và `forms state routing --stack react`: giữ focus rõ ràng, không để overlay che focus và dùng controlled form theo pattern hiện có. AGY thực hiện các tra cứu hẹp cần thiết cho phần mình sửa; kiểm tra gợi ý có phù hợp React 18 và web desktop trước khi áp dụng.

**Ưu tiên:** yêu cầu dev và ảnh nguồn đứng trước gợi ý mặc định của skill. Không bỏ icon thẻ thống kê, màu cam, nền nâu tối, header bảng hoặc các thành phần trong ảnh chỉ vì quy tắc thẩm mỹ chung của skill không thích chúng. Không tạo lại palette/layout ngẫu nhiên, không thêm thành phần “cho đẹp”.

## 4. Kiểm tra trước thay đổi

- [x] Đã đọc các trang admin, layout, hooks dữ liệu, hợp đồng nhân viên/vai trò/audit và cấu hình kiểm thử hiện có.
- [x] Đã chạy kiểm tra ban đầu: lint/build thiếu executable; unit test có 20 mục đạt và 1 file lỗi vì thiếu `axios`.
- [x] Đã chạy `npm ci` theo `frontend/package-lock.json`: cài dependency có sẵn, không nâng cấp hoặc thêm package.
- [x] Chạy lại sau khi dependency sẵn sàng: `npm run lint` đạt; `npm test` đạt 25/25; `npm run build` đạt (Vite 5.4.21). Đây là kết quả trước khi triển khai UI; browser tests chưa chạy ở bước này.

`npm ci` báo 4 lỗ hổng trong dependency hiện có (3 moderate, 1 high). Không chạy `npm audit fix`, không nâng cấp ngoài phạm vi.

## 5. Các bước giao AGY thực thi

AGY làm tuần tự, có thể hoàn thành các bước trong cùng một lượt. Không chỉnh cùng file với Codex; Codex chỉ review khi AGY báo xong hoặc hỏi.

### Bước 1 — Khung admin và tài nguyên thiết kế

- [x] Xem trực tiếp đủ 5 ảnh; có thể giải nén nguyên bản vào `doc/ui-spec-admin/` để đối chiếu, không sửa ZIP gốc.
- [x] Dựng theme admin có phạm vi rõ ràng: nền tối nâu/đen, cam nhấn, thẻ, viền, góc bo, typography và khoảng cách theo ảnh.
- [x] Dựng sidebar logo XBIKE, cảnh xe đạp, ba mục menu; breadcrumb, tên trang và cụm tài khoản phía trên.
- [x] Dùng tài nguyên có sẵn. Nếu dùng ảnh thiết kế làm nguồn hình sidebar, chỉ hiển thị vùng artwork bằng CSS; không dùng nguyên ảnh màn hình để thay giao diện hoặc biểu đồ. Không tự tạo ảnh người hoặc thiết kế thương hiệu mới.
- [x] Giữ route và kiểm tra quyền hiện có, bao gồm các route admin ngoài 5 ảnh; chỉ thay điều hướng hiển thị theo thiết kế. Không tác động sidebar kho/nhân viên.

### Bước 2 — Quản lý tài khoản và chi tiết

- [x] Dựng thanh công cụ, bảng, checkbox, STT, avatar, ngày sinh, badge, nút Chi tiết/Sửa/Vô hiệu hóa/Mở khóa và phân trang theo ảnh.
- [x] Dùng API danh sách hiện tại; mặc định 10 dòng như ảnh, điều hướng số trang từ metadata thật. Không viết cố định tổng trang hoặc số người.
- [x] Dựng trang chi tiết hai cột theo ADM-03, có Quay lại/Chỉnh sửa/Vô hiệu hóa, đủ thứ tự trường, ngày và hệ số lương đúng cách hiển thị.
- [x] Giữ form tạo/sửa hiện có và các payload riêng cho hồ sơ, vai trò, trạng thái. Tách chế độ xem chi tiết khỏi chế độ sửa, cập nhật caller/test trực tiếp bị ảnh hưởng.
- [x] Giữ chặn khóa chính mình/quản trị viên, chặn hạ quyền quản trị viên, yêu cầu lý do và ETag/If-Match.

### Bước 3 — Popup xác nhận

- [x] Áp dụng ADM-05 khi lưu sửa hồ sơ. Lưu tạo mới giữ luồng hiện có vì ảnh xác nhận nằm trên chi tiết.
- [x] Hủy/X không ghi dữ liệu và giữ bản nháp sửa; chỉ Xác nhận mới gọi API lưu.
- [x] Giữ chống gửi lặp, trạng thái đang xử lý, lỗi API, focus và điều khiển bàn phím. Khóa/mở khóa giữ câu chữ và yêu cầu lý do hiện có; không thay bằng câu xác nhận sửa hồ sơ.

### Bước 4 — Vai trò

- [x] Dựng đủ tìm kiếm, nút Tạo vai trò, bảng STT/Tên vai trò/Mô tả/Thao tác và phân trang theo ảnh.
- [x] Dùng danh sách vai trò thật. Chỉ có ba vai trò từ API thì hiển thị ba; không tự thêm “Cộng tác viên”, “Hỗ trợ kỹ thuật”.
- [x] Đối chiếu `VaiTroRead` và router: tạo/sửa/xóa vai trò hoặc mô tả chưa có phải ghi `MISSING.md`. Các nút tương ứng vẫn hiện, chưa gắn hành động; không dựng form hoặc endpoint mới.
- [x] Dữ liệu mô tả thiếu dùng cách hiển thị giá trị thiếu của project, không tự gán quyền từ câu mô tả minh họa. Tìm kiếm/phân trang phía client có thể dùng trên danh sách đã tải đầy đủ, không giả định một trang API là toàn bộ dữ liệu.

### Bước 5 — Tổng quan

- [x] Dựng 4 thẻ theo thứ tự Tổng tài khoản / Tổng vai trò / Tài khoản đang hoạt động / Tài khoản đã vô hiệu hóa; lấy tổng từ API.
- [x] Dựng donut phân bổ từ dữ liệu thật hoặc tổng theo vai trò qua API hiện có; tính cả tài khoản bị khóa, bảo đảm số lượng và tỷ lệ khớp nhau.
- [x] Dựng khung lưu lượng và các nút Hôm nay/7 ngày/30 ngày theo ảnh. Khi chưa có API, ghi thiếu, giữ controls chưa gắn hành động và không vẽ đường/số liệu giả. Giữ vùng biểu đồ để tích hợp sau; không thêm banner giải thích kỹ thuật vào sản phẩm.
- [x] Dựng bảng Hoạt động gần đây 4 cột. Dùng response thực và dữ liệu nhân viên có quyền đọc để hiển thị tên khi có; không tự bịa nội dung sự kiện hoặc lấy thêm trường bị hạn chế. Thiếu thông tin nào ghi `MISSING.md`.

### Bước 6 — Kiểm chứng và báo Codex

- [x] Chạy `npm run lint`, `npm test`, `npm run build` trong `frontend`; không làm yếu kiểm thử để có kết quả xanh.
- [x] Cập nhật và chạy browser tests bị ảnh hưởng do chi tiết chuyển từ modal sang trang, tên menu/tiêu đề và thao tác mới; bảo toàn kiểm thử tương ứng ở kho/nhân viên.
- [x] Bổ sung kiểm thử có ý nghĩa cho xác nhận trước PATCH, Hủy không ghi/không mất bản nháp, chặn gửi lặp, lọc/phân trang, nút thiếu API không gọi request và kiểm tra quyền/ETag hiện có.
- [x] Dùng API fixture hiện có cho browser tests; không ghi vào database ứng dụng. Fixture chỉ dành cho test, không được import vào UI chạy thật.
- [x] Chụp và xem đủ 5 màn hình ở kích thước gần ảnh nguồn, thêm 1440×900; kiểm tra không vỡ nội dung ở màn hình hẹp theo cơ chế responsive sẵn có, không tự thiết kế thêm luồng mobile.
- [x] Kiểm tra console lỗi, focus, tương phản, dữ liệu rỗng/lỗi/tải và khả năng truy cập.
- [x] Cập nhật checklist đặc tả, plan và `MISSING.md` theo bằng chứng, phân biệt đã dựng UI / đã tích hợp / đã kiểm tra. Không đánh dấu API còn thiếu là đã hoàn thành.
- [x] Báo bằng `worker_done`: file sửa, kết quả từng lệnh, đường dẫn screenshot đã xem, skill đã đọc/chạy, mục thiếu và các quyết định còn cần dev. Nếu một check lỗi, ghi rõ là lỗi; không tuyên bố toàn bộ đã đạt.

## 6. Điều kiện Codex chấp nhận và vòng lặp

1. Codex đọc diff và đối chiếu source/ảnh ở cả 5 màn hình; xem screenshot thực, không chỉ dựa báo cáo của AGY.
2. Không có lỗi chức năng, bảo mật, validation, quyền, ETag hoặc ảnh hưởng theme/luồng ngoài admin do thay đổi.
3. Các check có liên quan đạt; nếu có giới hạn môi trường thì phải nêu rõ và không coi là kiểm chứng thành công.
4. Từng phần trong thiết kế có hiện diện. Ngoại lệ dữ liệu/API được ghi rõ trong `MISSING.md`, đúng quyết định giữ nút chưa gắn hành động; không có chức năng hoặc dữ liệu giả.
5. Nếu có lỗi hoặc khác ảnh đáng kể, Codex gửi danh sách cụ thể cho cùng AGY worker sửa, kèm vị trí, kết quả mong đợi và cách xác minh; AGY báo lại, Codex review tiếp. Không dừng ở lần bàn giao đầu nếu chưa đạt.
6. Không mở rộng backend hoặc tự quyết yêu cầu còn thiếu để đạt “hoàn thành toàn bộ”. UI được phép triển khai và các phụ thuộc chưa có phải được báo riêng.

## 7. Nhật ký vòng lặp

- [x] Vòng 1: AGY triển khai theo kế hoạch này, tự kiểm tra và báo Codex.
- [x] Codex review vòng 1: đã xem diff/source và đủ 5 screenshot nguồn-size. **Chưa đạt**: ETag khi khóa từ danh sách, tỷ lệ/bố cục, popup và bằng chứng test; xem [prompt sửa vòng 2](./admin-ui-review-round-2.md).
- [x] Vòng 2: AGY đã sửa toàn bộ `R2-01`..`R2-05` theo `doc/admin-ui-review-round-2.md`, kiểm chứng lại và báo Codex kiểm tra; chờ Codex review nghiệm thu UI.
- [x] Codex review cuối (08/11/2026): đạt phạm vi frontend được phép triển khai. Đã đối chiếu source/ảnh, kiểm tra bổ sung bốn route và chạy lại ADM-02 (1/1 đạt). Chi tiết file sửa, bằng chứng và giới hạn ở `doc/admin-ui-review-round-2.md`; các API còn thiếu vẫn mở trong `MISSING.md`, không báo E2E backend thật hoặc toàn bộ browser suite xanh.
