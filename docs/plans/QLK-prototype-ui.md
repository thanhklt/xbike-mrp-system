# Frontend Quản lý kho theo prototype đã duyệt

Ngày: 17/11/2026. Nguồn giao diện: `docs/prototypes/XBike_MRP_Prototype-backend-v4.html` mới nhất, bao gồm đơn vị tính có dấu và bỏ hai dòng giới thiệu ở đầu trang.

Dev cho phép sửa frontend QLK và xác nhận đồng bộ các form/thao tác cũ sang API v4. Không sửa backend, schema, database, dependency; không commit/push.

## Phạm vi và quyết định

- Dùng màu tối nâu/cam, bố cục và ngôn ngữ của prototype. Không tạo hướng thiết kế mới hoặc đưa dữ liệu giả/hàm nghiệp vụ mô phỏng vào ứng dụng.
- CSS chỉ có hiệu lực khi vai trò đã xác thực là `quan_ly`, gồm cả dialog xác nhận nằm ngoài layout. Dọn cờ theme khi đổi vai trò/đăng xuất. Giữ giao diện QTV và NV.
- Giữ route, API client Axios, TanStack Query, kiểm tra phiên/quyền, ETag đã xem và thông báo lỗi của ứng dụng. Các route NCC/điều chỉnh/ticket hiện có giữ nguyên; vị trí và việc hiện menu được cập nhật theo phản hồi cuối tài liệu. Đổi giao diện không đồng nghĩa backend các context cũ đã được nghiệm thu v4.
- API thật là chuẩn cho dữ liệu và thao tác. Không thêm nút QLK lập/sửa/xóa/gửi/về nháp phiếu xuất. Không lấy cây BOM nhiều cấp hoặc gọi POST `/bom` cũ.
- Mặt hàng: hai loại v4; mã tự sinh; số tồn/đang giữ/còn dùng từ server. Thành phẩm mới kèm `bom.chi_tiet`, PATCH không gửi mã/loại/BOM. Chỉ thành phẩm được ngừng/dùng lại theo lifecycle backend hiện có.
- Nhà cung cấp giữ màn hiện có, sửa form tạo để mã do DB sinh và gửi đủ năm trường bắt buộc của `NhaCungCapCreate`. Không bổ sung màn sửa/xóa NCC mới.
- BOM: một cấp, bất biến; tạo phiên bản qua `POST /bom/{id}/phien_ban`. Đổi phiên bản/ngừng/dùng lại mang ETag của bản được xem. Tạo định mức đầu tiên qua màn tạo thành phẩm.
- Nhập kho/sản xuất/báo cáo/audit giữ API thật hiện có; bộ lọc/phân trang/đơn vị tính được trình bày theo prototype. Báo cáo vẫn chỉ đọc sổ kho.

## Task và tiêu chí

| Task | Kết quả | Kiểm chứng |
| --- | --- | --- |
| T1 — Khảo sát | Đọc layout, component dùng chung, API và schema v4; ghi nhận mốc trước | Build, lint, 284 test logic đạt. Browser ban đầu: 23/24 đạt; lỗi sẵn `/nv/xuat-nvl` không có dòng phù hợp fixture |
| T2 — Khung QLK | Theme, sidebar/logo, tài khoản góc phải, bảng/form/dialog/responsive | Kiểm tra trình duyệt desktop/tablet/điện thoại, hoạt động menu và sự cách ly vai trò |
| T3 — Form v4 | Mặt hàng/BOM/PX đúng request và trạng thái đã được dev xác nhận | Test body/header/method/path; hủy xác nhận không ghi; lỗi giữ nội dung, không tự đổi ETag |
| T4 — Bàn giao | Bộ lọc, báo cáo, lịch sử và màn vận hành dùng API; ghi kết quả | Test logic, lint/build; browser với fixture API tại biên mạng; chụp và xem bố cục |

## Truy vết

