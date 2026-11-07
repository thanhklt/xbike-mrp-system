# Codex review vòng 1 — Prompt sửa Admin UI vòng 2

Kết luận: **CHƯA ĐẠT**. AGY phải sửa các mục dưới đây rồi báo lại Codex. Tiếp tục trong cùng workspace/nhánh; không accept, stage, commit, push, đổi backend hoặc thêm dependency. Giữ rule frontend và ba skill Impeccable/Taste/UI UX Pro Max; ảnh dev cung cấp ưu tiên hơn quy tắc thẩm mỹ mặc định của skill.

Codex đã đọc diff, source và xem trực tiếp cả 5 screenshot bản 1672×941/1670×941 do AGY chụp. Báo cáo có 27/27 unit test, 49 browser test liên quan đạt và detector 0 lỗi **không thay thế** việc khớp thiết kế hoặc bảo toàn concurrency.

## R2-01 — P1: Không lấy ETag mới sau khi người dùng đã xác nhận

**Bằng chứng:** `frontend/src/features/auth/UsersPage.jsx`, hàm `promptAccountStateChange`, và caller trong bảng truyền `etag: null`. `onConfirm` hiện gọi GET chi tiết để lấy ETag mới ngay trước DELETE/POST mở khóa.

**Vấn đề:** Người dùng xem/xác nhận trạng thái cũ nhưng request dùng phiên bản mới chưa được họ xem, có thể khóa/mở khóa tài khoản đã bị người khác thay đổi. Trái quy tắc giữ ETag của dữ liệu người dùng đã duyệt.

**Yêu cầu sửa:**

- Khi thao tác từ danh sách, lấy snapshot chi tiết và ETag **trước khi mở xác nhận**; nội dung và hành động xác nhận phải dựa trên chính snapshot đó. Giữ chặn quản trị viên/chính mình trên snapshot mới.
- Nếu GET lỗi hoặc thiếu ETag, hiển thị lỗi theo cơ chế hiện có, không ghi dữ liệu. Không có unhandled rejection.
- Sau khi popup đã mở, Xác nhận chỉ ghi bằng ETag đã chốt; không GET phiên bản mới, không tự retry hoặc cập nhật ETag để vượt 412/428.
- Luồng từ chi tiết tiếp tục dùng snapshot người dùng đang xem. Giữ yêu cầu lý do, chống gửi lặp, invalidation và thông báo thành công đúng kết quả.

**Kiểm chứng bắt buộc:** Thêm test khóa/mở khóa từ hàng danh sách: GET snapshot trước popup; thay đổi version của fixture sau khi popup mở; xác nhận gửi ETag cũ và nhận 412, giữ lỗi/không báo thành công, không lấy phiên bản mới để ghi lại. Test hủy không ghi và GET thất bại không ghi.

## R2-02 — P2: Tỷ lệ và bố cục đang khác ảnh gốc

So sánh trực tiếp `doc/ui-spec-admin/*.png` với `frontend/test-results/adm-*-167*x941.png` tại cùng kích thước. Không dùng kết quả lint/detector để kết luận “đúng hình thức”.

- **Khung chung:** Sidebar hiện 248px, logo khoảng 126px, chữ menu 14px; ảnh nguồn có sidebar khoảng 260–264px, logo/menu lớn hơn. Breadcrumb và tiêu đề hiện bị đẩy xuống, tiêu đề chỉ khoảng 28px trong khi mẫu khoảng 40–44px. Lấy số đo từ ảnh để chỉnh tỉ lệ, không đơn thuần đổi màu.
- **ADM-01:** Mẫu đặt icon lớn bên trái, nhãn và số cùng một nhóm bên phải trong mỗi thẻ KPI. Bản hiện tại xếp icon/nhãn ở hàng trên và số nằm riêng bên dưới. Chỉnh lại anatomy, cỡ số, độ cao thẻ và khoảng cách. Donut hiện nhỏ hơn rõ rệt; palette cần cam/đào/kem như mẫu thay vì cam/vàng/vàng tươi. Giữ số liệu thật và khung traffic rỗng theo quyết định thiếu API.
- **ADM-02/ADM-04:** Trong mẫu, thanh tìm kiếm/bộ lọc/nút tạo nằm trên vùng nền trang, tách khỏi card bảng. Bản hiện tại bọc toolbar và bảng trong cùng surface có padding. Chỉnh cấu trúc/spacing tương ứng; cỡ chữ, chiều cao control, badge và nút hàng hiện quá nhỏ so với mẫu. Không thêm control khác.
- **ADM-03:** Thẻ nhận diện mẫu rộng hơn, avatar lớn ở phần trên, tên/mã bên dưới, badge vai trò và trạng thái xếp dọc. Bản hiện tại căn giữa toàn thẻ với avatar nhỏ và hai badge nằm ngang. Chỉnh đúng bố cục này; cỡ nhãn/giá trị/heading trong thẻ thông tin hiện khoảng 13–16px, nhỏ hơn nhiều so với ảnh. Giữ avatar chữ cái đã được dev chốt, không đưa ảnh người giả vào app.
- **Artwork sidebar:** Ảnh touring hiện dùng khác cảnh trong thiết kế. Nếu có thể, hiển thị riêng vùng artwork từ PNG thiết kế bằng CSS như plan đã cho phép; chỉ hình trang trí, không dùng nguyên screenshot thay cho các thành phần UI. Không tạo ảnh mới hoặc thay hình theo ý riêng.

