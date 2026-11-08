# Báo cáo triển khai UI Admin — xBike MRP

Ngày báo cáo: **08/11/2026**. Branch: **`feature/UI-admin`**.

**Kết quả:** đã hoàn thành và qua review Codex trong phạm vi frontend được dev chấp thuận. Giao diện sử dụng API hiện có; các phần thiếu API vẫn được theo dõi riêng. Chưa kết luận toàn bộ chức năng admin hoặc E2E với backend/database thật đã hoàn tất.

## 1. Căn cứ và phạm vi

- [Đặc tả giao diện admin](./dac-ta-giao-dien-admin.md), năm ảnh gốc trong [ui-spec-admin](./ui-spec-admin/) và các quyết định của dev trong cuộc trò chuyện.
- [Quy tắc frontend](./FRONTEND_RULES.md), `AGENTS.md` và [danh sách còn thiếu](./MISSING.md).
- [Kế hoạch triển khai ban đầu](./admin-ui-plan.md) và [review ban đầu](./admin-ui-review-round-2.md).
- [Kế hoạch chỉnh sửa trực tiếp](./admin-ui-inline-edit-plan.md) và [bằng chứng các vòng review tiếp theo](./admin-ui-inline-edit-review.md).

Phần UI admin ban đầu đã có trong commit `f1085ae`; bản sửa biểu tượng mắt trùng của Edge có trong `373ecae`. Báo cáo này đi cùng phần cập nhật chỉnh sửa trực tiếp, phản hồi khi lưu, popup đăng xuất, nút vai trò và kiểm thử tương ứng.

Không thay đổi backend, hợp đồng API, schema, dependency hoặc dữ liệu ứng dụng trong đợt cập nhật frontend này.

## 2. Các phần đã triển khai

| Khu vực | Đường dẫn | Trạng thái và hành vi |
| --- | --- | --- |
| Tổng quan | `/admin` | Bốn thẻ thống kê, donut phân bổ tài khoản theo vai trò và hoạt động gần đây lấy từ API hiện có; giữ khung lưu lượng khi chưa có API. |
| Quản lý tài khoản | `/admin/tai-khoan` | Danh sách, checkbox trên trang hiện tại, tìm kiếm bằng Enter, bộ lọc khi chọn, phân trang chỉ 10 dòng/trang và các hành động theo quyền. |
| Chi tiết tài khoản | `/admin/tai-khoan/:id` | Khối danh tính bên trái và mười hàng thông tin bên phải; mật khẩu luôn là dấu chấm cố định. |
| Chỉnh sửa tài khoản | `/admin/tai-khoan/:id?mode=edit` | Sửa trực tiếp trong các hàng chi tiết, nút Hủy/Lưu ở thanh hành động; thay thế form sửa hai cột cũ. |
| Tạo tài khoản | `/admin/tai-khoan/moi` | Giữ form tạo và validation hiện có; không xóa luồng này khi thay form sửa. |
| Quản lý vai trò | `/admin/vai-tro` | Danh sách thật, tìm kiếm và phân trang; cả Sửa/Xóa của ba vai trò hệ thống bị disabled theo mã vai trò. |
| Lịch sử | `/admin/lich-su` | Giữ trang và khả năng đọc API lịch sử theo quyền; không đưa dữ liệu snapshot nghiệp vụ bị hạn chế vào giao diện admin. |
| Hồ sơ bản thân | `/ho-so` | Giữ luồng hồ sơ/đổi mật khẩu hiện có. |

- [x] Theme nâu tối/cam, sidebar XBIKE, artwork xe đạp, breadcrumb, avatar chữ cái và bố cục bám thiết kế đã chốt.
- [x] Form sửa cũ với các khối Phân quyền/Trạng thái tài khoản tách riêng đã được thay bằng chỉnh sửa trực tiếp; trang chi tiết và form tạo mới vẫn được giữ.
- [x] Sáu trường hồ sơ được sửa: họ tên, ngày sinh, số điện thoại, email, ngày vào làm, hệ số lương. Vai trò là dropdown trong chính hàng Vai trò.
- [x] Tên đăng nhập, mật khẩu che cố định và trạng thái giữ chế độ chỉ đọc tương ứng; không tự thêm chức năng sửa tên đăng nhập hoặc reset mật khẩu.
- [x] Nút Sửa của `quan_tri_vien`, `quan_ly`, `nhan_vien` dùng `disabled` thật. Tìm kiếm hoặc thay thứ tự hiển thị không bỏ được bảo vệ theo mã vai trò.
- [x] Popup đăng xuất chỉ hỏi **“Bạn có muốn kết thúc phiên làm việc?”**, có Hủy/Xác nhận và X đóng; bỏ nhắc lưu và notice tồn kho riêng ở popup này.
- [x] Ô mật khẩu đăng nhập giữ một nút hiện/ẩn của ứng dụng; biểu tượng mặc định bị trùng trên Edge đã được ẩn.

