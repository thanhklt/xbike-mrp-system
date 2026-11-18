# Kế hoạch xử lý missing và E2E UI Nhân viên

Ngày 17/11/2026. Baseline: commit `03fb878`, luồng main v4; đây là kế hoạch, chưa triển khai backend hoặc chạy E2E thật.

## 1. Phạm vi và căn cứ

- Tuân thủ AGENTS.md, FRONTEND_RULES.md; áp dụng skill e2e-testing cho kiểm thử và bằng chứng.
- Nguồn: MISSING.md, báo cáo review trước push, đặc tả Nhân viên, UC-34/37, router/schema phieu_xuat, YeuCauRead và cấu hình Playwright hiện có.
- Giữ UI hiện tại, quyền theo main, tạo nháp trước khi gửi, server quản lý dòng hàng/số lượng/thời gian; không khôi phục lệnh sản xuất hoặc quyền duyệt của NV.
- Kết quả 282 unit và 84 browser trước đó là baseline được ghi nhận; browser dùng fixture, không chứng minh API/DB thật. Không dùng các log 122/10 của UI cũ làm bằng chứng bản này.
- Chỉ lập kế hoạch trong đợt này. Các thay đổi backend/API dưới đây là đề xuất cần duyệt phạm vi; không tự thay schema hoặc DB ứng dụng.

## 2. Thứ tự thực hiện

### P1 — NV-MAIN-005: mở lại phiếu đã tồn tại

Hiện GET danh sách phiếu chỉ dành cho QLK; GET chi tiết cần ID; YeuCauRead không có ID phiếu. Refresh hoặc quay lại yêu cầu làm NV mất đường mở phiếu, tạo lại nhận 409.

Đề xuất tối thiểu: bổ sung tham chiếu phiếu linh kiện/thành phẩm vào response chi tiết yêu cầu mà NV được phép đọc, truy vấn từ quan hệ hiện có; không mở quyền danh sách toàn bộ phiếu và không thêm cột DB. Tên trường, nullability, phạm vi response và điều kiện đọc cần chốt trước triển khai; nếu không phù hợp cấu trúc hiện có thì dùng endpoint lookup riêng theo yêu cầu, không triển khai cả hai.

- Backend: tái sử dụng chính sách phân quyền hiện hành; không lộ tham chiếu vượt phạm vi đọc; tránh N+1 nếu đưa vào danh sách.
- UI RequestsPage/MaterialIssuingPage: có tham chiếu thì mở phiếu; chưa có thì tạo theo điều kiện main. Khi POST bị 409 do người khác vừa tạo, refetch tham chiếu và cho mở phiếu; không tự gửi lại POST.
- Test: chưa có/có nháp/chờ duyệt/từ chối/đã duyệt; refresh và đăng nhập lại vẫn mở đúng; hai lần tạo cạnh tranh chỉ có một phiếu; truy cập ngoài quyền theo contract.
- Đóng mục khi API, UI và kiểm tra thật chứng minh mở lại được phiếu; không đóng chỉ vì fixture xanh.

### P1 — NV-MAIN-006: preview dòng linh kiện trước lưu nháp

PhieuXuatCreate chỉ nhận loại phiếu và ID yêu cầu; dòng hàng do POST chốt. Không dùng API kiểm tra yêu cầu ở trạng thái khác để thay preview.

Đề xuất endpoint GET chỉ đọc theo yêu cầu và loại phiếu, trả nguồn nhu cầu đã chốt cùng mã/tên/đơn vị/số lượng cần thiết cho preview. Đường dẫn và response là hợp đồng mới cần duyệt, không phải endpoint đang tồn tại.

- Tái sử dụng nguồn tính dòng của create; không tính BOM lần nữa ở frontend, không ghi/giữ hàng hoặc tạo nháp khi mở preview.
- POST vẫn kiểm tra lại quyền/trạng thái và chốt dữ liệu bằng transaction hiện hành. Preview không bảo đảm dữ liệu không đổi; khi trạng thái đổi phải báo lỗi và tải lại, không tự sửa payload.
- UI mở modal tải preview, có loading/error/retry; hủy không POST; lưu nháp xong dùng response thật để hiển thị, gửi là bước riêng.
- Test: nhu cầu đúng, không có dòng, trạng thái không hợp lệ, bị hủy/đổi trạng thái giữa preview và lưu, mất quyền, lỗi tải; chứng minh GET không gây biến động DB.
- Cập nhật sequence module sở hữu endpoint và contract/UC liên quan trong cùng thay đổi.

### P2 — NV-CHECK-001: accessibility và responsive

Kiểm desktop và 375px, browser zoom thật 200%, chuỗi dài, contrast chữ/control/focus, reduced-motion; đi hết luồng bằng keyboard. Dialog phải wrap focus đúng đầu/cuối, trả focus về nút mở, cuộn thân dialog và giữ nút thao tác dùng được; pending chặn submit trùng và đóng ngoài ý muốn. Ghi ảnh và kết quả đo; viewport nhỏ không thay bằng chứng zoom.

### Các missing cần quyết định riêng

