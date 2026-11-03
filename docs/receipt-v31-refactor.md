# Refactor phiếu nhập v3.1

> **C?p nh?t h?p nh?t v?o main ? 03/11/2026:** N?i dung d??i ??y l? l?ch s? nh?nh `feature-phieu_nhap`, kh?ng ph?i h??ng d?n ?p d?ng hi?n t?i. Ph?m vi ?? ch?t: gi? endpoint kh?c theo main; ch? t?ch h?p s?u API phi?u nh?p v? ph?n n?i b? c?n thi?t. D?ng schema PascalCase trong `infra/postgres/init.sql`; kh?ng t?o/ch?y migration, kh?ng s?a schema/seed c?a main, kh?ng chuy?n ngu?n ??c API inventory, kh?ng kh?i ph?c `/receiving`. Audit v?n gi? quy?n/projection c?a main; `CreationAudit.du_lieu_sau` n?i b? cho ph?p null ?? x?a nh?p. Lu?ng ho?n t?t ??i tr?ng th?i tr??c INSERT `GiaoDichKho` trong c?ng transaction ?? ??p ?ng trigger. S? ?? hi?n t?i: [sequence/phieu_nhap.md](sequence/phieu_nhap.md). C?c k?t qu? test/?nh ph?a d??i thu?c nh?nh c?; test c? ???c gi? ?? dev t? x? l?.

Ki?m ch?ng h?p nh?t b?ng script ri?ng `.handoff/verify-phieu-nhap-merge.py`: import/ORM/OpenAPI s?u route; t?o, ??c, s?a, x?a, ho?n t?t tr?n database PostgreSQL m?i ri?ng c? h?u t? `_test`; ti?n/ETag/If-Match, ph?n quy?n Q, retry kh?ng nh?n ??i giao d?ch, audit v? rollback khi audit l?i ??u ??t. To?n b? ghi th? nghi?p v? rollback; kh?ng ghi database ?ng d?ng. Kh?ng s?a test c? ?? ph? h?p ki?n tr?c m?i.

## A. Phân tích và quyết định trước khi sửa

Nhánh: `feature-phieu_nhap`. Working tree sạch khi bắt đầu. Không tìm thấy ERD v3.1 trong repository; đã đọc bản người dùng cung cấp tại `C:/Users/Bao/Downloads/xbike_mrp_data_model_v3.1_mermaid.md` và yêu cầu tác vụ đính kèm.

Hiện trạng: router có sáu endpoint `/phieu_nhap` và ba route legacy `/receiving`; chỉ Q dùng contract mới. Service đã xử lý JWT/role qua dependency, If-Match, khóa phiếu/chi tiết, replay hoàn tất, đối chiếu ledger và audit cùng transaction. Hoàn tất hiện đọc/khóa/cộng `ton_kho`, có bộ cấp ID dòng tồn. Phiếu và chi tiết dùng ID không tự tăng; thiếu ngày nhập/ghi chú, cho phép NULL người lập/NCC/thời gian cũ và tiền INTEGER. Repository cấp ID/mã dựa MAX và snapshot audit. Alembic có hai revision trạng thái nhân viên, chưa có migration nghiệp vụ phiếu nhập.

Người dùng chốt trong tác vụ này:

1. Giữ tên bảng snake_case; nâng cấu trúc và nghiệp vụ tương ứng v3.1. Không đổi tên toàn schema.
2. Tiền API trả chuỗi Decimal chính xác, chuẩn hai chữ số sau dấu chấm.
3. `/inventory/stock` đọc từ `mat_hang`, giữ field cũ, ID dòng tồn bằng ID mặt hàng; giữ bảng `ton_kho` cũ để đối soát, không xóa.
4. Migration dừng nếu thiếu ngày nhập thực tế của phiếu cũ. Không suy ra ngày nhập từ ngày tạo.

