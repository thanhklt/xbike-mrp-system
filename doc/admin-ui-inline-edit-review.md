# Codex review: chỉnh sửa tài khoản trực tiếp

## Vòng 1 — Chưa đạt

Argon đã sửa frontend nhưng dừng do quota trước khi gửi báo cáo hoàn tất. Dev yêu cầu chuyển chính chat AGY hiện có sang Gemini 3.8 Flash (High) để làm phần còn lại; Codex đã xác minh tên model trong terminal. Giữ Ponytail full và ba skill thiết kế đã chốt. Không commit/push.

### Kiểm tra Codex đã chạy

- [x] `npm run lint`: đạt.
- [x] `npm test`: 27/27 đạt.
- [x] `npm run build`: đạt.
- [ ] `npx playwright test tests/browser/admin-ui.spec.js tests/browser/mutations.spec.js tests/browser/record-dialog.spec.js tests/browser/navigation.spec.js tests/browser/sidebar.spec.js`: 49/51 đạt, còn hai lỗi dưới đây.
- [x] Tái hiện riêng lỗi ETag và cache bằng Playwright với API fixture trong bộ nhớ; không ghi database ứng dụng. Script kiểm chứng: `%TEMP%/xbike-admin-inline-review-repro.mjs`.
- [x] Đã xem screenshot inline edit desktop/mobile và success popup; popup thành công chưa khớp dấu check trong ảnh mẫu. Chưa có screenshot logout đạt kiểm tra ADM-04.

## Prompt sửa vòng tiếp theo cho AGY — Flash 3.8 High

Tiếp tục trên cùng code và chat, không làm lại từ đầu. Đọc plan và các quyết định dev đã chốt. Sửa các lỗi bên dưới, bổ sung kiểm thử có ý nghĩa rồi báo Codex; chưa được tự kết luận toàn bộ đạt.

### 1. P1 — Không đổi ETag đã được người dùng kiểm tra khi refetch nền

- Vị trí: `AccountDetailView`, `latestSnapshotRef`, effect theo `snapshot`, `handleInlineSubmit` và callback `onConfirm` trong `UsersPage.jsx`.
- Bằng chứng: mở sửa tài khoản 2 ở `"v1"`, sửa họ tên rồi mở xác nhận. Trong lúc xác nhận đang mở, fixture đổi số điện thoại thành `0999999999`, tăng version lên `"v2"` và kích hoạt refetch cache. Xác nhận hiện dùng `"v2"` từ `latestSnapshotRef`, PATCH lại số điện thoại cũ cùng bản nháp và báo thành công; thay đổi của người khác bị ghi đè.
- Yêu cầu: giữ snapshot nền của phiên sửa và cố định ID, payload, phạm vi thay đổi cùng ETag của thao tác đã được xác nhận. Refetch nền không được âm thầm nâng ETag cho bản nháp. Chỉ được chuyển sang ETag của response ghi thành công thuộc chính chuỗi lưu hiện tại để ghi phần tiếp theo.
- Kiểm chứng: refetch khi đang sửa và khi popup đang mở không đổi If-Match của lần ghi đầu; backend trả 412 thì dừng, giữ bản nháp, không gửi PUT tiếp hoặc GET+retry để vượt lỗi.

### 2. P1 — Sửa cách tạo ApiError và giữ thông tin lỗi

- Vị trí: ba chỗ `new ApiError({...})` mới trong `UsersPage.jsx`.
- Hợp đồng thật ở `lib/api/contract.js`: `new ApiError(message, { status, code, details, requestId, ticketId, uncertain })`.
- Hiện truyền object làm đối số đầu khiến thông báo thành `[object Object]`, mất mã HTTP và metadata. Test `admin-ui.spec.js:382` thất bại tại phần báo lưu một phần vì lỗi này.
- Yêu cầu: dùng đúng constructor, báo rõ hồ sơ đã lưu và vai trò còn lỗi. Giữ status/details/requestId cùng cờ kết quả chưa xác định khi có; lỗi mạng không được trình bày như chắc chắn đã rollback hoặc chắc chắn chưa ghi. Không hiện popup thành công toàn bộ nếu phần còn lại lỗi.
- Kiểm chứng: test partial save đạt với câu thông báo đọc được; 412/428 giữ đúng mã và hướng dẫn; lỗi mạng giữ ngữ nghĩa chưa xác định, không auto retry.