| UC | Màn/tầng frontend | Kiểm chứng chính |
| --- | --- | --- |
| UC-09–12, UC-16 | `MaterialsPage.jsx`, `itemForm.js` → client `/mat_hang` | Số dư server, mã tự sinh, BOM đầu tiên, PATCH/DELETE đúng payload và ETag |
| UC-13/14 | `SuppliersPage.jsx` → client `/nha_cung_cap` | Form tạo không gửi mã; tên/điện thoại/địa chỉ/phường/tỉnh bắt buộc |
| UC-15, UC-17–19 | `BOMPage.jsx` → client `/bom/{id}` | Phiên bản một cấp, activate/stop, không có POST collection hoặc gửi version/is_active tự đặt |
| UC-20–22 | `ReceivingPage.jsx` → client `/phieu_nhap` | Nháp và hoàn tất giữ luồng hiện có, chỉ chọn linh kiện |
| UC-23–33 | Các trang `production` | Giữ luồng API, bố cục theo theme QLK, quyền NV giữ nguyên |
| UC-34–40 | `MaterialIssuingPage.jsx`, `ApprovalActions.jsx` | QLK chỉ đọc/duyệt/từ chối; snapshot ETag; không sửa dòng hoặc gửi đơn giá |
| UC-41–43 | `ReportsPage.jsx`, `MovementsPage.jsx`, `AuditPage.jsx` | Bộ lọc AND, ngày VN, nhãn và đơn vị có dấu, chỉ đọc |

## Kết quả cuối

### Các file chính

| Nhóm | File | Vai trò/thay đổi |
| --- | --- | --- |
| Theme QLK | `frontend/src/layouts/Warehouse.css` (mới), `MainLayout.jsx`, `Sidebar.jsx`, `Sidebar.module.css` | Theme riêng QLK, logo trong sidebar, tài khoản góc phải, trạng thái/bảng/form/dialog, responsive và cleanup theme |
| Danh sách | `frontend/src/components/Collection.jsx`, `DataTable.jsx` | Tùy chọn Xóa lọc, 20/50/100 dòng và đổi nhãn lựa chọn mà giữ nguyên giá trị gửi server; mặc định của các vai trò khác giữ nguyên |
| Thao tác chứng từ | `frontend/src/components/ApprovalActions.jsx` | Cho phép màn QLK chỉ cấp đúng hai thao tác duyệt/từ chối, không dùng quyền lập/sửa cũ |
| Mặt hàng | `frontend/src/features/materials/MaterialsPage.jsx`, `itemForm.js` (mới) | Hiện ba số dư, payload v4, BOM đầu tiên cùng thành phẩm, PATCH chỉ trường thay đổi, trạng thái TP qua ETag |
| BOM | `frontend/src/features/bom/BOMPage.jsx` | Một cấp, bỏ POST collection và cây nhiều cấp, tạo phiên bản/ngừng/dùng lại mang ETag chi tiết; đường dẫn `/moi` cũ chuyển đến tạo TP |
| Nhà cung cấp | `frontend/src/features/suppliers/SuppliersPage.jsx` | Form tạo theo schema hiện tại, mã readonly tự sinh, đủ năm trường bắt buộc |
| Phiếu xuất | `frontend/src/features/material-issuing/MaterialIssuingPage.jsx` | QLK đọc/duyệt/từ chối; không có chế độ lập/sửa/xóa/gửi/về nháp; nhận loại `xuat_linh_kien` và nguồn yêu cầu |
| Vận hành | `frontend/src/features/receiving/ReceivingPage.jsx`, `production/RequestsPage.jsx`, `production/CompletionListPage.jsx` | Bộ lọc/phân trang QLK; nhập chỉ chọn LK; thay lối tạo PX sai trong yêu cầu bằng lối xem danh sách |
| Theo dõi | `frontend/src/features/dashboard/DashboardPage.jsx`, `inventory/MovementsPage.jsx`, `reports/ReportsPage.jsx`, `reports/AuditPage.jsx`, `lib/format.js` | Nhãn tiếng Việt, đơn vị có dấu, bộ lọc/ngày/phân trang; số liệu vẫn từ API thật, không chuyển cách tính sang frontend |
| HTTP | `frontend/src/lib/api/client.js` | `body: null` nghĩa là không có thân HTTP, tránh Axios tuần tự hóa thành chuỗi `null` ở DELETE không nhận body; payload lý do và action `{}` vẫn giữ nguyên |
| Test | `frontend/tests/warehouse-item-form.test.js` (mới), `browser/warehouse-ui.spec.js` (mới), `client.test.js`, `browser/api-fixture.js`, `browser/mutations.spec.js`, `browser/workflows.spec.js` | Kiểm tra request v4, không ghi khi hủy, ETag/409/412, body rỗng, vai trò, responsive; fixture theo loại/field v4, locator phiếu nhập được giới hạn trong dialog |

