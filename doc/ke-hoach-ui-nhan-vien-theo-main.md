# Kế hoạch sửa UI Nhân viên theo main

Ngày lập: 16/11/2026. Trạng thái: đề xuất, chưa triển khai hoặc nghiệm thu.

**Cập nhật thực thi 17/11/2026:** Dev đã yêu cầu sửa theo luồng main sau review. Đã chuyển source theo mô hình yêu cầu, quyền NV lập/gửi phiếu và QLK duyệt, payload chỉ gồm nguồn, giao diện chỉ đọc và gửi lại trực tiếp. Các lựa chọn chờ chốt ở mục 4 bên dưới là lịch sử của bản kế hoạch, được thay bằng chỉ đạo này. Giữ giao diện NV người dùng đã chỉnh. Nguồn backend/infra đối chiếu main `b228193`; không chạy SQL/seed hoặc sửa backend nghiệp vụ. Hai giới hạn lookup phiếu theo yêu cầu và preview dòng trước Lưu vẫn mở tại NV-MAIN-005/006 trong MISSING. Chưa có merge commit, push hoặc nghiệm thu; các checklist dưới đây là danh sách công việc gốc, kết quả cuối ghi tại [báo cáo review và sửa](./review-ui-nhan-vien-truoc-push.md).

## 1. Mốc đối chiếu và nguyên tắc

- UI hiện tại: `feature/UI-nhanvien`, commit `5d6e207`; chưa merge main.
- Backend/frontend đích đã đọc bằng `git show origin/main:<path>`: `b228193df637d5f6cf908d366965f92caa89e1b5`. Kiểm tra lại SHA trước triển khai; nếu main đổi thì rà lại hợp đồng.
- 79 ảnh tại [mục lục ảnh](./ui-nhan-vien-screenshots/2026-11-16/README.md) là fixture của UI cũ, không phải ảnh main hoặc bằng chứng API thật. Đã mở xem trực tiếp dashboard desktop, form tạo chứng từ theo lệnh và popup lệnh mobile trong lượt lập kế hoạch này; không tuyên bố đã xem trực tiếp cả 79 ảnh.
- Áp dụng `AGENTS.md`, `doc/FRONTEND_RULES.md` còn trên nhánh UI; main đã xóa FRONTEND_RULES và MISSING, không mặc nhiên coi việc xóa file là quyền bỏ các ràng buộc người dùng đã giao.
- Skill đã đọc: `clean-code` (kèm React/JavaScript pack), `ui-ux-pro-max` (tra cứu dialog/focus/keyboard). Giữ stack React hiện có, không áp dụng khuyến nghị React 19 hoặc nâng dependency từ skill cho project React 18.
- Chỉ lập kế hoạch frontend, fixture/test và tài liệu; không sửa backend/schema, chạy DB, commit hoặc push. Giữ nguyên file chưa lưu và ảnh nguồn.

## 2. Ảnh hiện có và hướng chuyển đổi