### 3. P1 — Cập nhật đúng cache và không làm hiện lại hồ sơ cũ sau partial save

- Vị trí: `setQueryData(["resources", "detail", API.employees, String(id)], ...)` và invalidation `queryKey: ["resources", API.employees]` trong `UsersPage.jsx`.
- Key thật của `useDetail` qua `useResource`: `["resources", user.id, user.ma_vai_tro, `${API.employees}/${id}`, params]`. Hai key mới không trùng cache đang được UI sử dụng và không giữ phạm vi người dùng/vai trò.
- Bằng chứng: PATCH hồ sơ thành công, PUT vai trò trả 500. Fixture đã có tên mới, nhưng Hủy popup rồi Hủy chỉnh sửa làm trang chi tiết hiển thị lại tên cũ; phần đã lưu chưa được phản ánh đúng.
- Yêu cầu: cập nhật cache thực có phạm vi user/role và baseline của phần đã lưu. Hủy chỉ bỏ phần chưa lưu, không hoàn tác bằng hiển thị giả phần đã được server lưu. Thử lại do người dùng xác nhận không được PATCH lại hồ sơ đã lưu; không tự lấy version mới để vượt 412.
- Kiểm chứng: partial success rồi Hủy về xem chi tiết phải hiện tên mới và vai trò cũ. Mở sửa lại phải khởi tạo từ dữ liệu đã lưu. Thử lại phần lỗi chỉ gửi phần chưa lưu với ETag hợp lệ được trả về từ lần ghi của chính thao tác.

### 4. P2 — Sửa test mở menu đăng xuất, giữ kiểm tra đủ Hủy/X/Xác nhận

- `ADM-04` ở `admin-ui.spec.js:514` timeout tại lời gọi nút Đăng xuất vì menu tài khoản chưa mở. Sidebar admin không có nút này; nút nằm trong `.user-menu` đóng.
- Mở menu bằng thao tác UI thật trước khi chọn Đăng xuất; đảm bảo các lần mở lại cũng hoạt động. Không xóa phần test logout, không đổi selector để click phần tử ẩn.
- Kiểm chứng: test đạt cả câu chữ, không có notice tồn kho, Hủy/X giữ phiên và chỉ Xác nhận mới đăng xuất. Chụp screenshot popup sau khi mở thành công.

### 5. P2 — Khớp ảnh popup thành công và kiểm tra lại logout

- Ảnh đã xem: `frontend/test-results/adm-05-save-success-1440x900.png`. Hiện chỉ có dấu check nhỏ màu trắng; ảnh mẫu là dấu check xanh trong vòng tròn, có kích thước và khoảng cách rõ ràng.
- Dùng icon có sẵn trong thư viện dự án và CSS nhỏ nhất để khớp ảnh; không tự vẽ lại icon nếu thư viện đã có. Giữ đúng một nút Đóng và không có API khi đóng.
- Logout đang dùng chung toàn bộ kiểu header/body/footer căn giữa với profile-save; đối chiếu trực tiếp ảnh `03-xac-nhan-dang-xuat.png` (tiêu đề/câu hỏi căn trái, nút bên phải, hộp gọn). Chỉ điều chỉnh phạm vi logout khi cần, không thay giao diện các xác nhận khác.
- Chụp và xem ảnh thực desktop và responsive; không dùng mockup AI thay screenshot sản phẩm.

## Bàn giao cần có

- [x] Sửa đủ các finding trên và kiểm thử hồi quy tương ứng; không làm yếu assertion để ép xanh.
- [x] Kiểm tra thêm ID/bản nháp khi route thay đổi và thiếu ETag response giữa hai lần ghi; không gửi dữ liệu của người này sang người khác, không dùng ETag cũ thay ETag mới bị thiếu.
- [x] Chạy lại lint, unit, build và năm browser suites nêu trên sau khi sửa; báo chính xác kết quả.
- [x] Giữ form tạo mới, chặn admin/self, validation, quyền và API hiện tại. Chưa có quyền sửa backend hoặc thử ghi trên database ứng dụng.
- [x] Cập nhật phần kết quả review ở cuối file này và checklist trong plan/đặc tả đúng bằng chứng, giữ nguyên lịch sử findings vòng 1.
- [x] Báo `worker_done` với report-path, file sửa, screenshot và giới hạn. Codex review lại trước khi kết luận đạt.