## 3. Luồng lưu hồ sơ và vai trò

Dev đã chốt **một nút Lưu cho cả hồ sơ và vai trò**, đồng thời **giữ xác nhận trước khi ghi**.

1. Bấm Lưu mở popup xác nhận; chưa gửi request ghi.
2. Hủy/X trong popup không ghi và giữ bản nháp; Hủy chế độ chỉnh sửa bỏ phần nháp chưa lưu để quay về xem chi tiết.
3. Xác nhận mới gửi những phần thực sự thay đổi. Không gửi request hồ sơ/vai trò dư thừa khi phần đó không đổi.
4. Chỉ sau khi mọi phần yêu cầu lưu thành công mới hiện popup **“Lưu thành công”**, dấu check xanh và một nút **Đóng**.
5. Nếu hồ sơ đã lưu nhưng đổi vai trò lỗi, thông báo rõ phần đã lưu và phần còn lỗi. Không giả lập rollback, không báo thành công toàn bộ; hủy hoặc mở sửa lại vẫn phản ánh hồ sơ đã lưu.

| Thao tác | API hiện có | Điều kiện phiên bản |
| --- | --- | --- |
| Lưu hồ sơ | `PATCH /api/v1/nhan_vien/{id}` | Gửi `If-Match` của snapshot đã được người dùng kiểm tra. |
| Lưu vai trò | `PUT /api/v1/nhan_vien/{id}/vai_tro` | Dùng ETag đã kiểm tra nếu chỉ đổi vai trò; nếu sau PATCH thì dùng ETag của response PATCH thành công trong chính chuỗi lưu này. |
| Khóa/mở khóa | API nhân viên hiện có | Giữ snapshot/ETag, yêu cầu lý do và chặn thao tác không được phép. |

Hai API lưu là **hai lần ghi riêng**, không phải một transaction chung. Nếu phản hồi lần ghi đầu thiếu ETag cần cho bước sau, frontend dừng bước tiếp theo và báo đúng phần đã lưu. Lỗi mạng có thể chưa xác định kết quả ghi; không tự retry thao tác ghi.

## 4. Bảo toàn dữ liệu và quyền

- [x] Cố định baseline của phiên sửa và snapshot trong popup xác nhận; refetch nền không âm thầm thay ETag để ghi đè dữ liệu mới của người khác.
- [x] Lỗi `412`/`428` không bị vượt qua bằng GET lấy ETag mới rồi tự gửi lại.
- [x] Chống gửi lặp và giữ trạng thái đang xử lý; không mất phần nháp chưa lưu khi có lỗi.
- [x] Phần đã lưu được phản ánh trong baseline và cache; thử lại phần còn lỗi không tự PATCH lại hồ sơ đã lưu.
- [x] Cache cập nhật đúng user/vai trò hiện tại, không ghi đè projection của user hoặc vai trò khác.
- [x] Giữ chặn khóa chính mình/quản trị viên và chặn đổi vai trò quản trị viên theo luồng hiện có; không làm yếu phân quyền backend.
- [x] Chỉ Xác nhận đăng xuất mới kết thúc phiên và xóa cache theo luồng hiện có; Hủy/X giữ phiên.
- [x] Các kiểm tra ghi dùng browser fixture cô lập; fixture không được import vào ứng dụng chạy thật. Không seed/reset hoặc xóa database/volume để kiểm thử.

## 5. Kết quả kiểm chứng

| Kiểm tra | Kết quả | Phạm vi bằng chứng |
| --- | --- | --- |
| `npm run lint` | Đạt | Frontend, vòng sửa cuối. |
| `npm test` | 27/27 đạt | Unit tests frontend. |
| `npm run build` | Đạt | Build production frontend. |
| `admin-ui.spec.js` và `mutations.spec.js` | 20/20 đạt | Vòng cuối: 10 admin UI và 10 mutation test. |
| Năm suite admin/mutations/navigation/record-dialog/sidebar | 54/54 đạt ở vòng 2 | Kết quả trước bước thu hẹp cache cuối; không khẳng định đã chạy lại cả 54 test ở vòng cuối. |
| Kiểm chứng độc lập của Codex | Đạt | ETag khi refetch trong lúc xác nhận, thông báo partial save, Hủy/mở sửa lại sau partial save và cô lập cache user khác. |
| Đối chiếu ảnh thực tế | Đạt phạm vi frontend | Xem chi tiết, sửa trực tiếp, xác nhận trước lưu, popup thành công, popup đăng xuất và bảng vai trò. |
| Ghi E2E với FastAPI/PostgreSQL thật | Chưa thực hiện | Browser fixture không thay thế bằng chứng E2E backend/database. |

Các lệnh chạy từ `frontend/`:

```sh
npm run lint
npm test
npm run build
npx playwright test tests/browser/admin-ui.spec.js tests/browser/mutations.spec.js
```