| Nhóm ảnh | Hiện đang có | Đề xuất theo main |
| --- | --- | --- |
| 01–03 dashboard | 4 KPI, 3 tab, danh sách yêu cầu, việc tiếp theo, tồn nhanh, chứng từ gần đây | Giữ phong cách tối/cam, card, bảng và tồn nhanh; KPI/lọc phải dựa trên yêu cầu. Không dùng API lệnh đã bỏ hoặc API danh sách chứng từ chỉ dành QLK |
| 04, 15–16 yêu cầu | Danh sách và popup chỉ đọc | Trở thành trung tâm thao tác: xem yêu cầu được giao, kiểm tra/giữ hàng, bắt đầu sản xuất, mở chứng từ liên quan |
| 05, 17–18 lệnh | Trang và popup lệnh riêng, tiến độ theo lệnh | Main redirect `/nv/lenh-sx/*` về yêu cầu. Chuyển cách trình bày ô thông tin sang chi tiết yêu cầu; không coi ID lệnh cũ là ID yêu cầu |
| 06, 19–23 chứng từ | Trang riêng; chọn lệnh, nhập số lượng, giờ hiện tại; sửa/xóa/trả nháp | Mở từ yêu cầu, mỗi yêu cầu một chứng từ; số lượng cố định từ server, không nhập thời điểm; bị từ chối thì gửi lại trực tiếp |
| 07, 12–13, 24–27 phiếu xuất | Danh sách và chi tiết chỉ đọc; tham chiếu lệnh hoặc yêu cầu | Chi tiết dùng `yeu_cau_san_xuat_id`; danh sách cho NV chưa được endpoint danh sách hỗ trợ. Quyền lập/gửi thay đổi, cần chốt với dev |
| 08, 28 tồn kho | Bảng và popup 2 cột | Giữ bố cục; rà schema tồn hiện tại của main, phân biệt tồn thực/giữ/còn dùng nếu response hỗ trợ; không tự suy ra trường thiếu |
| 09–11 Phiếu của tôi | 3 tab, gồm danh sách hoàn thành và phiếu xuất | Không tiếp tục gọi hai endpoint danh sách bị giới hạn QLK; đề xuất truy cập chứng từ trong chi tiết yêu cầu, quyết định menu/tab cần chốt |
| 14, 33–35 tài khoản | Hồ sơ, đổi mật khẩu, menu và xác nhận đăng xuất | Main ProfilePage chỉ còn hồ sơ; dùng luồng auth mới. Không phục hồi form đổi mật khẩu cũ chỉ dựa vào ảnh |
| 29–32 xác nhận | Bắt đầu lệnh, xóa nháp, gửi duyệt, trả nháp | Bắt đầu yêu cầu, kiểm tra/giữ hàng, tạo nháp và gửi/gửi lại; bỏ hành vi xóa/sửa/trả nháp không có trong UC-30 mới sau khi chốt đặc tả |
| 36 mobile drawer | Sidebar 6 mục, nền xe đạp | Giữ hình thức, kiểm tra menu theo quyết định mới; không cố giữ đủ 6 mục bằng route/API không còn hợp lệ |

Giữ các chi tiết thị giác đã duyệt: màu Admin tối/cam cho NV, ảnh sidebar, tài khoản trên Topbar, ô chi tiết đóng khung 2 cột, bảng cuộn ngang, popup có header/đóng luôn truy cập được. Ảnh mobile cho thấy popup dài phải cuộn trong thân; tiếp tục chụp phần đầu/cuối, không mở rộng popup vượt viewport.

## 3. Hợp đồng đã xác minh từ source main

Các đường dẫn dưới đây có tiền tố `/api/v1`. Nguồn chính: `backend/app/modules/san_xuat/{router.py,schemas.py,service/chung_tu_hoan_thanh_sx.py}`, `phieu_xuat/{router.py,schemas.py,service.py}`, `frontend/src/features/production/{RequestsPage.jsx,completionForm.js}` tại SHA đích.

| UI / thao tác | Method + endpoint | Ràng buộc phải giữ |
| --- | --- | --- |
| Yêu cầu được giao | GET `/yeu_cau_san_xuat`, GET `/yeu_cau_san_xuat/{id}` | NV/QLK; phân trang/lọc theo schema; backend quyết định phạm vi dữ liệu |
| Xem trước kiểm tra | GET `/yeu_cau_san_xuat/{id}/kiem_tra` | NV; chỉ đọc kết quả dự kiến, không được trình bày như đã giữ hàng |
| Xác nhận kiểm tra/giữ hàng | POST `/yeu_cau_san_xuat/{id}/kiem_tra` | Body `{}`, If-Match của yêu cầu, xác nhận trước khi ghi |
| Bắt đầu sản xuất | POST `/yeu_cau_san_xuat/{id}/bat_dau` | Body `{}`, If-Match của yêu cầu; kiểm điều kiện từ main, không tự suy theo lệnh cũ |
| Chứng từ của yêu cầu | GET `/yeu_cau_san_xuat/{id}/chung_tu_hoan_thanh` | Response `data` có thể null; không có chứng từ không phải lỗi tải |
| Tạo nháp hoàn thành | POST `/chung_tu_hoan_thanh_sx` | Chỉ `{yeu_cau_san_xuat_id}`; đã bắt đầu, đang thực hiện, số cần SX > 0; mỗi yêu cầu một chứng từ |
| Chi tiết hoàn thành | GET `/chung_tu_hoan_thanh_sx/{id}` | NV được giao/QLK theo service; QLK không xem bản nháp |
| Gửi / gửi lại | POST `/chung_tu_hoan_thanh_sx/{id}/gui` | Body `{}`, If-Match chứng từ; từ nháp hoặc từ chối; server ghi `finish_time` khi gửi |
| Danh sách hoàn thành | GET `/chung_tu_hoan_thanh_sx` | Chỉ QLK; không gọi từ dashboard/Phiếu của tôi của NV |
| Phiếu xuất chi tiết | GET `/phieu_xuat/{id}` | NV/QLK; service kiểm NV được giao yêu cầu |
| Danh sách phiếu xuất | GET `/phieu_xuat` | QLK; menu tra cứu NV trong ảnh thiếu nguồn danh sách có quyền phù hợp |
| Lập/gửi phiếu xuất | POST `/phieu_xuat`, POST `/phieu_xuat/{id}/gui` | Main cho NV; tạo nhận `loai_phieu`, `yeu_cau_san_xuat_id`; chưa tự đưa hành động này vào thiết kế chỉ đọc cũ |
| Duyệt/từ chối | POST `.../{id}/duyet`, `.../{id}/tu_choi` | QLK; không xuất hiện thành thao tác NV |
| Tồn/danh mục | GET `/mat_hang`, `/mat_hang/{id}`, `/danh_muc_mat_hang/` | Tái sử dụng client main; chỉ đọc cho NV, rà trường/filter thực tế trước triển khai |
| Tài khoản | `/auth/dang_nhap`, `/auth/me`; ProfilePage main | Tái sử dụng auth main; kiểm luồng logout và quyền đổi mật khẩu theo UC-01/02/08, không dùng API.password đã bỏ khỏi endpoints.js |