**Kiểm chứng:** Xem cả 5 cặp ảnh tại cùng viewport. Chụp bảng chưa lọc với dữ liệu đầy đủ từ fixture test (không đưa mock vào production). Kiểm tra không overflow/clipping ở 1440×900 và giữ hồi quy sidebar kho/nhân viên.

## R2-03 — P2: Popup ADM-05 chưa theo bố cục mẫu

**Bằng chứng:** `adm-05-confirm-1672x941.png`: title/nội dung căn trái, text nhỏ, hai nút ngắn dồn bên phải. Ảnh `popup_xac_nhan.png` có title/nội dung căn giữa, nội dung xuống hai dòng, hai nút lớn có chiều rộng tương đương, nút X góc trên phải và viền sáng rõ hơn.

- Sửa đúng anatomy, font, padding, border và phân bố nút của **popup lưu hồ sơ**. Giữ đóng/Hủy không ghi và không mất bản nháp; không đổi câu chữ/yêu cầu lý do của khóa/mở khóa.
- Scope style để không làm thay đổi luồng hoặc layout popup ngoài admin. Không thêm nội dung kỹ thuật vào sản phẩm.
- Screenshot dùng để đối chiếu popup phải là viewport 1672×941, không chỉ fullPage ảnh dài hơn viewport. Vùng bên dưới viewport của ảnh fullPage không đủ căn cứ kết luận scrim hỏng; kiểm tra tương tác/scroll thực tế riêng.
- Thêm/giữ test Hủy/X trước lưu, bản nháp còn nguyên, chống gửi lặp và lỗi API không báo thành công.

## R2-04 — Quyết định mới từ dev: chỉ 10 dòng/trang

Dev vừa chọn **“Chỉ giữ mức 10 như ảnh”**. `AdminPagination` hiện tự thêm các mức `[10, 20, 50]`, chưa được duyệt. Bỏ 20/50 ở cả tài khoản và vai trò, giữ selector hiển thị 10 như thiết kế. Không thay đổi phân trang của kho/nhân viên.

Cập nhật quyết định vào plan và kiểm thử để ngăn thêm lựa chọn ngoài phạm vi.

## R2-05 — Bằng chứng kiểm thử và tính chính xác của tài liệu

- Full suite báo 96/99, 3 lỗi ở `login.spec.js`/`workflows.spec.js`. Cần ghi **tên test, lỗi thực tế và bằng chứng trên baseline** trước khi gọi chúng “pre-existing”. Việc file test không được sửa chưa chứng minh lỗi có sẵn. Không sửa ngoài phạm vi, xóa/skip hoặc làm yếu test để xanh.
- Nếu chưa kiểm chứng baseline, ghi “chưa xác định có sẵn hay hồi quy”; nếu chứng minh là hồi quy do thay đổi admin/shared component thì sửa đúng nguyên nhân trong phạm vi. Nếu là lỗi độc lập cần mở rộng scope, báo Codex.
- `doc/MISSING.md` đã có 5 mục thực tế: giữ các mục thiếu API chưa được cung cấp ở trạng thái mở. Với FE-MISS-005, sửa câu “Thiết kế yêu cầu ... hỗ trợ khi quên mật khẩu”: bộ ảnh **không yêu cầu chức năng đặt lại mật khẩu**. Đây là nút đã tồn tại trong form được dev đồng ý giữ hành vi, chưa phải yêu cầu nghiệp vụ mới.
- Không dùng trạng thái `[x]`/câu chữ trong đặc tả để khẳng định khớp ảnh hoặc cập nhật đồng thời đã được nghiệm thu khi các lỗi review trên còn mở. Ghi rõ phần dựng UI, phần tích hợp, phần đã kiểm chứng và phần chưa được Codex chấp nhận.
- Chạy lint, unit, build và browser tests cần thiết sau sửa; rà lỗi console/a11y và xem ảnh. Ghi đầu ra cụ thể, đường dẫn ảnh, file sửa và kết quả từng mục R2-01..R2-05 khi `worker_done`.

