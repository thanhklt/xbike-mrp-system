# xBike MRP — Bốn màn quản lý của Bảo

Giao diện tương tác bằng **React 18, TypeScript, Vite, React Router v6, TanStack Query, Axios và Lucide React**. CSS và token sáng/tối được đặt riêng trong feature `management`.

Phạm vi đã được xác nhận: bốn màn quản lý, dữ liệu demo trong bộ nhớ. Dựa trên `README_wireframe.txt`, `xbike_webpage_ui.txt`, HTML và ảnh trong thư mục wireframe người dùng cung cấp. File `xbike_webpage_ui.txt` liệt kê vai trò/phân công; không quy định màu hoặc token thiết kế.

## Chạy trên Windows

```powershell
cd D:\xbike-mrp-system\frontend
npm.cmd install
npm.cmd run dev
```

Mở http://localhost:5173. Trang gốc chuyển đến màn nhập kho. Không cần chạy backend hoặc đăng nhập cho prototype này.

| Màn hình | Đường dẫn |
|---|---|
| Phiếu nhập nguyên vật liệu | `/quan-ly/nhap-kho` |
| Yêu cầu thành phẩm | `/quan-ly/yeu-cau-thanh-pham` |
| Lệnh sản xuất | `/quan-ly/lenh-san-xuat` |
| Duyệt phiếu xuất | `/quan-ly/duyet-phieu-xuat` |

Các route cũ vẫn còn, chẳng hạn `/reports`, `/receiving`, `/production`, `/login`. Đăng nhập cũ là giao diện mock sẵn có, không phải luồng xác thực của prototype quản lý mới.

## Thử các luồng

1. **Nhập kho:** hai dòng ban đầu là 20 khung và 12 vành. Tổng tiền tính từ dòng: 9.000.000 + 2.160.000 = 11.160.000 đồng. Lưu nháp giữ nguyên tồn. Xác nhận có hộp thoại, cộng tồn đúng một lần và khóa phiếu. Có thể thêm/xóa dòng, chọn vật tư, thay số lượng/giá hoặc tạo phiếu mới.
2. **Yêu cầu:** Mountain Pro cần 10 xe, tồn 3 nên lắp thêm 7. Cần 14 cụm bánh, có 4 nên làm thêm 10. BOM cụm bánh cần 10 vành, 10 moay-ơ, 360 nan hoa. Tính lại nhu cầu dùng tồn trong phiên hiện tại. Tạo yêu cầu không đổi tồn; liên kết “Tạo lệnh” mang theo đúng yêu cầu vừa tạo.
3. **Lệnh:** chọn yêu cầu và lệnh lắp xe/cụm bánh, số lượng, nhân viên. Có thể tạo lệnh dù vật tư thiếu. Các lệnh cùng loại không vượt phần nhu cầu của yêu cầu. Tạo lệnh không đổi tồn.
4. **Duyệt xuất:** tìm/lọc hàng chờ, chọn phiếu, đối chiếu từng dòng. PX-2026-026 ban đầu xuất 7 khung và 7 phuộc. PX-2026-029 cần 720 nan hoa nhưng chỉ có 650, nên nút duyệt bị khóa. Từ chối phải nhập lý do và không trừ tồn. Duyệt thành công lưu số dư trước/sau, khóa thao tác và không trừ lại khi retry.

Tồn kho dùng chung giữa bốn màn. Có thể nhập thêm nan hoa rồi quay lại phiếu thiếu để thấy khả năng duyệt thay đổi. Nút đặt lại cạnh nút giao diện sáng/tối có hộp thoại xác nhận. Reload tab cũng đưa dữ liệu nghiệp vụ về ban đầu; lựa chọn sáng/tối được giữ riêng trong localStorage.

## Cấu trúc và vai trò

Trong `src/features/management/`:

