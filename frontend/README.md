# xBike MRP frontend

React/JavaScript + Vite. Source ứng dụng dùng `.jsx`/`.js`; không còn TypeScript.
Giao diện tiếng Việt theo mẫu HTML, có điều hướng riêng cho Quản trị viên, Quản lý kho và Nhân viên.

## Chạy cục bộ

Chạy các lệnh trong thư mục `frontend/`:

```sh
npm ci
npm run dev
```

Mở `http://localhost:5173`. Đăng nhập bằng tài khoản thật của backend; ứng dụng không có đăng nhập hoặc dữ liệu demo giả.

Mặc định frontend gọi `/api/v1` cùng origin; Vite chuyển tiếp tới `http://localhost:8000`.
Nếu backend ở địa chỉ khác, tạo `.env` theo `.env.example`, đặt `API_PROXY_TARGET` cho địa chỉ backend.
Vite đọc lại cấu hình này khi khởi động. Khi chạy dev, pathname của `VITE_API_BASE_URL` được dùng qua proxy để browser đọc được ETag.

Dockerfile frontend đặt `API_PROXY_TARGET=http://backend:8000`, phù hợp service backend trong Compose hiện có.
Không cần sửa CORS backend để đọc ETag khi dùng proxy. Build production mặc định dùng `/api/v1`; reverse proxy phục vụ production phải chuyển `/api/` tới backend và trả SPA cho các URL frontend.

```sh
npm run build
npm run preview
```

`preview` chỉ xem bản build; nó không khởi động backend hoặc tự tạo proxy API production.
Nếu chủ động dùng API khác origin trong bản production, backend cần expose header ETag; phần sửa backend đó không thuộc tác vụ này.

## Màn hình

| Vai trò       | Khu vực                                                                                                                                                                                                                                      |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Chung         | `/dang-nhap`, `/ho-so`, `/403`, `/404`                                                                                                                                                                                                       |
| Quản trị viên | `/admin`, `/admin/tai-khoan`, `/admin/vai-tro`, `/admin/lich-su`                                                                                                                                                                             |
| Quản lý kho   | `/kho`, `/kho/mat-hang`, `/kho/nha-cung-cap`, `/kho/bom`, `/kho/phieu-nhap`, `/kho/phieu-xuat`, `/kho/yeu-cau`, `/kho/lenh-sx`, `/kho/duyet-hoan-thanh`, `/kho/dieu-chinh`, `/kho/ticket`, `/kho/giao-dich`, `/kho/thong-ke`, `/kho/lich-su` |
| Nhân viên     | `/nv`, `/nv/yeu-cau`, `/nv/lenh-sx`, `/nv/xuat-nvl`, `/nv/xuat-tp`, `/nv/hoan-thanh`, `/nv/phieu`, `/nv/ton-kho`                                                                                                                             |

Các nhóm có chi tiết dùng `/:id`. Nhóm có quyền tạo dùng `/moi`; backend vẫn là nơi quyết định quyền và trạng thái hợp lệ.
Sidebar và kiểm tra đường dẫn dùng chung quy tắc tại `src/features/auth/permissions.js`, dựa trên `ma_vai_tro` từ `/auth/me`: Quản trị viên chỉ thấy khu vực `/admin`, Quản lý chỉ thấy `/kho`, Nhân viên chỉ thấy `/nv`. Mục không có quyền được loại khỏi sidebar; truy cập trực tiếp khu vực vai trò khác chuyển tới `/403`. Hồ sơ và đăng xuất dùng chung cho cả ba vai trò.
Các nút xem/sửa ở cột Thao tác và các form tạo mới mở trong popup chung, thay cho khung chi tiết bên dưới hoặc cạnh danh sách.
Popup hỗ trợ Đóng, Escape, Tab/Shift+Tab, lịch sử Back/Forward và cuộn nội dung riêng trên mobile; đóng popup trả về danh sách.
Hộp xác nhận nghiệp vụ mở phía trên popup chi tiết; hủy xác nhận giữ nguyên chi tiết đang xem.
Nhân viên chỉ xem phiếu xuất; Quản lý kho lập/gửi/duyệt phiếu xuất. Nhân viên lập chứng từ hoàn thành cho lệnh của mình.
Sidebar Nhân viên tập trung vào Tổng quan, Việc được giao, Chứng từ hoàn thành SX và Tra cứu tồn kho, cùng Hồ sơ/Đăng xuất. Yêu cầu phụ trách, Phiếu xuất NVL/BTP, Phiếu xuất thành phẩm và Phiếu của tôi không là mục sidebar riêng; các trang đọc vẫn truy cập được từ liên kết theo công việc. Việc ẩn menu không thay đổi quyền đọc API theo contract v3 §8–11.