UC-30 main quy định số lượng hoàn thành bằng `so_luong_can_san_xuat`, server tạo giá trị này; `finish_time` ban đầu có thể null. Không gửi `lenh_san_xuat_id`, số lượng nhập tay hoặc giờ máy khách. Không có PATCH/DELETE/`ve_nhap` hoàn thành trong router đã đọc. Tài liệu nguồn: `specs/use_cases/production/UC-30.md`; route lệnh cũ không còn là resource API ở router main.

Không tin riêng `documentPermissions()` cũ: source main vẫn còn các cờ edit/returnDraft mang nghĩa cũ; đối chiếu router/service và `completionForm.js` trước khi tái sử dụng.

## 4. Các quyết định cần chốt trước triển khai phần liên quan

1. **Điều hướng:** đề xuất theo main: Tổng quan / Việc được giao / Tra cứu tồn kho; chứng từ trong yêu cầu. Có giữ mục tra cứu phiếu xuất riêng không, khi endpoint danh sách NV chưa có? Không âm thầm xóa menu thiết kế.
2. **Dashboard:** đề xuất 3 KPI theo main (yêu cầu được giao, đã giao, đang thực hiện), bỏ phụ thuộc danh sách chứng từ toàn cục. Tab chờ duyệt và bảng chứng từ gần đây cần quyết định bỏ/đổi hoặc backend cung cấp; không tải từng yêu cầu kiểu N+1 để giả làm API tổng hợp.
3. **Phiếu xuất:** main cho NV lập/gửi, trái yêu cầu trước đây chỉ đọc. Đề xuất triển khai đúng UC main sau khi dev xác nhận mở rộng tương tác; tuyệt đối không cấp quyền duyệt cho NV.
4. **Tài khoản:** đề xuất hồ sơ chỉ đọc và đăng xuất theo main; không giữ form đổi mật khẩu cũ khi chưa xác minh quyền/endpoint tương ứng.

Các mục này là khác biệt yêu cầu/hợp đồng, không phải lỗi frontend đã được phép tự sửa. Ghi theo dõi trong MISSING; có thể triển khai phần bố cục độc lập trong lúc chờ quyết định.

## 5. Thứ tự triển khai và phạm vi file

