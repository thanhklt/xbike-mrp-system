# Kế hoạch: hai dashboard chứng từ và tự đổi mật khẩu Nhân viên

Ngày: 17/11/2026. Nhánh: `feature/UI-nhanvien`. Coordinator/reviewer: phiên Sol hiện tại. Developer: **một phiên Gemini 3.8 Flash high mới**, model CLI đã tra cứu: `gemini-3.8-flash-high`.

## 1. Quyết định của dev và phạm vi

- Hai dashboard mới: **Phiếu xuất** và **Chứng từ hoàn thành**. Giữ Tổng quan, Việc được giao và Tra cứu tồn kho hiện tại; chưa gộp/xóa những trang này.
- Phiếu xuất có hai tab: **Xuất linh kiện** và **Xuất thành phẩm**. Chứng từ hoàn thành là trang riêng.
- Mỗi dòng có **một nút Xem chi tiết**, mở đúng ID hồ sơ của dòng đó. Popup chỉ hiện hồ sơ đang chọn và dữ liệu liên quan trực tiếp; không hiện nút mở hồ sơ khác, danh sách phiếu anh em hoặc chi tiết của ID khác.
- Bổ sung theo ảnh popup YCSX số 1: thay dãy nút `Mở phiếu PX-…` trong **Chi tiết yêu cầu** bằng **một** nút `Xem phiếu xuất`, mở dashboard Phiếu xuất với bộ lọc đúng `yeu_cau_san_xuat_id`. Tại dashboard, mỗi dòng có một nút mở đúng ID phiếu; không tự chọn phiếu đầu/cuối hoặc ẩn/xóa loại phiếu còn lại.
- Vẫn giữ tối đa **một phiếu mỗi loại cho một yêu cầu sản xuất**, không đổi thành một phiếu duy nhất cho cả yêu cầu. Yêu cầu sản xuất nhập kho không có phiếu xuất thành phẩm.
- Nhân viên tự đổi mật khẩu của chính mình bằng **mật khẩu hiện tại + mật khẩu mới + nhập lại mật khẩu mới**. Dev đã cho phép bổ sung API và kiểm thử cho chức năng này. Không mở quyền reset mật khẩu người khác.
- Chỉ Nhân viên có giao diện mới. Không redesign Admin/Quản lý, không thay quyền duyệt, không thêm dashboard đề nghị nhập linh kiện.
- Không commit, push, accept, sửa Dockerfile/hạ tầng, reset/seed hay ghi dữ liệu vào DB ứng dụng. Kiểm thử ghi dùng DB test riêng và dọn đúng tài nguyên test đã tạo.

## 2. Nguồn và hiện trạng cần giữ

Cập nhật theo quyết định dev ngày 18/11/2026 (chọn 1.A và 2.A): bộ lọc ở Việc được giao, Tra cứu tồn kho, Phiếu xuất và Chứng từ hoàn thành chuyển từ dropdown sang nút xoay vòng, cuối danh sách quay về lựa chọn đầu. Áp dụng lựa chọn ngay; tìm từ khóa sau 300 ms ngừng gõ, lọc ngày khi hợp lệ. Nút `Reset tìm kiếm` xóa từ khóa và toàn bộ bộ lọc/ngày, về trang 1; riêng Phiếu xuất giữ tab và ngữ cảnh `yeu_cau_san_xuat_id`. Admin/QLK giữ select và nút Lọc. Quyết định này thay mô tả dropdown của Nhân viên trong kế hoạch ban đầu.

Đọc `AGENTS.md`, `CLAUDE.md` và source hiện tại trước khi sửa. `CLAUDE.md` dẫn lại `AGENTS.md`. File cũ `doc/FRONTEND_RULES.md` không còn ở nhánh hiện tại; không tự tái tạo. Đối chiếu tài liệu frontend local nếu còn và các UC dưới đây. Không dùng superpowers.