Kế hoạch: bổ sung cột số dư vào mặt hàng; nâng phiếu/dòng lên IDENTITY, DATE/ghi chú và numeric(18,2); giữ API paths/envelope/quyền, bổ sung các field bắt buộc. Chuyển hoàn tất sang khóa mặt hàng theo ID tăng dần, cộng số dư và ghi ledger/trạng thái/audit chung transaction. Chỉ giữ khóa cấp mã PN, không tự cấp ID phiếu/dòng/tồn. Migration kiểm tra số dư với ledger và chuyển tồn cũ; dữ liệu thiếu chủ phiếu/NCC/ngày nhập thực tế hoặc lệch ledger phải dừng để đối soát. Chỉ chuyển kiểu ngày tạo từ UTC không offset sang TIMESTAMPTZ, không dùng ngày tạo thay ngày nhập. Không chạy migration trên database ứng dụng.

Phụ thuộc: `inventory/stock` còn đọc StockLevel; chuyển nguồn đọc theo quyết định trên. `StockLevel`/bảng cũ giữ để phục vụ đối soát, không còn là nguồn số dư hiện hành. Phiếu xuất, sản xuất và điều chỉnh/ticket không được viết lại trong tác vụ này. Các facts tên `ton_kho` trong pure rule engine là dictionary số dư, không phải truy vấn bảng.

Kiểm thử dùng PostgreSQL 16 trong container tạm riêng, tmpfs, cổng 55451, database `xbike_receipt_v31_test`. Các bài cần khóa/transaction/concurrency phải dùng nhiều connection PostgreSQL thật. Không mock thay thế tính chất của database.

## B. Thay đổi đã triển khai

Luồng giữ nguyên: tạo nháp → sửa nháp → hoàn tất → cộng tồn → ledger → audit. Mọi bước ghi sổ dùng một session/transaction. Khóa phiếu/chi tiết trước, khóa mặt hàng theo ID tăng dần; đối soát số dư với tổng ledger trước khi cộng. Replay hoàn tất trả ID ledger cũ và `da_ghi_so_truoc_do=true`, không cộng tồn hay ghi audit lần hai. Quyền Q, JWT/active/password-version, ETag/If-Match và các đường dẫn chính giữ nguyên.