### Kiểm chứng

| Lệnh/kiểm tra | Kết quả |
| --- | --- |
| `npm test` | **289 pass, 0 fail** |
| `npm run lint` | Đạt |
| `npm run build` | Đạt |
| Playwright: warehouse-ui/sidebar/mutations/workflows/record-dialog, loại trừ năm test auth/NV nêu dưới | **58 pass**; gồm các luồng QLK và hồi quy liên quan |
| `npx playwright test tests/browser/warehouse-ui.spec.js` sau lượt rà ảnh cuối | **13 pass, 0 fail**; thêm kiểm tra liên kết yêu cầu không lập PX, footer popup tối, số lượng BOM nhìn thấy được và request DELETE thực sự không có body |
| Rà giao diện | Chụp 12 màn QLK ở 1440/768/390px, không tràn ngang; mở/đóng/thu gọn sidebar, modal và đổi vai trò được kiểm tra |
| Design skill lint trên theme/Mặt hàng/BOM/PX | 0 fail, 1 cảnh báo: công cụ bắt chuỗi `box-shadow: none` như có shadow; rule thực tế đang loại shadow của card, giữ có chủ đích |
| Giới hạn thay đổi | Không sửa backend, infra, routing, auth hoặc package/dependency; không commit/push |

Test browser dùng API fixture tại biên HTTP, không nạp mock vào ứng dụng và không ghi vào database ứng dụng. Không coi kết quả trên là E2E với PostgreSQL thật.

Lượt chạy rộng đầu tiên (61 test) có 8 lỗi: ba lỗi của phần đang triển khai/fixture đã được sửa và kiểm tra lại; năm test auth/NV ngoài phạm vi vẫn chưa đạt, nên không tuyên bố toàn bộ browser suite xanh:

- `mutations`: khóa tài khoản đòi lý do bắt buộc, khác luồng UC-05 hiện tại.
- `record-dialog`: `/nv/xuat-nvl` không có dòng do bộ lọc cũ. Lỗi này đã xuất hiện ở lượt baseline 23/24.
- `workflows`: thông báo sai thông tin đăng nhập; phiên `/auth/me` đổi vai trò; NV đọc danh sách phiếu xuất. Source auth/routes không được chỉnh trong tác vụ này.

Các test đó vẫn được giữ nguyên, không skip hoặc sửa kỳ vọng để làm xanh. Lệnh chạy phạm vi dùng `--grep-invert "locking an employee|/nv/xuat-nvl|bad credentials|the latest /auth/me|employee can view issues"`; ghi rõ lựa chọn này để tránh hiểu là đã chạy đạt toàn suite.

### Khác biệt được giữ có chủ đích