Chưa chạy E2E với backend/database thật; chưa nghiệm thu bản triển khai.

---

## Vòng 2 — Kết quả sửa lỗi và kiểm chứng (Gemini 3.8 Flash High)

Đã hoàn thành toàn bộ 5 nhóm yêu cầu sửa lỗi theo đúng checklist bàn giao:

### 1. Chi tiết các điểm đã sửa

1. **P1 — Cố định ETag và snapshot đã duyệt (`UsersPage.jsx`)**:
   - Sử dụng `editBaselineRef` cố định snapshot tại thời điểm mở phiên chỉnh sửa hoặc sau khi ghi thành công từng bước.
   - Khi đang ở chế độ chỉnh sửa (`isEditing: true`), các refetch nền từ `useDetail` không ghi đè `editBaselineRef.current.etag`.
   - Khi bấm `Lưu`, đóng băng đối tượng `submission` (gồm ID, `reviewedEtag`, bản ghi baseline, payload hồ sơ và vai trò). Lần ghi đầu tiên luôn gửi đúng `If-Match: submission.reviewedEtag`.
   - Nếu dữ liệu server thay đổi trong lúc popup xác nhận đang mở, server trả về `412 Precondition Failed`; hệ thống dừng ghi, giữ nguyên bản nháp, không tự nâng ETag và không ghi đè dữ liệu của người khác.

2. **P1 — Chuẩn hóa khởi tạo `ApiError` (`UsersPage.jsx`)**:
   - Chuyển toàn bộ các vị trí tạo lỗi sang đúng chữ ký constructor: `new ApiError(message, options)`.
   - Thông báo lỗi lưu một phần hiển thị chuỗi rõ ràng: `"Đã lưu thông tin hồ sơ, nhưng cập nhật vai trò thất bại: ..."` thay vì `[object Object]`.
   - Giữ nguyên `status`, `code`, `details`, `requestId`, `ticketId` và cờ `uncertain`.

3. **P1 — Đồng bộ React Query cache và baseline lưu thực tế (`UsersPage.jsx`)**:
   - Cập nhật đúng cấu trúc queryKey theo phạm vi người dùng/vai trò: `["resources", user.id, user.ma_vai_tro, `${API.employees}/${id}`, {}]` và đồng bộ toàn diện qua `queryClient.setQueriesData({ predicate })`.
   - Khi lưu một phần thành công (PATCH hồ sơ thành công, PUT vai trò thất bại), `editBaselineRef.current` và React Query cache lưu ngay bản ghi mới của hồ sơ và ETag mới (`"v2"`).
   - Khi người dùng bấm `Hủy` sau partial save, màn hình chi tiết hiển thị đúng họ tên mới đã lưu trên server, không còn tình trạng hiển thị lại họ tên cũ đã lỗi thời.
   - Nếu người dùng bấm `Chỉnh sửa` lại hoặc xác nhận thử lại, hệ thống nhận diện hồ sơ đã khớp baseline và chỉ gửi tiếp phần vai trò chưa lưu với ETag mới (`"v2"`).

4. **P2 — Sửa test thao tác mở menu đăng xuất (`admin-ui.spec.js`)**:
   - Thêm hàm `triggerLogout()` thực hiện mở dropdown `.user-menu summary` của topbar trước khi bấm `Đăng xuất`.
   - Kiểm tra đầy đủ cả 3 luồng: `Hủy` giữ phiên làm việc, nút đóng `×` giữ phiên làm việc, và `Xác nhận` đăng xuất chuyển hướng về `/dang-nhap`.