| File | Vai trò và thay đổi |
|---|---|
| `backend/app/modules/phieu_nhap/models.py` | ORM phiếu/chi tiết: IDENTITY, creator/NCC bắt buộc, DATE/ghi chú, Decimal numeric(18,2), created_at có múi giờ. |
| `backend/app/modules/phieu_nhap/schemas.py` | Validate NCC/ngày, chi tiết duy nhất, số lượng >0; Decimal không dùng float, giới hạn numeric(18,2); OpenAPI đúng integer/string đầu vào và string đầu ra. |
| `backend/app/modules/phieu_nhap/service.py` | Ghi ngày/ghi chú, lấy creator từ JWT, tính tổng server kể cả route cũ; cập nhật schema khi kiểm tra nháp trước ghi sổ. |
| `backend/app/modules/phieu_nhap/repository.py` | Bỏ cấp ID MAX; database sinh ID; giữ khóa mã tháng và lịch sử mã; khóa mặt hàng FOR UPDATE, lọc created_at theo kiểu có múi giờ. Hết sequence trả 409. |
| `backend/app/modules/catalog/models.py` | Thêm `so_luong_ton` mặc định 0/CHECK không âm và `ton_kho_updated_at` có múi giờ. |
| `backend/app/modules/inventory/repository.py` | Hoàn tất cập nhật mặt hàng, không dùng StockLevel; API stock đọc projection từ mặt hàng, giữ tên field/phân trang. |
| `backend/migrations/versions/20261103_receipt_v31.py` | Alembic kiểm tra dữ liệu, chuyển số dư/thời gian UTC, nâng kiểu/nullable/identity, giữ toàn bộ bảng tồn cũ. Không suy ra ngày nhập. |
| `infra/postgres/init.sql` | Bootstrap cấu trúc mới trên database trống; giữ tên bảng và schema nghiệp vụ ngoài phạm vi. |
| `infra/postgres/seed.sql` | Phiếu mẫu có ngày nhập; tồn đầu kỳ ghi vào mặt hàng từ ledger; đối soát đúng nguồn mới, đồng bộ sequence. |
| `backend/tests/test_phieu_nhap_api.py` | Regression API đọc/tạo, validation, phân quyền, mã tháng, sequence và transaction. Payload/giá trị mong đợi nâng theo contract mới. |
| `backend/tests/test_phieu_nhap_actions.py` | Regression sửa/xóa/hoàn tất/replay, row lock, concurrent requests, ledger và rollback số dư mặt hàng. Trường hợp ID tồn cũ hết dải không còn áp dụng. |
| `backend/tests/test_supplier_writes.py` | Fixture phiếu tham chiếu NCC thêm creator/ngày bắt buộc; không thay quy tắc NCC. |
| `backend/tests/test_auth_migrations.py` | Test riêng auth dừng tại revision auth, thay vì chạy head nghiệp vụ trên schema chỉ có nhân viên; kiểm tra head mới nằm trong test migration phiếu nhập. |
| `backend/tests/test_receipt_v31.py` | Test các field mới, tiền chính xác/giới hạn, ngày, IDENTITY thực tế, route cũ tính tiền và hoàn tất khi không có bảng tồn cũ. |
| `backend/tests/test_receipt_v31_migration.py` | Chạy Alembic thật trên PostgreSQL: dữ liệu cũ, từ chối dữ liệu sai và rollback schema, actual init/seed và luồng tạo/hoàn tất, bảo vệ downgrade. |
| `.gitignore` | Cho phép Git theo dõi hai file test mới. |
| `docs/sequence/phieu_nhap.md` | Cập nhật cả 9 endpoint và luồng khóa/số dư/schema. |
| `docs/sequence/inventory.md` | Tài liệu 3 endpoint inventory; ghi rõ POST movements đang trả 501, chưa triển khai. |
| `docs/phieu-nhap-api-verification.md` | Đánh dấu báo cáo 22/10 là lịch sử, dẫn sang báo cáo v3.1 để tránh dùng payload cũ. |
| `docs/receipt-v31-refactor.md` | Báo cáo phân tích, thay đổi, tương thích, kiểm chứng và triển khai. |

### Thay đổi contract cần frontend cập nhật

| Endpoint/phạm vi | Thay đổi |
|---|---|
| `POST /api/v1/phieu_nhap` | Bắt buộc `ncc_id` không NULL và `ngay_nhap` YYYY-MM-DD; thêm `ghi_chu` tùy chọn. |
| `PATCH /api/v1/phieu_nhap/{id}` | Có thể sửa ngày/ghi chú; omission giữ nguyên. `ncc_id:null` và `ngay_nhap:null` trả 422; `ghi_chu:null` xóa ghi chú. |
| Mọi response `/phieu_nhap` và `/receiving` có resource | Thêm ngày/ghi chú; `tong_tien`, `don_gia_thuc`, `tong_gia` đổi từ number sang string hai chữ số thập phân, hoặc NULL khi tiền cũ chưa có. NCC/creator không còn NULL sau migration. |
| `POST /api/v1/receiving` | Giữ `items`, mã do client gửi, quyền A/Q/N và response trực tiếp; bắt buộc NCC/ngày, ít nhất một dòng có giá, không nhận dòng trùng/sai loại/inactive. Tổng dòng/tổng phiếu tính lại; creator client bị ghi đè bằng JWT. |
| Request giá trong cả hai POST và PATCH | Nhận chuỗi Decimal hoặc integer, từ chối float/bool, âm, quá hai chữ số thập phân hoặc vượt numeric(18,2). Frontend nên gửi chuỗi; không tính tiền bằng JS floating point. |
| `GET /api/v1/inventory/stock` | `id` bằng ID mặt hàng, `mat_hang_id` giữ nguyên; danh sách gồm cả mặt hàng tồn 0; updated_at có offset. Không coi ID này là PK của ton_kho cũ. |
| ETag | Schema resource mới làm ETag thay đổi; frontend GET lại trước PATCH/DELETE/hoàn tất. |