- Bố cục/màu theo prototype đã được dev chọn, không bốc ngẫu nhiên hướng thiết kế; giữ thư viện icon, font và stack hiện có.
- Rà ảnh đã sửa nút Tìm quá rộng, ngày nhập bị xuống dòng, tài khoản mobile bị ẩn tên, footer xác nhận còn nền trắng và bảng xác nhận BOM đẩy cột số lượng ra khỏi khung; kiểm tra lại sau sửa.
- Dữ liệu đếm/tồn/audit, lỗi và trạng thái tải là dữ liệu API, có thể khác các con số demo trong prototype. Audit không có ô tìm mã giả vì backend chỉ có bộ lọc tương ứng đã triển khai.
- Mã đơn vị đang lưu không được đổi để làm đẹp nhãn. PATCH không gửi lại trường không thay đổi, kể cả đơn vị dữ liệu cũ có dấu; đơn vị mới vẫn tuân schema mã không dấu.
- Các màn ticket/điều chỉnh cũ chỉ nhận theme qua layout; không bổ sung endpoint hoặc xác nhận nghiệp vụ v4 cho các context đó. Sửa/xóa NCC vẫn chưa được triển khai trong frontend.
- Chưa kiểm chứng biên BIGINT hoặc E2E nghiệp vụ toàn hệ thống; giới hạn số nguyên an toàn của các input tiền hiện có vẫn giữ nguyên.

### Cách xem

Chạy backend v4 hiện tại, rồi trong `frontend` chạy `npm run dev` và đăng nhập tài khoản có mã vai trò `quan_ly`. Refresh trang nếu Vite đang chạy từ trước. Không cần tạo lại database hoặc nạp seed để áp dụng giao diện.

## Bổ sung theo phản hồi — 17/11/2026

- `frontend/src/layouts/navigation.js`: bỏ mục Ticket sự cố khỏi sidebar QLK. Không xóa endpoint hoặc các liên kết tới ticket trong lịch sử/lỗi nghiệp vụ.
- `frontend/src/layouts/Warehouse.css`: ẩn dòng mô tả dưới tiêu đề trang trong layout QLK; giữ tiêu đề chính, các nút thao tác và thông tin bên trong trang. Không tác động header của QTV/NV.
- Cập nhật kỳ vọng menu trong `tests/browser/navigation.spec.js` (giữ mục chứng từ hoàn thành hiện có) và kiểm tra không còn mục Ticket/dòng mô tả hiển thị trên các màn trong `warehouse-ui.spec.js`.
- Kiểm chứng: **9/9 test logic điều hướng**, **3/3 test trình duyệt được chọn** (menu desktop/mobile và 12 màn ở 1440/768/390px), lint và build đều đạt. Không chạy lại toàn suite hoặc ghi database cho thay đổi hiển thị này.

## Sắp xếp sidebar theo ảnh — 17/11/2026

- `navigation.js`: sidebar QLK gồm đúng bốn nhóm theo thứ tự ảnh: **Chung** (Tổng quan); **Danh mục** (Mặt hàng & tồn kho, Định mức BOM); **Vận hành** (Phiếu nhập kho, Nhu cầu bổ sung LK, Yêu cầu sản xuất, Phiếu xuất kho, Hoàn thành sản xuất); **Theo dõi** (Nhập – xuất – tồn, Biến động kho, Lịch sử thao tác).
- Nhà cung cấp và Điều chỉnh kho được bỏ khỏi sidebar theo bố cục mới, không xóa trang, route hoặc API. Hồ sơ/Đăng xuất giữ nguyên; không đổi menu hai vai trò còn lại.
- `Sidebar.jsx`: dùng icon Lucide đã cài cho từng mục QLK theo ảnh; giữ ánh xạ icon của QTV/NV. Không sửa màu hoặc stylesheet trong lượt này.
- `tests/browser/navigation.spec.js`, `sidebar.spec.js`, `workflows.spec.js`: cập nhật thứ tự/tên hiển thị; thao tác hover/thu gọn/điều hướng dùng mục Mặt hàng thay NCC đã được bỏ khỏi menu.
- Kiểm chứng: **9/9 test logic điều hướng**, **11/11 test trình duyệt được chọn**, lint/build đều đạt. Đã xem ảnh desktop 1440px và menu mobile 375px; kiểm tra active state, toàn bộ link hiện có, thu gọn/mở rộng và đổi vai trò. Không sửa backend, routing hoặc dữ liệu; không commit/push.