| File | Vai trò |
|---|---|
| `ManagerLayout.tsx` | Khung quản lý, điều hướng desktop/mobile, theme, toast, tải dữ liệu và reset demo |
| `ReceivingScreen.tsx` | Form nhập kho nhiều dòng, lưu nháp, xác nhận và tóm tắt tồn |
| `RequestScreen.tsx` | Form yêu cầu, tính nhu cầu hai cấp và chuyển sang tạo lệnh |
| `ProductionScreen.tsx` | Form lệnh xe/cụm bánh, định mức, người thực hiện và lệnh vừa tạo |
| `ApprovalScreen.tsx` | Hàng chờ/chi tiết phiếu, tìm/lọc, duyệt và từ chối có lý do |
| `components.tsx` | Field, panel, badge, bảng định mức, lỗi và dialog native có focus |
| `management.css` | Token sáng/tối, bố cục và trạng thái responsive; CSS giới hạn trong workspace |
| `types.ts` | Kiểu dữ liệu riêng của bản demo |
| `planning.ts` | Tính BOM, nhu cầu, định dạng số/tiền; không phụ thuộc React |
| `demo-data.ts` | Danh mục, tồn, một yêu cầu và sáu phiếu xuất mẫu |
| `demo-engine.ts` | Thao tác demo và kiểm tra bất biến tồn kho, retry, trạng thái |
| `demo-api.ts` | Axios adapter nội bộ; không gửi request tới backend |
| `workspace-hooks.ts` | Mutation và cập nhật cache TanStack Query |
| `demo-engine.test.ts` | Kiểm tra hành vi nghiệp vụ bằng Node test runner |

Các thay đổi ngoài feature phục vụ wiring/build: `app/query-client.ts`, `App.tsx`, routes, metadata tiếng Việt, package/lockfile. Bảy file màn cũ chỉ được xóa import Lucide không sử dụng đang làm TypeScript build thất bại; không thay đổi chức năng của chúng.

## Kiểm tra

```powershell
npm.cmd run typecheck
npm.cmd run build
npm.cmd run lint
npm.cmd run test:demo
```

Bộ test demo dùng tính năng chạy TypeScript của Node; môi trường đã kiểm tra là Node 24. App build không cần test runner bổ sung.

Kết quả ngày 03/11/2026: **8/8 test logic PASS**, typecheck và production build PASS; ESLint 0 lỗi, 2 cảnh báo cũ ở báo cáo. Kiểm thử Chromium PASS các luồng lưu/xác nhận nhập, liên kết yêu cầu → lệnh xe/cụm bánh, duyệt/từ chối, chặn thiếu tồn, số dư lịch sử sau phát sinh tiếp theo, tìm kiếm rỗng, sáng/tối, menu mobile/Escape, tab BOM bằng phím mũi tên và reset có xác nhận. Không có page error hoặc tràn ngang toàn trang ở 1440/768/390px. Chụp 12 ảnh responsive sáng và bốn ảnh desktop tối; artifact kiểm tra nằm trong `.venv/ui-review/` tại root, không đưa vào source.

Màu và bố cục theo hướng bảng điều phối sáng, trung tính, token tối tương ứng; nhận diện là khung xe xBike và nhánh BOM xe → cụm bánh → vật tư. Không có KPI hoặc chứng nhận backend giả. Form có required/validation, dialog native, focus bàn phím, tab BOM hỗ trợ phím mũi tên, menu hỗ trợ Escape và giữ focus; bảng rộng cuộn trong khung, không kéo ngang cả trang.

Kết quả và giới hạn kiểm tra được ghi cùng phần bàn giao. Công cụ `design-taste-frontend` chọn style/đo browser tự động không chạy được vì bản skill thiếu thư mục `scripts/lib/`; đã dùng Chromium headless thay thế để kiểm tra thao tác và chụp cả bốn màn ở 1440, 768 và 390px. Static style lint chạy được; shadow được giữ riêng cho dialog/toast, dấu gạch ngang dài chỉ dùng để biểu diễn dữ liệu thiếu. Boundary checker chưa có cấu hình `clean-architecture`; import đã được rà theo vai trò, không có API thật trong component.

## Giới hạn demo và tích hợp sau này

- Dữ liệu mẫu không lấy từ database, không có xác thực/phân quyền thực tế. Tên quản lý/nhân viên/nhà cung cấp, mã chứng từ và BOM đều là dữ liệu minh họa từ wireframe hoặc mở rộng để test trạng thái.
- Bốn model mẫu hiện dùng chung một BOM minh họa. Khi nối backend phải dùng BOM/phiên bản và quy tắc cấp lệnh thực tế.
- Việc kiểm tồn/không ghi dở/retry được mô phỏng trong một engine TypeScript. Không thay thế transaction, khóa, ETag, ledger hoặc audit backend.
- Màn tạo lệnh theo wireframe là prototype. Cần thống nhất endpoint thực tế trước khi thay adapter; không tự thêm API backend hoặc đổi nghiệp vụ.
- Lint toàn frontend hiện có hai cảnh báo `any` cũ ở `ReportsPage.tsx`, ngoài phạm vi bốn màn này.
- Khi rollback UI, gỡ các route `/quan-ly`, chuyển trang gốc lại `/reports` và bỏ feature mới. Không có migration hoặc dữ liệu database cần hoàn tác.