Lịch sử review có hai lần Codex yêu cầu sửa tiếp trước khi kết luận đạt: lỗi ETag dùng phiên bản mới khi xác nhận, sai chữ ký `ApiError`, cache không phản ánh partial save, test mở menu đăng xuất và phạm vi cache chưa giới hạn user/vai trò. Các lỗi này đã được sửa và có kiểm chứng hồi quy trong [báo cáo review](./admin-ui-inline-edit-review.md).

## 6. Ảnh giao diện đã triển khai

Ảnh dưới đây chụp từ frontend chạy thật với **API fixture kiểm thử trong trình duyệt**, viewport 1672 × 941. Đây là ảnh triển khai, không phải mockup AI hoặc bằng chứng đã ghi vào database thật.

| Trạng thái | Ảnh |
| --- | --- |
| Xem chi tiết | [Mở ảnh](./ui-admin-screenshots/01-account-detail.png) |
| Chỉnh sửa trực tiếp | [Mở ảnh](./ui-admin-screenshots/02-inline-edit.png) |
| Xác nhận trước khi lưu | [Mở ảnh](./ui-admin-screenshots/03-confirm-before-save.png) |
| Lưu thành công | [Mở ảnh](./ui-admin-screenshots/04-save-success.png) |
| Xác nhận kết thúc phiên | [Mở ảnh](./ui-admin-screenshots/05-logout.png) |
| Ba nút Sửa vai trò bị vô hiệu hóa | [Mở ảnh](./ui-admin-screenshots/06-disabled-role-edit.png) |

![Chỉnh sửa trực tiếp trong trang chi tiết](./ui-admin-screenshots/02-inline-edit.png)

![Popup lưu thành công](./ui-admin-screenshots/04-save-success.png)

![Popup đăng xuất rút gọn](./ui-admin-screenshots/05-logout.png)

## 7. Các phần chưa hoàn tất hoặc cần backend

Các mục sau vẫn mở tại [MISSING.md](./MISSING.md); hoàn thiện UI không có nghĩa đã cung cấp API còn thiếu:

- [ ] **FE-MISS-001:** dữ liệu lưu lượng truy cập website theo giờ/khoảng thời gian. Khung và nút vẫn hiện, chưa gắn hành động, không vẽ dữ liệu giả.
- [ ] **FE-MISS-002:** mô tả vai trò và API tạo/sửa/xóa vai trò. Giữ danh sách thật, placeholder dữ liệu thiếu; ba vai trò hệ thống được bảo vệ như dev đã chốt.
- [ ] **FE-MISS-003:** API chưa cung cấp ảnh đại diện nhân viên. Giữ avatar chữ cái như đã thống nhất, không tự thêm upload ảnh.
- [ ] **FE-MISS-004:** mô tả hoạt động gần đây ngoài projection API audit hiện có. Không tự bịa nội dung hoặc lấy snapshot nghiệp vụ bị hạn chế.
- [ ] **FE-MISS-005:** API admin đặt lại mật khẩu nhân viên. Hàng mật khẩu vẫn chỉ hiển thị dấu chấm cố định.
- [ ] Kiểm chứng ghi E2E trên backend/database test riêng phù hợp hợp đồng hiện tại.

## 8. Các file trong đợt bàn giao này

| Nhóm | File | Mục đích |
| --- | --- | --- |
| Giao diện/luồng tài khoản | `frontend/src/features/auth/UsersPage.jsx` | Chỉnh sửa trực tiếp, lưu hồ sơ/vai trò, ETag, cache và partial save. |
| Thông báo dùng chung | `frontend/src/components/FeedbackProvider.jsx` | Popup thành công, đóng bằng bàn phím và trả focus. |
| Vai trò | `frontend/src/features/auth/RolesPage.jsx` | Disabled Sửa theo ba mã vai trò hệ thống. |
| Khung ứng dụng | `frontend/src/layouts/MainLayout.jsx` | Nội dung và phạm vi popup đăng xuất. |
| Kiểu hiển thị | `frontend/src/app/App.css` | Input trực tiếp, popup thành công và logout có phạm vi. |
| Kiểm thử | `frontend/tests/browser/admin-ui.spec.js`, `api-fixture.js`, `mutations.spec.js` | Kiểm tra luồng mới và hồi quy an toàn dữ liệu. |
| Tài liệu | `doc/MISSING.md`, `dac-ta-giao-dien-admin.md`, `admin-ui-inline-edit-plan.md`, `admin-ui-inline-edit-review.md` | Yêu cầu, quyết định, checklist và bằng chứng. |
| Bàn giao | `doc/bao-cao-ui-admin.md`, `doc/ui-admin-screenshots/*.png` | Báo cáo tổng hợp và ảnh kiểm chứng có thể xem cùng repository. |

**Kết luận bàn giao:** đạt yêu cầu frontend đã chốt; còn các phụ thuộc API và kiểm chứng E2E nêu trên. Dev đã yêu cầu commit/push báo cáo cùng code lên `feature/UI-admin`; không bao gồm merge vào `main` hoặc thay đổi môi trường dữ liệu.