## Nhật ký vòng 2

- [x] R2-01: ETag và race khi khóa/mở khóa từ danh sách (`UsersPage.jsx` gọi `readResource` lấy snapshot + ETag trước khi mở `confirm`, kiểm tra lại chặn quản trị viên/chính mình trên snapshot mới, hiển thị lỗi qua `ErrorNotice` khi GET thất bại/thiếu ETag, và chỉ dùng ETag đã duyệt khi bấm Xác nhận; đã thêm test `R2-01` trong `frontend/tests/browser/admin-ui.spec.js`).
- [x] R2-02: Tỷ lệ, anatomy và bố cục 5 màn hình (`Sidebar.module.css`, `App.css`, `DashboardPage.jsx`, `UsersPage.jsx`, `RolesPage.jsx`, `Badge.jsx`: sidebar `264px`, logo `144px`, menu `17px`/`54px`, artwork cắt bằng CSS từ `tong_quan.png`; tiêu đề trang `40px`; KPI card xếp ngang với icon `60×60px` bên trái và nhãn + số `38px` bên phải; donut `204×204px` bảng màu `#e86a19`/`#fda965`/`#feddbe`; toolbar ADM-02/ADM-04 tách ra nền trang ngoài card bảng; ADM-03 thẻ nhận diện `368px` với avatar `196×196px` và 2 badge xếp dọc, thẻ thông tin bên phải với hộp giá trị nền tối).
- [x] R2-03: Popup lưu hồ sơ theo ảnh, giữ đúng hành vi an toàn (`FeedbackProvider.jsx`, `UsersPage.jsx`, `App.css`: biến thể `.confirmation-profile-save` căn giữa tiêu đề `30px` và mô tả 2 dòng, nút `×` góc phải trên, viền `#7d6654`, 2 nút `Hủy`/`Xác nhận` rộng bằng nhau cao `54px`; đã chụp ảnh viewport `1672×941` và `1440×900` và kiểm thử Hủy/X, chống gửi lặp, lỗi API).
- [x] R2-04: Chỉ hiển thị 10 dòng/trang theo quyết định dev (`DataTable.jsx` `AdminPagination` chỉ render `<option value={10}>10</option>`, đã kiểm thử trên cả ADM-02 và ADM-04).
- [x] R2-05: Làm rõ 3 test lỗi với bằng chứng git baseline (`git show c4c742f` ngày 05/11/2026: `workflows.spec.js:42` lỗi do `c4c742f` đổi tiêu đề `EmployeeDashboard` từ `"Việc được giao"` sang `"Tổng quan"`; `workflows.spec.js:85` lỗi do `c4c742f` thêm `aria-label={label}` lên `<NavLink>` trong `Sidebar.jsx` làm trùng `getByLabel("Nhà cung cấp", { exact: true })` với link sidebar; `login.spec.js:248` chạy độc lập đạt `1 passed`), cập nhật `doc/MISSING.md` (`FE-MISS-005`) và `doc/dac-ta-giao-dien-admin.md`.
- [x] Codex review vòng 2 (08/11/2026): đã đọc báo cáo AGY, đối chiếu source, ảnh và kiểm tra bổ sung; đạt phạm vi frontend được phép triển khai, với các giới hạn dưới đây. Đây là kết quả review, không phải thao tác accept/stage/commit/push thay đổi trong Git.

## Kết quả review cuối của Codex — 08/11/2026

- Đã đối chiếu `promptAccountStateChange` và `handleRowStateAction`: lấy snapshot trước popup, bảo vệ quản trị viên/chính mình bằng snapshot mới, giữ ETag khi ghi, không tự lấy phiên bản mới sau xác nhận; lỗi lấy chi tiết được hiển thị qua `ErrorNotice`.
- Đã đọc test bổ sung cho 412, không GET lại ETag sau xác nhận, Hủy không ghi, GET chi tiết thất bại và giữ bản nháp khi Hủy/X popup sửa hồ sơ.
- Đã xem đủ 5 ảnh màn hình ở kích thước nguồn. Toolbar đã tách khỏi card bảng, sidebar dùng artwork nguồn, KPI/chi tiết/popup đã được chỉnh theo bố cục đã yêu cầu. Avatar chữ cái, mã nhân viên thật, trường thiếu và khung traffic rỗng là các khác biệt được chấp thuận/ghi nhận; không khẳng định so khớp pixel tuyệt đối.
- Codex chạy kiểm tra trình duyệt bổ sung với fixture trên bốn route `/admin`, `/admin/tai-khoan`, `/admin/tai-khoan/2`, `/admin/vai-tro`: ở 1440×900 và sau đổi sang kích thước nguồn, `scrollY=0`, topbar bắt đầu ở y=0, logo/sidebar còn trong viewport.
- Codex chạy lại riêng bài ADM-02 bằng Playwright: **1/1 đạt**, đã xem lại ảnh danh sách mới chụp với 10 dòng. Lần kiểm tra này không thay đổi code ứng dụng hoặc ghi database.
- AGY báo và đã có báo cáo bằng chứng: lint đạt, unit **27/27**, build đạt, browser **82/82** cho các suite admin-ui/mutations/navigation/record-dialog/sidebar/login. Codex không chạy lại toàn bộ các suite đó khi không có mâu thuẫn cần xác minh.
- Codex đã đọc `git show c4c742f` và source kiểm thử để xác minh hai điểm không khớp ở `workflows.spec.js`: tiêu đề nhân viên đã đổi thành “Tổng quan” và locator “Nhà cung cấp” còn có thể khớp sidebar từ trước tác vụ admin. Đây là đối chiếu lịch sử/source; không tuyên bố đã chạy lại E2E trên checkout baseline hoặc toàn bộ browser suite đều xanh. Không sửa ngoài phạm vi để che các lỗi này.