- FE-MISS-003 avatar ảnh: giữ initials theo quyết định hiện có; upload/lưu ảnh là tính năng riêng.
- FE-MISS-006 badQty/note: không tự bổ sung vào chứng từ main; cần chốt nghiệp vụ và contract nếu muốn làm.
- FE-MISS-008 ngưỡng tồn tối thiểu: tồn/đang giữ/còn dùng đã có; ngưỡng min chưa có. Không tự gán ngưỡng hoặc suy ra tồn thấp từ số lượng 0.
- NV-CHECK-003: nghiệm thu của dev, không thay bằng review/test tự động.

## 3. E2E API/PostgreSQL thật — NV-CHECK-002

### Môi trường

Tạo cấu hình Playwright riêng cho tests/e2e, URL frontend/backend test rõ ràng; không dùng installApi hoặc route.fulfill cho API nghiệp vụ. Đăng nhập thật. Giữ bộ fixture hiện có để kiểm trạng thái lỗi/busy một cách ổn định.

Chỉ dùng PostgreSQL test riêng mới/trống với bootstrap hiện tại sau khi duyệt môi trường. Kiểm tra đích kết nối và chặn chạy nếu trùng DB ứng dụng; không seed/reset volume có dữ liệu. Browser chạy qua server có transaction riêng nên không giả định rollback của pytest sẽ dọn được ghi từ browser. Dùng dữ liệu mang run ID hoặc database dùng một lần; cleanup chỉ tài nguyên test xác định rõ.

Chuẩn bị NV-A, NV-B, QLK và admin cho smoke regression; yêu cầu giao cho A/B riêng, BOM/mặt hàng/tồn đủ và thiếu, yêu cầu xuất không cần sản xuất, yêu cầu có sản xuất, chứng từ nháp/từ chối/đã duyệt. Dữ liệu test không phải seed vào ứng dụng.

### Ma trận bắt buộc

| Nhóm | Kịch bản và bằng chứng |
| --- | --- |
| Auth | Đăng nhập thật, refresh, hết hạn phiên, logout; không truy cập dữ liệu sau logout |
| Tổng quan/Việc được giao | KPI, lọc/tìm/phân trang đúng dữ liệu; filter nâng cao thu gọn khi vào trang; A/B thấy và thao tác đúng quyền theo main |
| Bắt đầu sản xuất | Điều kiện đủ/thiếu vật tư, trạng thái hợp lệ, xác nhận và hủy; không tự giả định mọi yêu cầu đều được bắt đầu |
| Phiếu linh kiện | Preview không ghi; tạo nháp, refresh/mở lại, gửi; QLK từ chối rồi NV gửi lại; QLK duyệt, tồn/giữ hàng/audit đúng quy tắc main |
| Hoàn thành | Tạo theo yêu cầu, số lượng/giờ từ server; tạo nháp rồi gửi; QLK từ chối/gửi lại/duyệt; không tạo chứng từ trùng |
| Phiếu thành phẩm | Nhánh dùng tồn sẵn không sản xuất và nhánh cần hoàn thành đã duyệt; tạo/gửi/duyệt, biến động kho đúng một lần |
| Phân quyền | Hai browser context A/B; đọc/ghi theo policy backend; NV không duyệt, không đọc danh sách QLK; thử trực tiếp API trên test backend để chứng minh UI ẩn nút chưa đủ |
| Cạnh tranh | ETag cũ, double click, hai tab, tạo trùng, mất phản hồi sau ghi; không nhân đôi chứng từ/biến động kho/audit |
| Tra cứu và tài khoản | Tồn/giữ/còn dùng khớp dữ liệu test; chi tiết mặt hàng; profile chỉ đọc, logout Topbar |
| Hồi quy | Admin/QLK sidebar, chi tiết, duyệt/từ chối và dialog dùng chung; desktop/mobile |

Các mã 401/403/404/409/412/422/428 phải đối chiếu contract thực tế cho từng endpoint, không áp một mã chung. Kiểm DB chỉ đọc sau thao tác để xác nhận transaction, số bản ghi và số dư; test lỗi rollback ở tầng integration khi cần fault injection, không can thiệp DB ứng dụng.

## 4. Bàn giao và điều kiện hoàn tất

1. Chốt hợp đồng lookup/preview và môi trường DB test; frontend độc lập/accessibility có thể làm trước.
2. Backend contract/service tests và sequence; tích hợp UI cùng fixture bám contract.
3. Chạy unit, lint, build và bộ browser liên quan; sau đó E2E thật trên database test.
4. Báo từng tầng: pass/fail/skip, command, commit SHA, môi trường, thời điểm, exit code, trace/screenshot đã xem; không tính skip là pass. Không lưu credential/token trong artifacts công khai.
5. Cập nhật MISSING và đặc tả theo bằng chứng; trình dev nghiệm thu. Commit/push cần yêu cầu riêng.

Kế hoạch không bao gồm sửa Dockerfile còn dang dở, merge lịch sử main, avatar upload, badQty/note hay ngưỡng min nếu chưa được chốt. Chưa chạy test hoặc gọi API/DB trong lượt lập kế hoạch.
