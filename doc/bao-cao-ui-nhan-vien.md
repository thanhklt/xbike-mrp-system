# Báo cáo bàn giao UI Nhân viên — xBike MRP

Ngày báo cáo: **12/11/2026**. Nhánh bàn giao: **`feature/UI-nhanvien`**.

## 1. Phạm vi và căn cứ

- Căn cứ: [đặc tả UI Nhân viên](./dac-ta-yeu-cau-ui-nhan-vien.md), [mẫu HTML và ảnh](./ui-nhan-vien-preview/), [quy tắc frontend](./FRONTEND_RULES.md), `AGENTS.md` và quyết định của dev: **đổi giao diện theo mẫu, giữ nghiệp vụ/quyền/API hiện tại, ghi riêng khác biệt để duyệt**.
- Theme nhân viên dùng màu Admin hiện có; bố cục tham chiếu mẫu preview. Giữ các đường dẫn và luồng nghiệp vụ cũ, gồm `/nv/phieu`, `/nv/xuat-nvl`, `/nv/xuat-tp`, nháp → gửi duyệt, trả về nháp, kiểm tra ETag, trạng thái bận và báo lỗi.
- Không thay đổi backend, endpoint, schema, bootstrap SQL, dependency hoặc dữ liệu. Diff `backend/Dockerfile` đã tồn tại trước đợt này và không thuộc bàn giao.

## 2. Phần đã triển khai

| Khu vực | Kết quả |
| --- | --- |
| Khung nhân viên | Sidebar sáu mục, ảnh xe đạp, breadcrumb, module pill, menu hồ sơ/đăng xuất, drawer mobile; theme chỉ áp dụng trong nhân viên và dialog tương ứng. |
| `/nv` | Bốn KPI đếm từ `meta.total`, yêu cầu được giao, việc tiếp theo, cảnh báo vật tư theo trạng thái API, tra cứu tồn kho nhanh, chứng từ gần đây và nhãn ngày Việt Nam. |
| `/nv/lenh-sx` | Bốn thẻ lọc theo trạng thái API, thanh tiến độ trên dòng lệnh, chi tiết vật tư và chứng từ liên quan; giữ hành động bắt đầu khi đủ điều kiện. |
| `/nv/yeu-cau` | Danh sách và chi tiết chỉ đọc, ghi chú quyền, tìm mã và lọc trạng thái API. |
| `/nv/hoan-thanh` | Bảng và form theo theme mới; giữ tạo/sửa/xóa nháp, gửi duyệt và trả về nháp theo quyền hiện tại. |
| `/nv/phieu-xuat` | Route tra cứu phiếu xuất liên quan, chỉ đọc; không có quyền tạo hoặc duyệt cho nhân viên. |
| `/nv/ton-kho` | Tra cứu và chi tiết chỉ đọc với SKU, loại hàng và số tồn thực tế; không hiển thị giá hoặc thao tác ghi. |

Các component dùng chung được giữ hành vi cũ cho Admin/Quản lý; thay đổi về bảng, dialog và sidebar nhân viên được giới hạn bằng class/theme. Ảnh quản lý trong mục 4 được kiểm tra để phát hiện thay đổi giao diện ngoài phạm vi.

## 3. Kiểm chứng

| Kiểm tra | Kết quả | Giới hạn |
| --- | --- | --- |
| `npm run lint` | Đạt ở bản hiện tại | ESLint frontend. |
| `npm test` | 46/46 đạt trước thay đổi nhỏ cuối cùng về nhãn ngày dashboard | Không chạy lại unit tests sau nhãn ngày; build và browser hiện tại đã kiểm tra phần này. |
| `npm run build` | Đạt ở bản hiện tại | Vite build 1643 modules. |
| Browser fixture: `employee-ui.spec.js` + `navigation.spec.js` | **18/18 đạt** ở bản hiện tại: 11 ca nhân viên, 7 ca điều hướng ba vai trò | [Log](./ui-nhan-vien-evidence/browser-18-tests.log); fixture không chứng minh API/PostgreSQL thật. |
| `git diff --check` | Đạt | Kiểm tra whitespace của diff được theo dõi. |