## Khôi phục mục Nhà cung cấp — 17/11/2026

- Theo phản hồi tiếp theo của dev, thêm lại **Nhà cung cấp** vào nhóm **Danh mục**, ngay sau **Mặt hàng & tồn kho**; dùng route `/kho/nha-cung-cap` hiện có và icon `Truck`. Thứ tự các mục khác giữ nguyên.
- Chỉ cập nhật `navigation.js`, ánh xạ icon QLK trong `Sidebar.jsx` và danh sách menu mong đợi trong `tests/browser/navigation.spec.js`; không sửa trang Nhà cung cấp, backend hoặc cấu hình routing.
- Kiểm chứng: **9/9 test logic điều hướng**, **2/2 test trình duyệt QLK desktop/mobile**, lint và build đều đạt. Test trình duyệt dùng API fixture, không ghi database.

## Giao diện sidebar theo ảnh tham chiếu — 17/11/2026

- Giữ nguyên toàn bộ tab, nhóm, thứ tự, route và quyền hiện tại của ba vai trò. `navigation.js` có SHA-256 giống hệt bản ngay trước lượt chỉnh này; **Nhà cung cấp** vẫn nằm sau **Mặt hàng & tồn kho** trong nhóm Danh mục của QLK.
- `frontend/src/layouts/Sidebar.jsx`: tái sử dụng logo và ảnh `slide-02-touring.webp` có sẵn cho sidebar. Ảnh mang tính trang trí, nằm sau các mục menu trong vùng cuộn; không thêm số đếm giả từ ảnh tham chiếu. Giữ các hành vi điều hướng, thu gọn và đăng xuất hiện có.
- `frontend/src/layouts/Sidebar.module.css`: nền nâu tối, chữ sáng, active màu cam, hover/focus, logo phía trên và ảnh xe hoàng hôn phía dưới. Màu cam được điều chỉnh để chữ trắng đạt tương phản **4,64:1**. CSS chỉ tác động sidebar; menu dài và màn hình thấp vẫn cuộn được tới Hồ sơ/Đăng xuất; ảnh không che các nhóm. Sidebar mobile giữ cách mở/đóng hiện tại.
- Không sửa Header, nội dung trang, cấu hình menu/routing, API, backend, database hoặc dependency. Trong lượt này chỉ thay hai file sidebar và bổ sung ghi chú này; các thay đổi đã có trước được giữ nguyên. Không commit/push.

### Kiểm chứng lượt sidebar