5. **P2 — Tinh chỉnh giao diện khớp ảnh mẫu (`FeedbackProvider.jsx`, `App.css`)**:
   - `FeedbackProvider.jsx`: Sử dụng icon `<CheckCircle2 size={52} strokeWidth={2.4} />` từ thư viện `lucide-react` với màu xanh lá `#4ade80`, tiêu đề `Lưu thành công` và nút `Đóng` cam bo góc 12px, đối chiếu trực quan khớp bố cục ảnh `02-luu-thanh-cong.png`.
   - `App.css`: Tách riêng hoàn toàn kiểu dáng của `.confirmation.confirmation-logout` khỏi `.confirmation.confirmation-profile-save`. Tiêu đề `Đăng xuất` và câu hỏi `Bạn có muốn kết thúc phiên làm việc?` căn trái, nút `×` góc trên bên phải, footer chứa hai nút `Hủy` và `Xác nhận` căn phải trong khung gọn 460px, đối chiếu trực quan khớp bố cục ảnh `03-xac-nhan-dang-xuat.png`.

### 2. Kết quả kiểm chứng tự động

- **ESLint**: `npm run lint` đạt (0 error, 0 warning).
- **Unit tests**: `npm test` đạt 27/27 test case.
- **Production Build**: `npm run build` thành công (0 error).
- **Playwright Browser Tests** (chạy từ thư mục `frontend/`): **54/54 test case ĐẠT** (100% pass trong 1.8 phút):
  - `admin-ui.spec.js`: 9/9 pass (bao gồm 3 regression test mới cho ETag freezing khi refetch nền, partial save then cancel/reopen, và thiếu response ETag).
  - `mutations.spec.js`: 10/10 pass.
  - `navigation.spec.js`: 7/7 pass.
  - `record-dialog.spec.js`: 20/20 pass.
  - `sidebar.spec.js`: 8/8 pass.

### 3. Kiểm tra trực quan bằng hình ảnh thực tế

Đã kiểm tra bằng công cụ đọc ảnh trên các screenshot thực tế vừa sinh trong `frontend/test-results/`:
- `adm-03-inline-edit-1440x900.png` và `adm-03-inline-edit-1670x941.png`: 10 hàng thông tin tài khoản hiển thị trực tiếp với các input viền cam khi focus, nút `Hủy` và `Lưu` ở thanh subbar bên cạnh `Vô hiệu hóa`, khớp `01-chinh-sua-truc-tiep.png`.
- `adm-05-save-success-1440x900.png`: Popup thông báo thành công với vòng tròn checkmark xanh lá, tiêu đề `Lưu thành công` và nút `Đóng` duy nhất, khớp `02-luu-thanh-cong.png`.
- `adm-05-logout-1440x900.png`: Popup đăng xuất rút gọn với câu hỏi duy nhất, không có thông báo ảnh hưởng tồn kho, nút `Hủy` và `Xác nhận` nằm bên phải, khớp `03-xac-nhan-dang-xuat.png`.
- `adm-04-roles-1440x900.png`: Cả 3 nút `Sửa` và `Xóa` của 3 vai trò hệ thống (`quan_tri_vien`, `quan_ly`, `nhan_vien`) bị vô hiệu hóa (`disabled` + `admin-action-muted`).

## Codex review vòng 2 — Cần thu hẹp phạm vi cập nhật cache

- [x] Đã đọc source sửa ETag/baseline, constructor ApiError, thao tác logout và ba regression test mới. Đã xem ảnh thực success, logout và bảng vai trò.
- [x] Đã đọc báo cáo 54/54 browser test và `.last-run.json` với trạng thái passed. Không chạy lại cả suite chỉ để lặp bằng chứng của worker.
- [x] **Còn lỗi:** `updateCache` trong `UsersPage.jsx` vừa `setQueryData` đúng key hiện tại, vừa `setQueriesData` với predicate chỉ kiểm tra `queryKey[0]` và `[3]`. Predicate bỏ qua user ID và mã vai trò ở vị trí `[1]`, `[2]`.
- [x] Codex đã tái hiện bằng fixture cô lập: tạo cache key `["resources", 999, "quan_ly", "/nhan_vien/3", {}]` với projection giới hạn, rồi lưu hồ sơ bằng admin. Cache của user 999 bị thay bằng response admin có cả email. Script: `%TEMP%/xbike-admin-cache-scope-probe.mjs`. Không thử trên database thật.
- [x] **Yêu cầu sửa:** bỏ `setQueriesData` dư thừa nếu `setQueryData` key thực đã đủ; nếu có lý do cần predicate thì bắt buộc match user ID và mã vai trò hiện tại. Không thay chính sách xóa cache phiên hay mở rộng refactor hook chung.
- [x] Thêm regression kiểm tra cache user khác và cache vai trò khác cùng user giữ nguyên khi lưu; cache hiện tại vẫn phản ánh partial success đúng. Chạy các test admin liên quan và lint; chỉ chạy rộng hơn nếu phát hiện ảnh hưởng khác.
- [x] Điều chỉnh câu báo cáo “khớp 100%” thành mô tả phần đã đối chiếu thực tế; chưa có phép đo pixel để khẳng định con số đó.