Log `test-run-full.log` **122/122** và `test-employee-targeted.log` **10/10** có trước redesign; chúng không được dùng làm bằng chứng hồi quy toàn bộ ở bản bàn giao này.

## 4. Ảnh đã kiểm tra

Ảnh dưới đây chụp từ frontend chạy bằng **API fixture** trong browser test, không phải E2E với database thật.

| Màn hình | Ảnh |
| --- | --- |
| Dashboard desktop | [1440px](./ui-nhan-vien-evidence/dashboard-1440.png) |
| Dashboard mobile | [375px](./ui-nhan-vien-evidence/dashboard-375.png) |
| Yêu cầu sản xuất | [1440px](./ui-nhan-vien-evidence/requests-1440.png) |
| Dialog lệnh sản xuất | [1440px](./ui-nhan-vien-evidence/order-dialog-1440.png) |
| Tra cứu phiếu xuất | [1440px](./ui-nhan-vien-evidence/issues-1440.png) |
| Giao diện Quản lý đối chiếu | [1440px](./ui-nhan-vien-evidence/manager-1440.png) |

## 5. Khác biệt preview và việc còn mở

Các mục sau giữ `[ ]` trong [MISSING.md](./MISSING.md) theo quyết định giữ hợp đồng hiện tại:

| Mã | Khác biệt cần dev quyết định |
| --- | --- |
| FE-MISS-006 | Trường sản phẩm lỗi và ghi chú sản xuất trong chứng từ hoàn thành chưa có trong schema ghi. |
| FE-MISS-007 | Mẫu cho nhân viên tạo phiếu xuất, nhưng backend chỉ cho Quản lý thực hiện. |
| FE-MISS-008 | Mức tồn tối thiểu và nhãn thiếu tồn chưa có dữ liệu nguồn. |
| FE-MISS-009 | Hạn hoàn thành, tìm nhiều trường và nhóm lọc tổng hợp trên lệnh sản xuất chưa có trong API. |
| FE-MISS-010 | Ghi chú xử lý và BOM tổng hợp cấp yêu cầu chưa có trong API đọc. |
| FE-MISS-011 | Nhóm yêu cầu “sẵn sàng xuất/cần sản xuất/chờ duyệt chứng từ” chưa có phép tính và bộ lọc đáng tin cậy. |

Vẫn cần kiểm tra zoom 200% và tương phản đầy đủ; thử quyền bằng hai tài khoản thật, luồng API/PostgreSQL trên môi trường test riêng; và nghiệm thu UI của dev. Các mục này chưa được đánh dấu hoàn tất. Không tự accept, reset/seed database hoặc merge vào `main`.

## 6. File thuộc bàn giao

| Nhóm | File |
| --- | --- |
| Layout/theme | `frontend/src/app/App.css`, `frontend/src/layouts/{MainLayout.jsx,Sidebar.jsx,Sidebar.module.css,navigation.js}`, `frontend/src/assets/images/brand/employee-bicycle.png` |
| Trang và route | `frontend/src/features/dashboard/DashboardPage.jsx`, `frontend/src/features/production/{ProductionPage.jsx,RequestsPage.jsx,CompletionsPage.jsx}`, `frontend/src/features/material-issuing/MaterialIssuingPage.jsx`, `frontend/src/features/materials/MaterialsPage.jsx`, `frontend/src/routes/index.jsx` |
| Component dùng chung | `frontend/src/components/{Collection.jsx,ResourceFields.jsx}` |
| Kiểm thử | `frontend/tests/navigation.test.js`, `frontend/tests/browser/{api-fixture.js,employee-ui.spec.js,navigation.spec.js,workflows.spec.js}` |
| Tài liệu và ảnh | `doc/MISSING.md`, `doc/dac-ta-yeu-cau-ui-nhan-vien.md`, `doc/ui-nhan-vien-preview/*`, `doc/ui-nhan-vien-evidence/*`, báo cáo này |
| Cấu hình design hook | `.impeccable/config.json` — ngoại lệ giá trị `Arial` cho logo XBIKE được đặc tả tại §10.2 |

Các file ngoài phạm vi trong worktree được giữ nguyên, đặc biệt `backend/Dockerfile` và `doc/dac-ta-ui-ux-frontend.md`.