| Nguồn | Sự thật hiện tại |
|---|---|
| `specs/use_cases/goods_issue/UC-34.md`, `UC-37.md` | Mỗi YCSX tối đa một phiếu xuất linh kiện và một phiếu xuất thành phẩm; có hai loại là đúng nghiệp vụ |
| `infra/postgres/init.sql` | Unique `(yeu_cau_san_xuat_id, loai_phieu)`; không sửa schema để làm ẩn phiếu |
| `frontend/src/features/production/RequestsPage.jsx`, `IssueLinks` | Đang map mọi phiếu cùng YCSX thành các link; đây là các phiếu liên quan, không tự kết luận dữ liệu trùng |
| `frontend/src/features/production/CompletionListPage.jsx` | Danh sách QLK mở cả yêu cầu cha; không bê cách mở này vào popup chi tiết chứng từ Nhân viên |
| `backend/app/modules/phieu_xuat/router.py` | GET danh sách chỉ QLK; GET theo yêu cầu/chi tiết có NV và kiểm tra phân công |
| `backend/app/modules/phieu_xuat/repository.py`, `list_issues` | Có tham số `employee_id` nhưng hiện chưa áp dụng vào query: **không chỉ truyền ID rồi cho rằng đã phân quyền** |
| `backend/app/modules/san_xuat/router.py`, GET danh sách chứng từ | Chỉ QLK; service cũng kiểm quyền QLK |
| `backend/app/modules/san_xuat/repository/chung_tu_hoan_thanh_sx.py` | Danh sách hiện loại chứng từ nháp; trang NV cần nhìn thấy bản nháp được phép quản lý |
| `specs/use_cases/identity_access/UC-08.md` | R3/AC-6 hiện cấm NV tự đổi mật khẩu: quyết định mới của dev cần được ghi rõ, giữ nguyên nghiệp vụ reset của Admin và giới hạn QLK |
| `frontend/src/features/auth/ProfilePage.jsx` | Hồ sơ hiện chỉ đọc, dùng chung các vai trò |
| `backend/app/modules/nhan_vien/service.py`, `reset_password` | Reset hiện chỉ Admin; đã có hash, transaction, audit và kiểm tra phiên theo phiên bản mật khẩu |

Giữ các sửa UI đang dở của phiên Flash cũ: dropdown Nhân viên, ngày dd/mm/yy, mã nghiệp vụ trong popup, loại việc hoàn thành khỏi KPI/badge và bỏ nội dung thừa. Sol đang review chúng; log test trước đó không chứng minh phiên bản của kế hoạch này đã đạt.

## 3. Thứ tự và quyền ghi

1. Phiên Flash cũ hoàn tất correction và bàn giao; Sol xác nhận baseline.
2. Flash mới đọc plan và audit source **read-only**, phản hồi lỗ hổng/đề xuất hợp đồng; không chạy server/test browser hoặc sửa source khi chưa được Sol chuyển quyền ghi.
3. Sau khi có quyền ghi: làm API đọc đúng quyền + test; rồi hai dashboard + chi tiết đúng ID; rồi đổi mật khẩu; cuối cùng kiểm thử tích hợp và tài liệu.
4. Sol review diff và bằng chứng; correction tiếp tục trong cùng phiên Flash mới. Không mở thêm agent/session. Không tự commit/push.

Không chạy hai writer hoặc hai Vite cùng port 5174. Bảo toàn `backend/Dockerfile` đang sửa từ trước, file SQL demo, ảnh và tài liệu chưa theo dõi.

## 4. Hợp đồng danh sách Nhân viên

Không mở rộng endpoint danh sách toàn kho của QLK cho NV. Bổ sung hai endpoint đọc dành riêng NV; đây là đường dẫn dự kiến, cần kiểm tra xung đột router trước khi chốt:

| Method/path dự kiến | Quyền và phạm vi |
|---|---|
| `GET /api/v1/phieu_xuat/cua_toi` | Chỉ NV hiện hành; phiếu thuộc các YCSX đang được giao cho NV đó, cùng phạm vi quyền xem chi tiết hiện tại |
| `GET /api/v1/chung_tu_hoan_thanh_sx/cua_toi` | Chỉ NV hiện hành; chứng từ của các YCSX đang được giao cho NV đó; gồm nháp, chờ duyệt, đã duyệt, từ chối |