Tồn hiện tại đọc từ mặt hàng. Ghi sổ phải qua xác nhận; sửa/action có phiên bản dùng ETag đã tải trong header If-Match. Không tự lấy ETag mới để vượt lỗi dữ liệu cũ, không tự retry thao tác ghi.
Cache tài nguyên được tách theo ID/vai trò người dùng và được xóa khi kết thúc phiên.

Tạo BOM theo API hiện tại đồng thời kích hoạt phiên bản mới và ngừng phiên bản cũ; giao diện yêu cầu xác nhận tác động này.
DELETE mặt hàng là ngừng sử dụng, giữ nguyên số dư/chứng từ; DELETE nhân viên là khóa tài khoản.

## Nút và phần chưa có backend hỗ trợ

| Chức năng                            | Hành vi giao diện                                                            |
| ------------------------------------ | ---------------------------------------------------------------------------- |
| Đặt lại mật khẩu nhân viên bởi Admin | Vô hiệu hóa, chưa có API; đổi mật khẩu chính mình vẫn hoạt động              |
| Sửa tên vai trò                      | Vô hiệu hóa, chỉ có API đọc                                                  |
| Sửa/xóa nhà cung cấp                 | Vô hiệu hóa, chỉ hỗ trợ xem/tạo                                              |
| Tạo ticket thủ công                  | Vô hiệu hóa; ticket chỉ sinh từ lỗi xác nhận điều chỉnh theo nghiệp vụ       |
| Giao dịch kho                        | Màn hình có giải thích, bộ lọc bị vô hiệu hóa do API đọc còn dùng ORM legacy |
| Thống kê nhập–xuất–tồn               | Màn hình có bộ chọn kỳ, nút chạy vô hiệu hóa vì chưa có router báo cáo       |
| Bộ lọc lịch sử chuyên sâu            | Chưa có API hiện hành hỗ trợ; hiện chỉ tìm kiếm/sắp xếp/phân trang           |

Lịch sử dùng adapter riêng cho `/audit` và envelope/query legacy đang có; không tự gọi đường dẫn `/lich_su_thao_tac` chưa triển khai. Admin không hiển thị snapshot trước/sau.

Điều chỉnh kho dùng một bước Xác nhận. Form chọn phiếu nhập đã hoàn tất, nhập ID giao dịch nhập gốc và số lượng đúng.
**Chưa tự chọn giao dịch gốc theo dòng phiếu nhập** vì API đọc sổ kho chưa đồng bộ; không lấy ID dòng phiếu nhập thay cho ID giao dịch.
Nếu backend xác nhận đã lưu ticket sau lỗi thiếu tồn, thông báo cung cấp liên kết tới ticket đó.

## Kiểm thử

```sh
npm run lint
npm test
npm run test:browser
npm run build
```

- `npm test`: dùng Node test runner để kiểm tra chính sách quyền, ETag, envelope, query, múi giờ và HTTP client.
- `npm run test:browser`: Playwright chạy headless Google Chrome đã cài, khởi động Vite trên cổng 5174. API được chặn/mô phỏng tại biên HTTP; không ghi database ứng dụng. Cổng 5174 cần trống.
- Nếu máy chưa cài Google Chrome, cài Chrome theo phương thức của dev trước khi chạy browser tests. Không tải browser tự động khi cài dependency.
- Các test kiểm tra toàn bộ nhóm màn hình, form, xác nhận/hủy, chống gửi lặp, lỗi quyền/validation/ETag/phiên, ticket, desktop và mobile. Ảnh kiểm chứng nằm tại `test-results/` sau khi chạy.
- Dữ liệu trong `tests/browser/api-fixture.js` chỉ dùng kiểm thử, không được ứng dụng import.

Kết quả browser với API mô phỏng **không thay thế E2E với FastAPI/PostgreSQL**. Không khẳng định ghi sổ/database hoặc toàn bộ backend đã đạt kiểm thử từ kết quả frontend này.

## Cấu trúc

- `src/app`, `src/main.jsx`: provider, Router và khởi tạo.
- `src/components`: component giao diện dùng chung và hộp xác nhận.
- `src/features`: màn hình theo chức năng; quyền frontend tại `features/auth/permissions.js`.
- `src/layouts`, `src/routes`: điều hướng và giới hạn route theo vai trò.
- `src/lib/api`: client, hợp đồng response/query, endpoint và hooks dữ liệu.
- `tests`: kiểm thử logic và trình duyệt.

Không chỉnh database, seed hoặc bootstrap trong tác vụ frontend. Nếu cần hoàn tác, review và hoàn tác riêng các thay đổi frontend; không reset dữ liệu để chạy phiên bản cũ.
