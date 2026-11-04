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

## Đồng bộ data model v3.1

Bốn màn `/quan-ly/*` dùng quan hệ từ `xbike_mrp_data_model_v3.1_mermaid.md` anh đã cung cấp, kết hợp tiền integer VND và nghiệp vụ của [API contract v3](https://drive.google.com/file/d/1yznre1rfIK6IIp8UTWb_D842r8vrNTIE/view). Phạm vi vẫn là demo trong bộ nhớ, chưa kết nối API thật.

| Màn | Thay đổi theo mô hình |
|---|---|
| Nhập kho | Chọn nhà cung cấp bằng ID; tách ngày nhập và thời điểm tạo; người lập từ quản lý demo; nhận NVL/linh kiện, không nhận thành phẩm/bán thành phẩm |
| Yêu cầu | Chọn mặt hàng, số lượng và người được giao theo ID; cho lưu nháp chưa giao người; lưu nháp → tính kế hoạch → gửi để sinh cây lệnh |
| Lệnh | Chọn lệnh đã sinh, xem BOM/phiên bản, lệnh cha, nhu cầu trực tiếp; giao nhân viên và gửi. Không tạo lệnh thủ công hoặc sửa số lượng/BOM |
| Duyệt xuất | Hai loại `xuat_vat_tu`/`xuat_thanh_pham`, nguồn là lệnh/yêu cầu có ID; quản lý lập và duyệt; giá null trước duyệt và chốt từ giá mặt hàng lúc duyệt |

Kiểu dữ liệu demo dùng camelCase. `supplierId` tương ứng `ncc_id`, `creatorId` tương ứng `nhan_vien_id` của chứng từ, `assigneeId` là người được giao, `bomId`/`parentOrderId` tương ứng `bom_id`/`lenh_san_xuat_cha_id`. `Item.stock` và `stockUpdatedAt` tương ứng `MatHang.so_luong_ton` và `ton_kho_updated_at`; không có kho số dư riêng. ID chuỗi trong demo là khóa nội bộ; API thật dùng ID integer, cần ánh xạ khi tích hợp.

## Thử các luồng

1. **Nhập kho:** hai dòng ban đầu là 20 khung và 12 vành. Tổng tiền tính từ dòng: 9.000.000 + 2.160.000 = 11.160.000 đồng. Lưu nháp giữ nguyên tồn. Xác nhận có hộp thoại, cộng tồn đúng một lần và khóa phiếu. Có thể thêm/xóa dòng, chọn vật tư, thay số lượng/giá hoặc tạo phiếu mới.
2. **Yêu cầu:** Mountain Pro cần 10 xe, tồn 3 nên lắp thêm 7; cần 14 cụm bánh, có 4 nên làm thêm 10. Lưu nháp, tính kế hoạch rồi gửi. Kế hoạch demo có hiệu lực 10 phút; dữ liệu thay đổi thì cần tính lại. Khi gửi, cây lệnh được sinh và đóng băng BOM/nhu cầu. Thiếu vật tư đưa yêu cầu vào `cho_bo_sung_vat_tu`, vẫn giữ cây lệnh.
3. **Lệnh:** chọn lệnh theo yêu cầu, xem đầu ra, số lượng cố định, BOM/phiên bản và lệnh cha. Lưu người thực hiện rồi gửi lệnh. Thiếu vật tư không chặn gửi; gửi không thay đổi tồn. Tạo mới lệnh thủ công đã được bỏ theo §9 contract v3.
4. **Duyệt xuất:** `PX-202611-000026` xuất 7 khung và 7 phuộc; giá hiển thị “Chưa chốt” trước duyệt. `PX-202611-000029` cần 360 nan hoa nhưng có 300; `PX-202611-000028` bị chặn vì yêu cầu đang chờ bổ sung. Nhập thêm 60 nan hoa giúp phiếu cấp nan hoa đủ tồn, nhưng yêu cầu còn thiếu đầu ra cụm bánh nên chưa tự thoát chờ bổ sung. Từ chối cần lý do, giữ tồn. Duyệt kiểm tra nguồn, nhu cầu còn lại, hoạt động mặt hàng và tồn, rồi chốt giá/lưu số dư một lần.

Tồn kho dùng chung giữa bốn màn. Có thể nhập thêm nan hoa rồi quay lại phiếu thiếu để thấy khả năng duyệt thay đổi. Nút đặt lại cạnh nút giao diện sáng/tối có hộp thoại xác nhận. Reload tab cũng đưa dữ liệu nghiệp vụ về ban đầu; lựa chọn sáng/tối được giữ riêng trong localStorage.

## Cấu trúc và vai trò

Trong `src/features/management/`:

| File | Vai trò |
|---|---|
| `ManagerLayout.tsx` | Khung quản lý, điều hướng desktop/mobile, theme, toast, tải dữ liệu và reset demo |
| `ReceivingScreen.tsx` | Form nhập kho nhiều dòng, lưu nháp, xác nhận và tóm tắt tồn |
| `RequestScreen.tsx` | Form yêu cầu, tính nhu cầu hai cấp và chuyển sang tạo lệnh |
| `ProductionScreen.tsx` | Cây lệnh đã sinh, BOM/cha-con, nhu cầu trực tiếp, giao và gửi lệnh |
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

Lần đồng bộ v3.1 này chỉ sửa `README.md` và 12 file trong `src/features/management/`: bốn `*Screen.tsx`, `ManagerLayout.tsx`, `types.ts`, `demo-data.ts`, `planning.ts`, `demo-engine.ts`, `demo-engine.test.ts`, `demo-api.ts`, cùng `management.css`. Khung, bảng và adapter dùng các quan hệ/trạng thái mới; CSS chỉ tăng độ rộng cuộn của bảng phiếu xuất để thêm giá chốt/thành tiền. Không sửa dependency, routes, backend, SQL hoặc database.

## Kiểm tra

```powershell
npm.cmd run typecheck
npm.cmd run build
npm.cmd run lint
npm.cmd run test:demo
```

Bộ test demo dùng tính năng chạy TypeScript của Node; môi trường đã kiểm tra là Node 24. App build không cần test runner bổ sung.

Kiểm chứng cập nhật v3.1 ngày 04/11/2026: **17/17 test logic PASS**, typecheck và production build PASS; ESLint 0 lỗi, 2 cảnh báo `any` có sẵn ở `ReportsPage.tsx`. Chromium kiểm tra bốn màn ở 1440/768/390px, không tràn ngang toàn trang hoặc lỗi runtime; kiểm tra lưu/hoàn tất nhập, giá xuất null → chốt khi duyệt, chặn thiếu tồn/nguồn chờ bổ sung, từ chối có lý do, nháp chưa giao người, tính/gửi kế hoạch sinh cây lệnh, phân công/gửi lệnh và menu mobile bằng Escape. Ảnh sáng/tối và artifact QA tại `.venv/ui-v31-review/` ở root, không đưa vào source.

Các test trước đây về tạo lệnh thủ công được thay bằng test sinh cây lệnh khi gửi yêu cầu, theo §8–9 contract v3. Các kiểm tra dự thảo mới gồm BOM chưa có, phiên bản BOM, mặt hàng ngừng hoạt động, token hết hạn/thay đổi, giới hạn lượng đã cấp, rollback mô phỏng và retry ghi sổ.

Màu và bố cục theo hướng bảng điều phối sáng, trung tính, token tối tương ứng; nhận diện là khung xe xBike và nhánh BOM xe → cụm bánh → vật tư. Không có KPI hoặc chứng nhận backend giả. Form có required/validation, dialog native, focus bàn phím, tab BOM hỗ trợ phím mũi tên, menu hỗ trợ Escape và giữ focus; bảng rộng cuộn trong khung, không kéo ngang cả trang.

Kết quả và giới hạn kiểm tra được ghi cùng phần bàn giao. Công cụ `design-taste-frontend` chọn style/đo browser tự động không chạy được vì bản skill thiếu thư mục `scripts/lib/`; đã dùng Chromium headless thay thế để kiểm tra thao tác và chụp cả bốn màn ở 1440, 768 và 390px. Static style lint chạy được; shadow được giữ riêng cho dialog/toast, dấu gạch ngang dài chỉ dùng để biểu diễn dữ liệu thiếu. Boundary checker chưa có cấu hình `clean-architecture`; import đã được rà theo vai trò, không có API thật trong component.

## Giới hạn demo và tích hợp sau này

- Dữ liệu mẫu không lấy từ database, không có xác thực/phân quyền thực tế. Tên quản lý/nhân viên/nhà cung cấp, mã chứng từ và BOM đều là dữ liệu minh họa từ wireframe hoặc mở rộng để test trạng thái.
- Mỗi model mẫu có BOM riêng và phiên bản; định mức vẫn là dữ liệu minh họa hai cấp xe → cụm bánh. Không phải bộ lập kế hoạch tổng quát cho mọi cây BOM.
- Việc kiểm tồn/không ghi dở/retry được mô phỏng trong một engine TypeScript. Không thay thế transaction, khóa, ETag, ledger hoặc audit backend.
- Token kế hoạch demo chỉ bảo vệ phiên thao tác trong bộ nhớ; không phải token có chữ ký của backend. Khi tích hợp phải dùng endpoint, ETag, transaction, ledger và audit thật.
- Chưa có màn hoàn thành sản xuất trong bốn màn này; không dùng nhập kho vật tư để cộng đầu ra cụm bánh hoặc xe. Luồng sản xuất nhiều đợt cần nối màn/chức năng hoàn thành riêng khi tích hợp backend.
- Lint toàn frontend hiện có hai cảnh báo `any` cũ ở `ReportsPage.tsx`, ngoài phạm vi bốn màn này.
- Khi rollback UI, gỡ các route `/quan-ly`, chuyển trang gốc lại `/reports` và bỏ feature mới. Không có migration hoặc dữ liệu database cần hoàn tác.