- [ ] **Bước 1 — Chuẩn bị tích hợp:** xác nhận SHA main, bảo toàn file chưa lưu/79 ảnh, tạo mốc khôi phục. Giải quyết merge theo mô hình main, không phục hồi ProductionPage/CompletionsPage cũ để làm hết conflict. Không tự commit/push.
- [ ] **Bước 2 — Hợp đồng và route:** cập nhật đặc tả/MISSING trước các điểm thay đổi; sửa `routes/index.jsx`, `layouts/navigation.js`, `Sidebar.jsx`, `MainLayout.jsx`. Giữ redirect lệnh của main; xử lý URL hoàn thành cũ bằng trang/điều hướng đã thống nhất, không ánh xạ ID tùy tiện.
- [ ] **Bước 3 — Yêu cầu là trung tâm:** tái sử dụng `RequestsPage.jsx`, `requestForm.js`, `completionForm.js` của main; bổ sung style employee có phạm vi. Hiện loại yêu cầu, hạn, số cần SX, bắt đầu, trạng thái từ YeuCauRead. Popup kiểm tra hiển thị phần còn dùng/thiếu và dự kiến giữ hàng từ KiemTraKetQua.
- [ ] **Bước 4 — Chứng từ:** chuyển hình thức ô chi tiết và popup xác nhận từ ảnh sang luồng tạo nháp → gửi; thêm gửi lại trực tiếp khi từ chối theo main. Số lượng chỉ đọc; không có input thời điểm tạo mới. ETag phải đúng resource; lỗi 409/412/428 giữ nội dung và yêu cầu tải lại/xác nhận lại phù hợp.
- [ ] **Bước 5 — Dashboard và tra cứu:** sửa `DashboardPage.jsx` theo KPI/menu đã chốt; giữ QuickStock. Rà `MaterialIssuingPage.jsx`, `MaterialsPage.jsx`, `MyDocumentsPage.jsx` theo quyền danh sách và tham chiếu mới; không dùng fixture để che lỗi 403.
- [ ] **Bước 6 — Responsive/accessibility:** giữ style trong `.employee-shell`/`html[data-employee-theme]`; không đổi admin/manager toàn cục. Kiểm 375/768/1024/1440, tab bàn phím, focus trap/return focus, Escape, loading/error/empty, busy và chống gửi lặp.
- [ ] **Bước 7 — Fixture/test và bàn giao:** cập nhật fixture theo schema/quyền main; các route cũ phải bị phát hiện chứ không giả trả thành công. Cập nhật test NV-03/NV-04/NV-09 theo luồng mới đã chốt; giữ kiểm tra quyền, ETag và trạng thái lỗi. Chụp bộ ảnh mới riêng, giữ bộ ảnh cũ để so sánh.

## 6. Kiểm chứng và điều kiện hoàn thành

- Chạy `npm --prefix frontend run test`, lint, build sau tích hợp; giữ các unit test UC-25/26/29/30/31/32/33 của main và hồi quy auth/role liên quan.
- Playwright employee/navigation/sidebar và workflows/record-dialog chịu ảnh hưởng: payload tạo đúng một trường; gửi đúng ETag; null chứng từ; gửi lại không gọi ve_nhap; NV không gọi API danh sách QLK; không có PATCH/DELETE hoàn thành; kiểm hai chủ sở hữu ở fixture.
- Kiểm tra popup xác nhận trước POST kiểm tra/giữ hàng, bắt đầu, gửi/gửi lại; lỗi server không đóng popup hoặc báo thành công giả; ngăn xác nhận kép.
- Hồi quy admin/manager cho các component/CSS chung và quyền lập phiếu xuất mới; không dùng kết quả 26 test cũ để chứng minh main đã tích hợp.
- API/DB E2E thật: chỉ trên môi trường test riêng được xác nhận; kiểm quyền hai tài khoản, tranh chấp ETag và tác động tồn. Chưa có bằng chứng runtime trong lượt lập plan.
- Chỉ hoàn thành khi mọi menu/action có route và API đúng quyền, phần khác biệt đã chốt hoặc ghi rõ còn mở, test phù hợp đạt và có bộ ảnh sau sửa. Dev nghiệm thu riêng; không tự accept.

## 7. Giới hạn của kế hoạch

Đã đọc source main và đối chiếu ảnh đại diện; chưa chạy API, DB, test hoặc merge trong lượt này. Module `lenh_san_xuat` chưa theo dõi tại worktree khác không thuộc commit main và không được coi là endpoint hiện có. Frontend main cũng có thể còn bất nhất với router mới; router/service/schema và UC phải được đối chiếu cùng nhau khi triển khai, không sao chép frontend main nguyên trạng rồi coi là đúng.