- `node --test tests/navigation.test.js`: **9/9 pass**.
- Playwright `sidebar.spec.js` và `navigation.spec.js`, loại hai test QTV lỗi sẵn bên dưới: **13/13 pass**; kiểm tra mọi link hiện có của cả ba vai trò, active ở trang chi tiết, hover, bàn phím, thu gọn, mobile/tablet, đổi vai trò và hủy đăng xuất. Đây là kiểm tra bằng API fixture, không ghi database ứng dụng.
- Rà riêng bằng Chrome ở **1440×900, 1024×600, 375×667** cho cả ba vai trò: **9/9 trường hợp đạt**; đối chiếu toàn bộ đường dẫn và thứ tự menu, ảnh/logo tải được, tương phản active, focus bàn phím, cuộn tới mục cuối và không tràn ngang. Đã xem ảnh desktop/mobile và màn hình thấp.
- `npm run lint`, `npm run build`: đạt sau chỉnh bố cục cuối.
- So sánh pixel ảnh QLK/NV 1440px trước/sau: **0 pixel thay đổi ngoài vùng sidebar**; ảnh giữ nguyên kích thước. Phép so sánh dùng bộ đọc PNG có sẵn của Playwright sau khi Python cục bộ không có Pillow; không cài thêm thư viện.
- Design skill lint: **0 fail, 2 warning** cho shadow của sidebar mobile đang nổi lên trên trang; giữ vì đây là overlay thật. Scrim trung tính chỉ áp dụng trên ảnh, theo ngoại lệ của skill và ảnh tham chiếu; không thêm gradient cho nút hoặc nền trang.
- Trước khi sửa, chạy toàn bộ hai file browser: **13 pass, 2 fail**. Hai test `quan_tri_vien: sidebar and direct URL permissions` (1440/375px) bị timeout tại `navigation.spec.js:48`: menu tài khoản hiện có nhãn **Hồ sơ**, test vẫn tìm **Hồ sơ & đổi mật khẩu**. Không sửa Header/test ngoài phạm vi này. Kiểm tra riêng QTV vẫn xác nhận đủ ba tab và điều hướng desktop/mobile.

## Sidebar trọn chiều cao và bỏ thu gọn — 17/11/2026

- `frontend/src/layouts/Sidebar.jsx`: gỡ nút thu gọn, hai icon PanelLeft và state collapsed; giữ nguyên logo, ảnh, các tab và thao tác đăng xuất.
- `frontend/src/layouts/Sidebar.module.css`: trên desktop, sidebar bắt đầu ở y=0 và cao `100dvh`; bỏ CSS của trạng thái thu gọn. Các quy tắc tích hợp layout được giới hạn bằng class CSS Module riêng: sidebar ở cột trái xuyên hai hàng, header và nội dung ở cột phải. Menu dài vẫn cuộn riêng bên trong sidebar.
- `frontend/src/layouts/MainLayout.jsx`: chỉ thêm class tích hợp sidebar cho layout QLK/NV. Giữ nội dung và hành vi Header, các trang và layout QTV hiện có; QTV đã có sidebar trọn chiều cao từ trước. Trên mobile, giữ nút mở/đóng menu ở Header và sidebar dưới Header để nút đóng luôn truy cập được.
- `frontend/tests/browser/sidebar.spec.js`: thay các kiểm tra thu gọn bằng yêu cầu mới (không còn nút, sidebar trọn chiều cao, header/main không bị che), giữ kiểm tra hover, bàn phím, điều hướng, mobile/tablet, reduced motion và hủy đăng xuất.
- Kiểm chứng: **9/9 test logic điều hướng**, **13/13 test browser được chọn**, lint/build đều đạt. Bộ browser vẫn loại hai test QTV lỗi nhãn Hồ sơ có sẵn đã nêu trên; không tuyên bố toàn bộ browser suite đạt. Đã xem ảnh QLK/NV desktop sau sửa; các test kiểm tra chiều cao sidebar của cả ba vai trò, màn hình 1024/1440px và menu mobile 375/768px.
- `navigation.js` có SHA-256 giống bản trước lượt này: không đổi bất kỳ tab, nhóm, thứ tự, route hoặc quyền nào; **Nhà cung cấp** giữ nguyên. Không sửa backend, database hoặc dependency; không commit/push.

## Kết nối frontend với backend thật — 17/11/2026