- ID người xem lấy từ danh tính đã xác thực, không từ query/body. Khóa scope trong SQL trước COUNT, sort và OFFSET/LIMIT; filter không được thay thế scope. Không phân quyền ở frontend.
- Query dành cho NV không nhận `employee_id`/`nhan_vien_id` để chọn người xem; các trường không thuộc hợp đồng bị từ chối 422. Schema/query QLK giữ nguyên.
- Giữ nguyên danh sách QLK, bao gồm quy tắc QLK không xem chứng từ nháp trong danh sách hiện tại.
- Reuse schema/phân trang/query builder/service/repository hiện có ở mức tối thiểu. Không thêm dependency hoặc framework hợp đồng mới. OpenAPI do FastAPI sinh từ schema phải khớp fixture.
- Trả `data[]` + `meta` phân trang hiện có; trường đủ hiển thị mã phiếu/chứng từ, mã YCSX, ID liên kết, loại phiếu/yêu cầu, thành phẩm, số lượng, thời gian và trạng thái. Chỉ bổ sung các reference còn thiếu thực sự cần để render; không mở rộng dữ liệu nhạy cảm so với quyền chi tiết đang có.
- Bộ lọc chỉ dùng trường backend hỗ trợ: loại phiếu, trạng thái, YCSX và ngày; chứng từ dùng trạng thái/thành phẩm/loại yêu cầu/ngày nếu có. Hiển thị rõ ngày lập hay thời điểm hoàn thành theo đúng trường lọc. Không thêm ô tìm tên khi API chưa tìm tên.
- Không ghép danh sách bằng cách đọc toàn bộ YCSX rồi gọi từng phiếu/chứng từ (N+1); không lấy một trang làm tổng.
- Khai báo route tĩnh trước `/{id}` khi cần. Kiểm tra query lạ, lặp, ngày đảo, page size và GET body theo convention hiện tại.
- Truy vấn danh sách không ghi audit hay thay đổi trạng thái/tồn/giữ hàng.

## 5. Hai dashboard và chi tiết đúng ID

### Phiếu xuất

- Route danh sách dự kiến `/nv/phieu-xuat`. Cập nhật alias redirect hiện tại có cùng prefix để tránh route mới bị chuyển về Việc được giao.
- Hai tab loại phiếu có trạng thái chọn rõ, thao tác bàn phím và reset page khi đổi loại/filter.
- Cột: mã phiếu, mã YCSX, thành phẩm/mặt hàng, thời gian lập, trạng thái, **một** nút Xem chi tiết. Tên + mã nghiệp vụ theo quyết định đã chốt.
- Link chi tiết dùng **ID phiếu**, không dùng `mat_hang_id`, `yeu_cau_san_xuat_id`, chỉ số dòng hoặc SKU. Có thể reuse `/nv/xuat-nvl/:id` và `/nv/xuat-tp/:id` nếu popup không kéo thêm hồ sơ khác.
- `IssueLinks` trong popup yêu cầu: khi có phiếu đã lưu, chỉ hiện một CTA `Xem phiếu xuất` tới `/nv/phieu-xuat?yeu_cau_san_xuat_id=<ID yêu cầu>`. Khởi tạo và giữ bộ lọc này ở API, đổi tab, phân trang, F5 và quay lại; không lọc cục bộ theo tên/thành phẩm. Các nút **lập** phiếu khi đủ điều kiện vẫn giữ theo UC, không bị thay bằng thao tác xem.
- Phiếu mở phải đúng ID và loại; chỉ GET chi tiết phiếu đó và các reference cần thiết để kiểm quyền/hiển thị/thao tác. Không mở màn hình yêu cầu cha để giả làm chi tiết phiếu.
- Giữ Lưu nháp → Gửi, gửi lại khi bị từ chối, ETag và kiểm điều kiện theo UC. Không tự gửi khi bấm Xem; NV không có Duyệt/Từ chối.

### Chứng từ hoàn thành

- Route dự kiến `/nv/chung-tu-hoan-thanh/:id?`; thêm menu riêng. Reuse Collection/RecordPanel/Badge/ErrorNotice, không sửa danh sách QLK theo nhu cầu NV.
- Cột: mã chứng từ, mã YCSX, tên + mã thành phẩm, số lượng hoàn thành, thời điểm hoàn thành, trạng thái và **một** nút Xem chi tiết.
- Popup tải đúng **ID chứng từ** qua API chi tiết hiện có, không nhúng toàn bộ RequestsPage/IssueLinks hoặc danh sách phiếu của yêu cầu cha.
- Reuse phần trình bày/thao tác tối thiểu từ CompletionSection; giữ bất biến nội dung chứng từ và gửi/gửi lại đúng quyền, không tự thêm Sửa/Xóa/Trả nháp.

### Bất biến chung