Nhận xét nhỏ từ ảnh logout: kiểm tra hai nút Hủy/Xác nhận nằm liền nhau và căn phải như ảnh mẫu; tránh để style grid `.actions` mặc định tạo cột giãn cách trong dialog logout. Giữ thay đổi CSS cục bộ nếu cần.

---

## Vòng 3 — Kết quả khắc phục cache isolation & hoàn thiện logout layout (Gemini 3.8 Flash High)

Đã hoàn thành toàn bộ các yêu cầu từ Codex review vòng 2:

### 1. Chi tiết các điểm đã xử lý

1. **Thu hẹp phạm vi cập nhật cache (`UsersPage.jsx`)**:
   - Loại bỏ hoàn toàn lời gọi `queryClient.setQueriesData({ predicate })` dư thừa trong hàm `updateCache`.
   - Chỉ cập nhật duy nhất một cache key đúng phạm vi actor và phiên bản hiện tại: `detailKey = ["resources", user?.id, user?.ma_vai_tro, `${API.employees}/${id}`, {}]`.
   - Đảm bảo cache projection của người dùng khác (khác user ID) hoặc vai trò khác của cùng người dùng (khác `ma_vai_tro`) không bị ghi đè hay rò rỉ dữ liệu.

2. **Bổ sung test hồi quy kiểm tra cô lập cache (`tests/browser/admin-ui.spec.js`)**:
   - Bổ sung test case: `ADM-03 regression: cache update scopes strictly to current actor/role and does not mutate other user or role projections`.
   - Seed trước 2 entry cache trong query client:
     - Khác user: `["resources", 999, "quan_ly", "nhan_vien/3", {}]` với projection giới hạn (không có email).
     - Cùng user nhưng khác role: `["resources", 1, "quan_ly", "nhan_vien/3", {}]`.
   - Thực hiện thao tác sửa hồ sơ họ tên và bấm Lưu; mô phỏng PATCH hồ sơ thành công (ETag lên `"v2"`), PUT vai trò trả 500 (lưu một phần).
   - Kiểm tra xác nhận: cả 2 projection ngoại lai trên giữ nguyên dữ liệu gốc, không bị ghi đè email hay họ tên mới. Trong khi đó, cache của actor hiện tại `["resources", 1, "quan_tri_vien", "nhan_vien/3", {}]` được cập nhật đúng họ tên mới và ETag `"v2"`.

3. **Hoàn thiện layout nút trong popup Đăng xuất (`App.css`)**:
   - Thêm CSS cục bộ cho `.confirmation.confirmation-logout .dialog-footer`:
     - Thiết lập `display: flex !important; justify-content: flex-end !important; align-items: center; gap: 12px;`.
     - `.button-wrap { width: auto; flex: 0 0 auto; display: inline-flex; }`.
   - Khắc phục triệt để hiện tượng style grid `.actions` kéo giãn 2 nút thành 2 cột rộng. Hai nút `Hủy` và `Xác nhận` giờ đây nằm liền kề nhau và căn phải, đối chiếu trực quan khớp bố cục trong ảnh mẫu `03-xac-nhan-dang-xuat.png`.

4. **Chuẩn hóa mô tả đối chiếu ảnh**:
   - Loại bỏ mọi từ ngữ "khớp 100%", thay bằng mô tả chi tiết các thành phần đã đối chiếu trực quan thực tế (kích thước icon 52px, màu sắc `#4ade80`, tiêu đề căn trái, các nút căn phải liền kề).

### 2. Kết quả kiểm chứng tự động

- **ESLint**: `npm run lint` đạt (0 error, 0 warning).
- **Unit tests**: `npm test` đạt 27/27 test case.
- **Production Build**: `npm run build` hoàn thành trong 7.68s, không lỗi.
- **Playwright Browser Tests** (chạy từ thư mục `frontend/`):
  - `admin-ui.spec.js`: 10/10 test case ĐẠT (trong đó có đủ 4 regression tests: ETag freeze nền, partial save then cancel/reopen, thiếu ETag response, và cache isolation).
  - `mutations.spec.js`: 10/10 test case ĐẠT.