- Frontend đã dùng Axios/TanStack Query với API thật qua Vite proxy: `http://localhost:5173/api/v1` chuyển tới backend cổng 8000. Không thay bằng mock hoặc sửa logic frontend trong lượt kết nối này.
- Chẩn đoán ban đầu: DB `xbike_audit_demo` lưu `YeuCauSanXuat.loai_yeu_cau` và CHECK constraint cũ `dap_ung`/`cho_kho`; backend và bootstrap hiện dùng `xuat_giao`/`nhap_kho`. Validation đầu ra gây 500 ở yêu cầu, nhu cầu bổ sung, chứng từ hoàn thành và các số liệu sản xuất trên Tổng quan.
- Dev đã xác nhận tạo database demo riêng **`xbike_ui_demo_v4_20261117`**, giữ DB cũ. Đã kiểm tra tên DB chưa tồn tại, tạo DB mới, xác nhận trống rồi lần lượt nạp nguyên bản `infra/postgres/init.sql` và `seed.sql`. Không reset DB, xóa volume, chạy migration hoặc seed lại DB đã có dữ liệu.
- File cấu hình sửa trong lượt này: **`backend/app/config/config.yml`**, chỉ chuyển tên database sang DB demo mới; giữ các cấu hình còn lại. Không sửa source nghiệp vụ, ORM hoặc hợp đồng API.
- Đã dừng các cây tiến trình Uvicorn chạy trùng thuộc đúng project sau khi xác minh đường dẫn/command line; giữ một cây backend mới với cấu hình đã cập nhật. Frontend hiện có vẫn chạy, PostgreSQL không bị dừng. Các dịch vụ đang sẵn sàng tại frontend `http://localhost:5173` và Swagger `http://localhost:8000/docs`.

### Kiểm chứng dữ liệu thật

Chạy Chrome trực tiếp vào frontend cổng 5173, đăng nhập tài khoản demo QLK `quan_ly_kho`, đi qua proxy và FastAPI/PostgreSQL thật; **không cài API fixture hoặc chặn request bằng mock**.

| Màn hình | Kết quả |
| --- | --- |
| Tổng quan | Các request 200; thống kê đã gửi 1, đang thực hiện 2, chờ bổ sung 1 |
| Mặt hàng & tồn kho | 200; 14 bản ghi API và 14 dòng hiển thị |
| Nhà cung cấp | 200; 2 bản ghi API và 2 dòng hiển thị |
| BOM | 200; 5 bản ghi API và 5 dòng hiển thị |
| Phiếu nhập | 200; 2 bản ghi API và 2 dòng hiển thị |
| Nhu cầu bổ sung linh kiện | 200; hiển thị bảng tổng hợp và yêu cầu thiếu |
| Yêu cầu sản xuất | 200; 8 bản ghi API và 8 dòng hiển thị |
| Phiếu xuất | 200; 4 bản ghi API và 4 dòng hiển thị |
| Chứng từ hoàn thành | 200; 2 bản ghi API và 2 dòng hiển thị |
| Nhập – xuất – tồn | Bấm Xem báo cáo tháng 11/2026: 200; 14 mặt hàng, đơn vị có dấu |
| Biến động kho | 200; 20 dòng trên trang đầu; DB có 33 giao dịch kho |
| Lịch sử thao tác | 200; 20 dòng trên trang đầu |

- Kết quả cuối: **12/12 màn đọc dữ liệu đạt**, không có request API 4xx/5xx hoặc lỗi JavaScript trong phiên kiểm chứng cuối. Đã xem ảnh Tổng quan, Yêu cầu sản xuất và báo cáo thực tế trên Chrome.
- Lượt kiểm chứng chỉ đăng nhập và đọc dữ liệu; đăng nhập có ghi lịch sử và middleware có đếm lưu lượng theo logic hiện có. Không tạo/sửa/xóa hoặc ghi sổ chứng từ để thử trên DB ứng dụng. Kết quả này không xác nhận các luồng ghi nghiệp vụ hoặc toàn bộ E2E hệ thống.
- Không chạy lại toàn bộ unit/lint/build vì không sửa source frontend/backend; cấu hình mới đã được xác nhận qua startup thật và request thật. Không commit/push.

### Cách mở kiểm tra

Mở `http://localhost:5173`, đăng nhập `quan_ly_kho` với mật khẩu demo ghi trong `infra/postgres/seed.sql`. Nếu trang đã mở từ trước, tải lại bằng Ctrl+F5 để bỏ cache giao diện/dữ liệu cũ. Không cần chạy lại seed khi khởi động lại ứng dụng.