- Khi đổi A → B, không hiện dữ liệu A dưới tiêu đề/URL B lúc đang tải; lỗi/404/403 không giữ dữ liệu hồ sơ trước.
- Chi tiết có thể hiển thị mã YCSX/reference liên quan trực tiếp; không lồng chi tiết hồ sơ khác hoặc thêm nút Xem hồ sơ khác trong popup đang chọn.
- Đóng/Escape trở về đúng dashboard, tab/filter/page và focus nút đã mở. Deep link, F5, Back/Forward và chuyển vai trò phải đúng.
- Ngày lọc Nhân viên giữ định dạng hiện tại dd/mm/yyyy, API ISO; nút xoay vòng và reset theo quyết định ngày 18/11/2026 ở mục 2; giao diện/mobile/focus theo đợt UI hiện tại. Không đổi định dạng Admin/QLK.
- Không xóa dữ liệu hoặc constraint để đạt yêu cầu chỉ hiện đúng một hồ sơ.

## 6. Nhân viên tự đổi mật khẩu

- UI đặt trong Hồ sơ/menu tài khoản của NV, không thêm một dashboard nghiệp vụ. Admin/QLK giữ UI/quyền hiện tại.
- Form: mật khẩu hiện tại, mật khẩu mới, nhập lại; nút hiện/ẩn mật khẩu có tên truy cập được; pending chặn gửi lặp; lỗi tại form, không lộ giá trị trong toast/confirm/URL/log.
- API dự kiến `POST /api/v1/nhan_vien/me/doi_mat_khau`, chỉ NV tự đổi; target luôn lấy từ actor. Body dự kiến chỉ `mat_khau_hien_tai`, `mat_khau_moi` dùng SecretStr; nhập lại là kiểm tra frontend. Dùng validation/password policy hiện tại (tối thiểu 6 ký tự), không trim mật khẩu, không tự đặt policy mới.
- Không dùng endpoint reset Admin cho NV và không nới quyền endpoint đó. Không chấp nhận ID tài khoản khác trong body/query.
- Service module nhân viên sở hữu cập nhật; reuse hash/verify hiện có. Khóa và kiểm lại credentials/trạng thái/phiên hiện hành; xác minh mật khẩu cũ với hash hiện hành trước ghi. Update hash + audit chung transaction. `repository.set_password_hash()` hiện đã tăng `phien_ban_dang_nhap`; reuse helper, không tăng thêm lần thứ hai.
- Sai mật khẩu hiện tại: HTTP **400**, code `mat_khau_hien_tai_khong_dung`, không đổi hash, không ghi audit thành công, không kết thúc phiên. Không dùng 401 cho trường hợp này vì `frontend/src/lib/api/client.js` tự kết thúc phiên khi request đã xác thực trả 401. Validate lỗi trả 422; chưa đăng nhập/phiên hết hạn 401; vai trò ngoài phạm vi 403.
- API self-change dùng credentials/row lock, không yêu cầu ETag của endpoint reset Admin. Frontend gọi `writeResource` với `versioned: false` một cách tường minh; mặc định `versioned: true` sẽ chặn request khi chưa có ETag. Không đổi mặc định của helper hoặc các thao tác reset/ghi khác.
- Thành công: response không chứa mật khẩu/hash/token; dự kiến 204. Mọi phiên cũ của NV bị vô hiệu theo cơ chế phiên bản credentials hiện có; xóa cache/auth frontend và về đăng nhập với thông báo thành công. Kiểm chứng cơ chế thực tế, không chỉ gọi logout tại tab hiện tại.
- Không cần đổi schema/bootstrap SQL hoặc thêm migration cho khả năng này. Nếu phát hiện cần thay đổi schema ngoài dự kiến, dừng phần phụ thuộc và báo Sol.

## 7. Kiểm chứng và tiêu chí nghiệm thu

### Backend trên DB test riêng

- Hai NV A/B, QLK và Admin: danh sách NV A không chứa dữ liệu NV B kể cả query giả người khác/ID yêu cầu khác; COUNT/page/sort đúng trên nhiều trang; bản nháp NV có, danh sách QLK vẫn giữ quy tắc cũ; đọc không đổi DB.
- Cùng một thành phẩm có hai YCSX, hai loại phiếu và nhiều chứng từ ID khác nhau: uniqueness mỗi loại được giữ; đọc chi tiết ngoài scope bị chặn.
- Đổi mật khẩu: sai mật khẩu hiện tại, token hết hạn, vai trò sai, body có ID khác, password ngắn, lặp submit/concurrent request; thất bại không đổi hash/audit/session.
- Thành công đổi được mật khẩu, mật khẩu cũ đăng nhập thất bại, mật khẩu mới thành công, token của hai phiên cũ đều không dùng được. Audit không có mật khẩu/hash; lỗi audit rollback cả cập nhật.
- Admin reset và QLK bị cấm tự đổi vẫn đúng; giữ test cũ, cập nhật những assertion cấm NV tự đổi theo quyết định mới với lý do rõ ràng.