Trạng thái: Hoàn tất khắc phục; sẵn sàng bàn giao cho Codex review vòng 3; không commit/push.

## Codex review cuối — Đạt phạm vi frontend (08/11/2026)

- [x] Đọc source sau vòng 3: `updateCache` chỉ ghi đúng detail key của user/vai trò hiện tại; đã bỏ predicate rộng. Đối chiếu baseline cố định của phiên sửa, submission được giữ trong popup xác nhận, ETag tuần tự từ response ghi và ApiError đúng chữ ký.
- [x] Chạy kiểm tra độc lập bằng browser fixture: cache user khác với key thực `/nhan_vien/3` không bị đổi hoặc nhận email từ response admin sau khi lưu. Script `%TEMP%/xbike-admin-cache-scope-verify.mjs`: đạt.
- [x] Chạy kiểm tra độc lập cho refetch khi xác nhận đang mở: lần ghi đầu vẫn gửi `"v1"`, nhận lỗi stale, không báo thành công và giữ nguyên điện thoại do người khác cập nhật: đạt.
- [x] Chạy kiểm tra độc lập partial save: thông báo rõ hồ sơ đã lưu/vai trò lỗi; Hủy và mở sửa lại đều giữ đúng hồ sơ đã lưu: đạt.
- [x] Chạy kiểm tra và chụp lại sáu trạng thái: chi tiết, sửa trực tiếp, xác nhận trước lưu, popup thành công, đăng xuất và ba nút Sửa vai trò bị disabled. Đã xem ảnh cuối của sửa trực tiếp, thành công và logout; nút logout liền nhau/căn phải, success có vòng tròn check xanh. Script `%TEMP%/xbike-admin-inline-final-verify.mjs`: đạt.
- [x] Đối chiếu báo cáo kiểm tra của AGY: lint, 27 unit test, build và 20 browser test admin/mutations vòng cuối đạt; năm suite trước đó đạt 54/54 ở vòng 2. Không tuyên bố đã chạy lại toàn bộ 54 test trên vòng cuối.
- [x] `git diff --check`: đạt; không có thay đổi backend/schema hay dependency, không commit/push.

Ảnh kiểm chứng độc lập được lưu ngoài source tại `C:/Users/binhb/Downloads/xbike-admin-mockups-20261108-114000/implemented/`. Dữ liệu ảnh là browser fixture cô lập, không phải bằng chứng E2E với backend/database thật.

### Các file thay đổi

- `frontend/src/features/auth/UsersPage.jsx`: thay form sửa cũ bằng mười hàng sửa trực tiếp; xác nhận/lưu hồ sơ và vai trò, ETag, cache và lỗi lưu một phần.
- `frontend/src/components/FeedbackProvider.jsx`: popup thành công có một nút Đóng và xử lý focus/Escape.
- `frontend/src/features/auth/RolesPage.jsx`: disabled nút Sửa theo ba mã vai trò hệ thống.
- `frontend/src/layouts/MainLayout.jsx`: câu hỏi đăng xuất rút gọn và ẩn notice tồn kho riêng popup này.
- `frontend/src/app/App.css`: input sửa trực tiếp, success popup và layout logout có phạm vi.
- `frontend/tests/browser/admin-ui.spec.js`, `api-fixture.js`, `mutations.spec.js`: kiểm thử và fixture tương ứng, gồm các lỗi hồi quy đã phát hiện.
- `doc/MISSING.md`, `doc/dac-ta-giao-dien-admin.md`, `doc/admin-ui-inline-edit-plan.md`, `doc/admin-ui-inline-edit-review.md`: quyết định mới, checklist, API còn thiếu và bằng chứng review.

Giới hạn: chưa chạy thử ghi E2E trên backend/database thật. Các API còn thiếu chưa được bổ sung hoặc đóng mục chỉ vì hoàn thành giao diện. Kết luận này là review frontend theo phạm vi được dev yêu cầu; không thực hiện commit/push hoặc thao tác accept/merge thay dev.