## Bộ lọc ngày dd/mm/yyyy trên mọi tab — 17/11/2026

- Phạm vi: hai trường **Từ ngày** (`tu_ngay`) và **Đến ngày** (`den_ngay`) trên mọi màn có bộ lọc này, cho cả QTV/QLK/NV. Giữ nguyên các ô ngày khác như Ngày nhập, Hạn hoàn thành và định dạng ngày trong bảng.
- `frontend/src/components/Field.jsx`: chọn control lọc ngày chung chỉ khi tên trường là `tu_ngay`/`den_ngay` và kiểu là `date`; không đổi hành vi các field khác.
- `frontend/src/components/DateFilterInput.jsx` (mới): ô nhập/placeholder cố định `dd/mm/yyyy`, nút mở lịch gốc của trình duyệt, đồng bộ chọn lịch và xóa lọc. Ngày đang nhập dở giữ nguyên để tiếp tục sửa; ngày không tồn tại bị chặn bằng validity của form.
- `frontend/src/components/DateFilterInput.module.css` (mới): chỉ bố trí icon lịch và ô nhập trong control này; không đổi global CSS hoặc theme.
- `frontend/src/components/dateFilterValue.js` (mới): chuyển đổi hai chiều ngày/tháng/năm với ISO, kiểm tra ngày thực và năm nhuận; không chuyển múi giờ. Giá trị gửi API vẫn là `yyyy-mm-dd`, giữ kiểm tra khoảng ngày hiện có.
- `frontend/tests/date-filter-value.test.js` (mới): định dạng, dữ liệu nhập dở, ngày sai, năm nhuận và biên năm; `frontend/tests/browser/date-filters.spec.js` (mới): mười màn ở các vai trò, browser locale en-US, request ISO, ngày sai/khoảng đảo ngược, xóa lọc, lịch và responsive. Hai route Điều chỉnh/Ticket chỉ được kiểm tra trực tiếp vì đã có từ trước; không thêm lại menu.
- Không thêm dependency; không sửa API, backend, schema, database hoặc nghiệp vụ. Không commit/push.

### Kết quả kiểm chứng ngày

| Kiểm tra | Kết quả |
| --- | --- |
| Browser: `date-filters.spec.js` + `warehouse-ui.spec.js` | **25 pass**; gồm 12 test bộ lọc ngày và 13 hồi quy QLK |
| Unit: `date-filter-value.test.js` + `uc43-audit-history.test.js` | **24 pass** |
| Lint/build | Đạt |
| Chrome với backend thật, lọc phiếu nhập 01/11/2026–30/11/2026 | Hiện dd/mm/yyyy; query `tu_ngay=2026-11-01&den_ngay=2026-11-30`, **200**, 2 dòng; không lỗi JavaScript |
| Rà ảnh | Đã xem ô trống/ô có giá trị, popup lịch Chrome và mobile 375px; không tràn ngang |
| `npm test` toàn frontend | **288 pass, 4 fail, 0 skip**; bốn lỗi độc lập với phần ngày, chi tiết bên dưới |

Bốn test còn dùng cấu trúc/nhãn sidebar trước các yêu cầu chỉnh menu gần đây: `uc27-shortage-page.test.js:132`, `uc33-completion-list.test.js:223` tìm nhóm cũ; `uc41-inventory-report.test.js:63` kỳ vọng nhãn “Báo cáo nhập – xuất – tồn”; `uc42-stock-movements.test.js:128` kỳ vọng “Lịch sử biến động kho”. Tác vụ ngày không sửa `navigation.js` và không sửa kỳ vọng bốn test này để làm xanh suite. Kết quả browser dùng API fixture, trừ lượt đọc phiếu nhập thật ghi riêng ở trên; chưa kiểm tra trên Firefox/Safari.