Không đổi endpoint, HTTP method, envelope, mã lỗi hay quyền endpoint. `tu_ngay/den_ngay` tiếp tục lọc **created_at** theo ngày Việt Nam, không tự đổi sang ngày nhập.

Ví dụ tạo nháp:

```json
{
  "ncc_id": 1,
  "ngay_nhap": "2026-11-03",
  "ghi_chu": "Nhập bổ sung",
  "chi_tiet": [{"mat_hang_id": 1, "so_luong": 3, "don_gia_thuc": "12500.50"}]
}
```

Tổng server trả `"37501.50"`; lấy ID/mã/Location/ETag từ response 201. Hoàn tất gửi `{}` và If-Match đã nhận. Draft không đổi tồn hay ledger.

## C. Kiểm chứng

Chạy đầy đủ ngày 03/11/2026: **335 passed, 1 failed, 54.46 giây**, không có test skip. Toàn bộ 37 test mới v3.1 (24 API/schema + 13 migration) nằm trong lượt chạy này và đều đạt. Test dùng DB riêng có hậu tố `_test`, schema ngẫu nhiên và rollback/cleanup. Test concurrent dùng nhiều connection PostgreSQL thực; subclass chỉ đặt barrier/chèn lỗi, không thay database bằng mock.

Test thất bại: `tests/test_auth_api.py::test_legacy_login_endpoints_issue_revocable_tokens`, dòng 261. Test gọi `POST /api/v1/auth/login` mong 200, nhưng router hiện không đăng ký `/login` nên trả 404. Lỗi này đã tồn tại trước thay đổi phiếu nhập và không được bỏ qua/skip hay sửa test để che lỗi. Route đăng nhập chính `/dang_nhap` vẫn được kiểm tra trong các test auth/API. Đây là điểm cần xử lý riêng ở module auth; không khẳng định toàn bộ suite/CI đã xanh.

Ruff lint đạt trên các file code/test thay đổi, formatter check đạt trên 12 file được định dạng, `git diff --check` đạt. Mermaid CLI đã render thành công 9 sơ đồ phiếu nhập + 3 sơ đồ inventory. Script map_structure không phát hiện cycle/misplacement trong vùng phiếu nhập; các cấu trúc router giống nhau được giữ vì thuộc module nghiệp vụ khác. `check_boundaries.py` không chạy được phép kiểm lớp vì repository chưa khai báo block `clean-architecture`; đã đối chiếu import thủ công: service dùng ports, SQL và ORM nằm trong repository/model, không thêm vòng phụ thuộc. Mức rủi ro HIGH do có migration và concurrency.

- Validation, quyền Q và tài khoản bị khóa; 401/403/404/409/412/422/428; filter/sort/phân trang và GET không ghi dữ liệu.
- Decimal `0.10 × 3 = 0.30`, tiền vượt INTEGER nhưng hợp lệ numeric, giá cực đại và từ chối vượt độ chính xác/âm/NaN/float.
- IDENTITY thật: đặt sequence ở giá trị khác MAX rồi kiểm tra ID API; mã tháng và xóa/tạo không tái sử dụng ID/mã.
- Cùng phiếu hoàn tất đồng thời chỉ ghi sổ một lần; sáu phiếu cùng mặt hàng tổng tồn 18, sáu ledger và 12 audit (tạo + hoàn tất).
- Chèn lỗi sau cập nhật số dư, ledger, trạng thái và audit: tất cả rollback, retry thành công; phiếu hoàn tất không sửa/xóa trực tiếp.
- Alembic giữ ngày nhập thực tế đã cung cấp, chuyển số dư/thời gian/tiền/sequence; thiếu ngày/creator/NCC/thời gian, âm/lệch số dư hoặc tiền sai thì dừng, không giữ lại DDL dở dang.
- Chạy init.sql/seed.sql thật trong schema test, chạy migration, tạo và hoàn tất phiếu bằng service với SQL này. Bảng ton_kho giữ trống, số dư mặt hàng và ledger khớp.
- Hoàn tất và đọc tồn vẫn thành công khi bảng ton_kho bị bỏ **chỉ trong schema test rollback**, chứng minh luồng mới không phụ thuộc bảng này.

