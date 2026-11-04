# Giao diện React/TSX kho và sản xuất

Các route `/mathang`, `/lenhsanxuat`, `/giaodichkho`, `/dieuchinhkho` chạy trong frontend Vite hiện có. Khởi động bằng `npm install` rồi `npm run dev` tại `frontend/`. Không cần backend để xem demo.

Từ giao diện cũ, chọn **Kho & sản xuất · Demo** trong menu Overview để mở bốn màn hình này.

## Phạm vi

- Chuyển prototype HTML sang component React và state TypeScript. Giữ prototype tại `frontend/prototypes/` để đối chiếu, không nhúng HTML qua iframe hoặc `dangerouslySetInnerHTML`.
- Bám `C:\Users\binhb\Downloads\DESIGN.md` và `api_contract_v3.md`: IBM Plex Sans, nền sáng, header navy, bố cục bảng, giao diện tiếng Việt; áp dụng taste-skill, Impeccable và UI-UX Pro Max.
- Giữ nguyên các route cũ. CSS mới giới hạn trong `.op-root`; tái sử dụng `Button` và React Router. Font được Vite đóng gói từ tài sản prototype sẵn có, kèm giấy phép OFL tại đó.
- Bộ lọc, phân trang và ID chi tiết ở query string; mở/đóng chi tiết giữ bộ lọc. Điều hướng trình duyệt và tải lại URL hoạt động.
- Có tìm kiếm, bộ lọc bổ sung, phân trang, sắp xếp, modal native với focus trap/Escape, lỗi biểu mẫu, trạng thái rỗng/tải/lỗi/412 và menu mobile.
- Mặt hàng: thêm/sửa, ngừng/kích hoạt lại; khóa trường đã tham chiếu; không sửa tồn trực tiếp.
- Lệnh: giao người, gửi, bắt đầu, hủy theo điều kiện; thao tác bị khóa có lý do. Không tạo thủ công hoặc hoàn tất trực tiếp.
- Sổ kho: chỉ đọc, truy vết chứng từ, lượng nhập hiệu lực và phiếu điều chỉnh đã xác nhận.
- Điều chỉnh: thêm/sửa/xóa nháp; xem trước chênh lệch và tồn trước/sau; xác nhận toàn bộ hoặc giữ nguyên ledger khi thất bại, tạo ticket demo; không sửa/thử lại phiếu lỗi.

## Tổ chức

| File | Trách nhiệm |
| --- | --- |
| `Operations.tsx` | Layout và danh sách bốn route, bộ lọc, phân trang |
| `Detail.tsx` | Chi tiết, biểu mẫu và xác nhận thao tác |
| `shared.tsx` | State demo, lưu phiên, modal, bảng, trường nhập |
| `model.ts` | Kiểu dữ liệu, tính tồn/hiệu lực và quy tắc nghiệp vụ demo |
| `seed.json` | Dữ liệu mẫu chuyển từ prototype đã duyệt |
| `operations.css` | Style giới hạn trong layout mới và responsive |

## Kiểm tra

Chạy trong `frontend/`:

```sh
node scripts/test-operations.mjs
npm run typecheck
npm run lint
npm run build
```

Self-check dùng TypeScript đã có trong dự án, kiểm tra tính nhất quán tồn, quyền ghi, khóa trường tham chiếu, điều kiện lệnh, tính lại chênh lệch và rollback toàn bộ điều chỉnh. Không thêm thư viện test.

Kiểm tra trình duyệt: bốn route ở 1440/1366/768/390px; mở trực tiếp và tải lại; lưu mặt hàng; giữ bộ lọc; lỗi 412 và focus; xác nhận điều chỉnh thành công/thất bại; gửi và bắt đầu lệnh; Q/N/A; menu và Escape. Kiểm tra lại sau thay đổi các luồng này.

## Giới hạn

Đây là UI demo, chưa tích hợp API, JWT, ETag, database hoặc transaction thực. Bộ chọn Q/N/A chỉ mô phỏng vai trò, không phải cơ chế bảo mật. Dữ liệu lưu riêng trong `sessionStorage` với khóa `xbike-react-demo-v1`, không ghi dữ liệu ứng dụng và không dùng lại phiên HTML cũ. Đóng phiên hoặc khôi phục mẫu làm mất thay đổi demo.

`seed.json` và các kiểu demo chứa một số trường phục vụ hiển thị (ví dụ `source`, `ticket_id` liên kết ticket). Không dùng chúng trực tiếp làm DTO API v3. Trước khi tích hợp thật cần ánh xạ response, quyền từ server, lỗi API và giao dịch nguyên tử từ backend. Tìm kiếm sổ kho hiện chỉ lọc dữ liệu mẫu cục bộ.

Snapshot BOM, trạng thái phiếu nhập và nhân viên đang hoạt động chỉ có trong fixture đã biết. Xử lý ticket đầy đủ nằm ngoài phạm vi bốn màn hình. Không tuyên bố E2E backend đã đạt.

Để frontend build được từ checkout, `App.tsx` khởi tạo QueryClient trực tiếp thay cho import tới file thiếu; bảy trang cũ chỉ được bỏ import icon không dùng bị TypeScript chặn build.

## Kết quả kiểm chứng ngày 04/11/2026

- Build production, typecheck và 11 nhóm self-check nghiệp vụ đạt.
- Lint: 0 lỗi; 2 cảnh báo `any` có sẵn trong `ReportsPage.tsx`, chưa sửa ngoài phạm vi.
- Trình duyệt headless: bốn route không tràn ngang ở 1440/1366/768/390px; các luồng CRUD mặt hàng, giữ bộ lọc/phân trang/focus, điều chỉnh thành công và rollback khi lỗi, giao/gửi/bắt đầu lệnh, phân quyền demo, trạng thái lỗi và menu mobile đạt; không có lỗi JavaScript trong các lượt chạy.
- Taste inspector trên trang mặt hàng bản production: không có finding ở bốn kích thước; font xBike Plex tải thành công. Đã xem ảnh desktop/mobile của danh sách và biểu mẫu.
- `npm install --package-lock=false` không đổi dependency khai báo; audit khi cài báo 15 vấn đề trong cây dependency hiện có (14 moderate, 1 high). Chưa chạy `audit fix` hoặc nâng cấp dependency vì ngoài phạm vi tác vụ.