### Frontend fixture + browser

- Dữ liệu cố tình có `mat_hang_id` giống nhau, YCSX ID khác nhau và ID phiếu/chứng từ khác YCSX ID. Mỗi dòng một nút; click/F5/back mở đúng ID, không hiện mã/chi tiết/nút hồ sơ khác.
- Với YCSX có cả phiếu linh kiện và thành phẩm: popup YCSX chỉ có một CTA xem phiếu; dashboard đích lọc đúng YCSX ở cả hai tab, không có phiếu của YCSX khác; mỗi dòng mở riêng đúng ID. Giữ nguyên hai bản ghi và unique mỗi loại.
- Hai tab phiếu, filter, phân trang, ngày ISO, nút xoay vòng và quay về đầu, reset hủy tìm kiếm đang chờ và xóa được ngày nhập dở/sai, mobile375px, loading/empty/error/403/404, chuyển A→B chậm, keyboard/Escape/focus-return.
- Đổi mật khẩu đúng/sai, nhập lại không khớp, pending/double-click, lỗi giữ form hợp lý và thành công logout. Không lưu secrets vào storage/test artifacts.
- Danh sách/chỉ xem không phát sinh POST; chỉ xác nhận hành động mới ghi. ETag/412/428 và quyền duyệt không bị suy yếu.
- Hồi quy Admin/QLK và các chỉnh UI đang dở, đặc biệt ngày bốn chữ số, select hiện tại, menu và profile theo vai trò.

Lệnh dự kiến: `npm --prefix frontend run test`, lint, build; Playwright các file mới và employee/navigation/sidebar/record-dialog/workflow liên quan. Backend pytest/Ruff theo module thay đổi, integration dùng PostgreSQL test đã tách biệt. Chỉ mở rộng test khi thay đổi/lỗi thực tế cần; không cài dependency hoặc dùng DB app để làm xanh test.

## 8. Tài liệu, review và bàn giao

- Cập nhật UC quyết định mới có ngày/nguồn dev; không mô tả self-change như quyền đã có từ main. Giữ phạm vi reset Admin/QLK rõ ràng.
- Mỗi endpoint thêm/sửa cập nhật đúng `docs/sequence/phieu_xuat.md`, `docs/sequence/san_xuat.md`, `docs/sequence/nhan_vien.md`; từng endpoint có method/path và sequenceDiagram gồm auth, validation, scope/transaction/audit, lỗi chính. Kiểm cú pháp Mermaid nếu có sẵn; nếu chưa render được báo rõ.
- Cập nhật `doc/MISSING.md` với trạng thái endpoint/dữ liệu còn thiếu và bằng chứng đã thực chạy. Tách thiếu chức năng khỏi kiểm chứng chưa làm; không tự đánh dấu human acceptance/E2E toàn hệ thống.
- Ghi command, exit code, số test và log path của **phiên bản cuối**. Log cũ 122/117/103 hoặc 297/298 chỉ là lịch sử; không cộng nhầm hoặc dùng thay kiểm chứng thay đổi mới.
- Reviewer Sol kiểm security/scope/ID isolation/busy-error/permission và diff shared components. Chỉ sau correction + kiểm chứng mới báo hoàn tất; commit/push/accept phải chờ dev yêu cầu riêng.

## 9. Nội dung còn cần audit, không phải quyền tự mở rộng

- Chốt tên/đường dẫn cuối của hai GET scoped và API self-password sau kiểm tra router/OpenAPI; không thêm endpoint ngoài ba hợp đồng cần thiết.
- Chốt cách phân trang/filter tối thiểu theo schema hiện hữu và trường tham chiếu cần bổ sung; dữ liệu ngoài quyền không được giải bằng cách gọi API QLK từ NV.
- Nếu fixture/UC/source còn mâu thuẫn, ghi cụ thể và hỏi Sol trước sửa phần phụ thuộc. Không đổi dữ liệu hoặc bỏ test để che mâu thuẫn.