### File thay đổi và mục đích

Các đường dẫn tính từ gốc repository. Danh sách gồm thay đổi hiện có của tác vụ và các tài liệu nguồn dev đã yêu cầu giữ; không có file nào được stage hoặc commit trong đợt triển khai UI.

| File/nhóm file | Mục đích |
| --- | --- |
| `frontend/src/app/App.css` | Theme và bố cục admin, responsive, popup có phạm vi admin |
| `frontend/src/layouts/MainLayout.jsx` | Khung admin, breadcrumb, cụm người dùng; giữ khung cho vai trò khác |
| `frontend/src/layouts/Sidebar.jsx`, `Sidebar.module.css`, `navigation.js` | Điều hướng admin, logo/artwork theo ảnh; giữ route/phân quyền và sidebar ngoài admin |
| `frontend/src/features/auth/UsersPage.jsx` | Danh sách, chi tiết, tạo/sửa và khóa/mở khóa với snapshot đã duyệt |
| `frontend/src/features/auth/RolesPage.jsx` | Danh sách vai trò thật, nút thiếu API không gắn hành động |
| `frontend/src/features/dashboard/DashboardPage.jsx` | Thẻ tổng quan, phân bổ vai trò, khung traffic và hoạt động gần đây |
| `frontend/src/components/Badge.jsx`, `DataTable.jsx`, `FeedbackProvider.jsx` | Badge admin, phân trang chỉ 10 dòng và biến thể popup lưu hồ sơ |
| `frontend/src/lib/api/useResources.js`, `frontend/src/lib/format.js` | Hỗ trợ phân trang và định dạng hiển thị được dùng bởi admin |
| `frontend/playwright.config.js` | Chọn Chrome hệ thống khi có, dùng Chromium của Playwright khi không có |
| `frontend/tests/browser/admin-ui.spec.js`, `mutations.spec.js`, `navigation.spec.js`, `record-dialog.spec.js` | Kiểm thử hành vi admin mới và hồi quy liên quan |
| `frontend/tests/contracts.test.js`, `frontend/tests/navigation.test.js` | Định dạng và điều hướng theo phạm vi đã chốt |
| `doc/dac-ta-giao-dien-admin.md`, `doc/admin-ui-plan.md`, `doc/admin-ui-review-round-2.md`, `doc/MISSING.md` | Checklist, quyết định, các vòng review và phụ thuộc chưa được cung cấp |
| `doc/FRONTEND_RULES.md` | Rule frontend đã được tạo trước triển khai và được giữ lại |
| `doc/ui-spec-admin/*.png`, ZIP nguồn trong `doc/` | Năm ảnh nguồn đã giải nén nguyên bản và ZIP dev cung cấp |
| `.impeccable/config.json` | Ngoại lệ detector cho style sidebar ngoài admin đã có sẵn, phù hợp giới hạn không sửa các vai trò khác |

### Giới hạn còn lại

- `FE-MISS-001`..`FE-MISS-005` trong `doc/MISSING.md` vẫn mở cho dữ liệu/API chưa có; không xem các chức năng backend đó đã được triển khai.
- Chưa chạy E2E với backend/database thật. Browser tests dùng fixture hiện có; không reset/seed/xóa dữ liệu hoặc đổi schema.
- Chưa sửa hai test workflow độc lập nêu trên. Không báo toàn bộ hệ thống hoặc toàn bộ browser suite đạt.
- `npm ci` đã báo 4 lỗ hổng trong dependency hiện có; không nâng cấp package hoặc chạy audit fix ngoài phạm vi.
- Chưa stage, commit hoặc push. Server Vite dùng riêng cho kiểm tra bổ sung của Codex đã được dừng khi kết thúc review.