Lệnh kiểm thử từ `backend`, sau khi đặt `TEST_DATABASE_URL` tới PostgreSQL test riêng:

```powershell
..\.venv\Scripts\python.exe -m pytest -q --tb=short
```

## D. Áp dụng migration và giới hạn

Revision mới `20261103_receipt_v31` nối sau `20261018_auth_status`. Migration **chưa chạy trên database ứng dụng**. Không xóa volume, không seed lại database có dữ liệu. Sửa init.sql/rebuild container không tự nâng database đã khởi tạo.

Trước khi triển khai: sao lưu và kiểm tra khả năng restore, dừng mọi writer/backend cũ, xác nhận database/schema đích, đối soát tồn với ledger. Database cũ có phiếu nhưng chưa có cột ngày phải được bổ sung **DATE và mapping ngày nhập thực tế do nghiệp vụ xác nhận** trước khi upgrade; không tự dùng ngày tạo hoặc ngày hiện tại. Không tạo mapping giả cho creator/NCC/thời gian bị thiếu. Việc bổ sung/sửa dữ liệu thực tế cần một kế hoạch được dev duyệt riêng.

Migration lấy ACCESS EXCLUSIVE lock, timeout chờ khóa 10 giây. Không có chế độ offline `--sql` vì phải đọc/kiểm tra dữ liệu thực. Trên bản sao đã đối soát và được phép nâng cấp, chạy Alembic từ backend với DATABASE_URL trỏ đúng môi trường:

```powershell
..\.venv\Scripts\python.exe -m alembic current
..\.venv\Scripts\python.exe -m alembic upgrade head
```

Không chạy lệnh upgrade khi chưa bổ sung ngày/khắc phục lỗi preflight. Auth revision trước đó cũng có thể dừng nếu trạng thái nhân viên cũ không hợp lệ; refactor này không tự mở khóa tài khoản.

Rollback: migration cố ý chặn downgrade tự động vì ton_kho là archive và tiền có thể đã có phần lẻ. Trước khi có giao dịch mới, restore bản backup nhất quán và rollback code cùng nhau. Sau cutover có ghi mới, phải xuất/đối soát và có kế hoạch chuyển ngược số dư/tiền được duyệt; không chỉ revert code hoặc lấy ton_kho cũ làm tồn hiện tại. ID sequence có thể có khoảng trống sau rollback; đây là tính chất bình thường, không được reset để lấp chỗ trống.

Chưa đổi nghiệp vụ phiếu xuất/sản xuất/điều chỉnh/ticket. Chỉ nâng cột thuộc phiếu nhập và số dư mặt hàng; timestamp ledger/audit cùng schema nghiệp vụ khác giữ kiểu hiện hành, chưa phải chuyển toàn bộ ERD sang v3.1. Trong code hiện tại không còn repository runtime đọc/ghi ton_kho ngoài mapping StockLevel giữ để đối soát. Tên facts `ton_kho` trong pure rule engine là dictionary, không phải truy vấn bảng. Tích hợp/SQL ngoài repository chưa được kiểm chứng; không đề xuất xóa bảng cũ ở đợt này. POST inventory/movements và một số workflow khác đang 501 từ trước, không được triển khai ngầm trong tác vụ này. Đóng ticket không tự chỉnh tồn.

BA đã chốt cách xử lý ngày thiếu là dừng; phần còn cần cung cấp khi nâng DB thật là mapping ngày nhập/creator/NCC bị thiếu và phương án xử lý chênh lệch số dư thực tế. Chưa có kiểm chứng trên dữ liệu ứng dụng thật. Frontend chưa sửa trong tác vụ backend này, cần cập nhật các contract nêu trên.

## E. Git

Đề xuất:

```text
refactor(phieu-nhap)!: align receipts and item stock with data model v3.1

BREAKING CHANGE: require supplier and receipt date, serialize receipt money as decimal strings, and read stock balances from items.
```

Không commit, push hoặc stage thay đổi.
