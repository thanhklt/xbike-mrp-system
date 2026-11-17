# Đặc tả backend Catalog — UC-09–UC-14 và UC-44

**SPEC APPROVED — dev đã duyệt Q2–Q6 ngày 14/11/2026; Q1 đã được giải quyết bằng pull BOM.**
**PLAN APPROVED - backend implemented; verification and trace below.**

Khảo sát ban đầu ngày 14/11/2026 tại `feature/bom`, HEAD `f461ecd`; kiểm tra lại sau
dev pull BOM tại `feature/catalog`, HEAD `b9e1020`. Phạm vi yêu cầu:
cả bảy UC trong thư mục `catalog`, chỉ backend; frontend để sau. Dev đã duyệt spec,
Q2–Q6 và plan/task qua hai cổng xác nhận riêng trước khi triển khai. Khảo sát ở
mục 2 là snapshot trước triển khai; kết quả hiện tại và truy vết nằm ở mục 6–7.

## 1. Mục tiêu, nguồn và ranh giới

Hoàn thiện tra cứu/tạo/sửa mặt hàng, ngừng/dùng lại thành phẩm; tra cứu/tạo/sửa nhà
cung cấp. Kế thừa quy tắc công thức một cấp, integer VND, audit qua service, giao
dịch nguyên tử và bảo vệ dữ liệu của quá trình BOM trước đó. Giữ nguyên các UC,
R và AC gốc; phần bổ sung backend ở cuối mỗi UC và tài liệu này để review riêng.

| Nguồn đã đọc | Nội dung dùng đối chiếu |
|---|---|
| [UC-09](UC-09.md), [UC-10](UC-10.md), [UC-11](UC-11.md), [UC-12](UC-12.md) | Tra cứu, tạo/sửa mặt hàng, trạng thái thành phẩm |
| [UC-13](UC-13.md), [UC-14](UC-14.md), [UC-44](UC-44.md) | Nhà cung cấp, mọi thông tin bắt buộc, mã tự cấp, no-op và thông tin hiện tại trên phiếu nhập |
| [BR-GIAIDOAN1](../../business_requirements/BR-GIAIDOAN1.md) | BR-001/003/004/005/007/008/010/012/016 |
| [Model v4](../../entity_model/data_model_v4.md) §3.2–3.3, §4.4 | MatHang/NhaCungCap/Bom, số dư và các ràng buộc |
| [SQL bootstrap](../../../infra/postgres/init.sql) | Identity, mã trigger, NOT NULL/check/unique/FK, cột tồn sinh tự động |
| [UC-16](../bom/UC-16.md), [UC-18](../bom/UC-18.md), [UC-19](../bom/UC-19.md) | Phụ thuộc công thức và trạng thái cùng transaction |
| Source `mat_hang`, `nha_cung_cap`, dependency/auth/transaction/audit; DTO/repository phiếu nhập | Hành vi đang có, khác biệt với UC và phạm vi tích hợp cần hỏi |

Không thay đổi bootstrap/seed/migration hoặc database ứng dụng. Chưa xác minh schema
database đang chạy; đối chiếu schema trong bước này là đối chiếu file SQL trong repo.
Không tái áp dụng quyết định cũ cho phép tên NCC null hoặc ID cấp tay khi đặc tả v4
đã chốt NOT NULL/Identity; các thay đổi tương thích phải nêu trong plan trước sửa ORM/API.

## 2. Khảo sát hiện trạng (chỉ đọc)

### 2.1. Trạng thái checkout và baseline

- Ban đầu working tree sạch tại `f461ecd`, chưa có phần BOM mới. Dev sau đó đã pull
  commit `b9e1020` vào nhánh `feature/catalog`; các source, bốn file test BOM/tích hợp,
  spec và artifact BOM hiện đã có. Các sửa spec Catalog đang có được giữ nguyên.
- Q1 về thiếu source BOM đã giải quyết; tái sử dụng phần tích hợp UC-10/12 hiện có,
  không cần khôi phục hoặc triển khai lại toàn bộ module BOM.
- **R00 — đã sửa theo xác nhận riêng của dev ngày 14/11/2026:** bản pull thiếu
  `@asynccontextmanager`. Reproducer không dùng DB trả `TypeError: 'async_generator'
  object does not support the asynchronous context manager protocol`. Các action ghi
  gọi `async with self.mutation.scope()` bị chặn. Ruff cũng báo F401 import decorator
  chưa dùng. Dev đã cho phép thêm lại đúng decorator; source chỉ sửa một dòng.
  Chạy lại bốn file test BOM/tích hợp với PostgreSQL test riêng: **105 pass trong
  16,79 giây, không skip/fail**. Ruff check/format và mypy file mutation đều đạt.
- Stack thực kiểm tra: FastAPI 0.144.0, Pydantic 2.14.1, SQLAlchemy 2.1.5;
  async Python/asyncpg, PostgreSQL; pytest, pytest-asyncio, Ruff, mypy theo pyproject.
- Baseline trước pull, `python -m pytest tests -q --tb=line` từ backend: **8 failed**, tất cả tại
  fixture `test_nhan_vien_create_code.py:86` thiếu trường bắt buộc `VaiTroRead.mo_ta`.
  Sau pull đã có test BOM và `test_mat_hang_bom.py` để tái sử dụng.
- Trước sửa R00: `pytest tests/test_bom_service.py -q` **22 pass**. Sau sửa đã xác
  nhận lại **105 test BOM/tích hợp/PostgreSQL pass** trên source vừa pull, không dùng
  kết quả lần bàn giao trước thay bằng chứng kiểm tra mới. Không dùng DB ứng dụng.
- Chạy lại suite không cấu hình URL PostgreSQL test: **24 pass, 8 fail, 81 skip**.
  81 ca phụ thuộc fixture DB được skip, không phải pass; 8 lỗi vẫn là fixture nhân
  viên thiếu `mo_ta`. Đây là kết quả trước sửa và trước cấu hình DB test; không thay
  thế lượt 105 pass với PostgreSQL test riêng sau sửa. Không sửa lỗi nền nhân viên.
- PostgreSQL recheck chạy tmpfs tại cổng 55464, database `bom_<uuid>_test` mới/trống
  mỗi case, bootstrap bằng SQL thực và dọn đúng tài nguyên test sau chạy. Không
  dùng/xóa/seed/reset database hoặc volume ứng dụng. Không commit/push.
- Import app và sinh OpenAPI thành công, không chạy lifespan/kết nối DB ứng dụng.
  Điều này không chứng minh API truy vấn/lưu đúng trên SQL v4.

### 2.2. Endpoint thực tế

| Method/path đang có | Service/luồng hiện tại | Phần thiếu so với UC |
|---|---|---|
| GET `/api/v1/danh_muc_mat_hang/` | `MatHangReader.danh_muc` đọc cache, QLK/NV | QTV bị chặn; DTO thiếu hai số đang giữ/còn dùng |
| GET `/api/v1/mat_hang` | `MatHangReader.list_mat_hang` + `filter_items`, hai loại, page/filter/sort trên cache | QTV bị chặn; từ khóa còn tìm SKU và coi `%/_` là wildcard |
| GET `/api/v1/mat_hang/{id}` | `MatHangReader.get_mat_hang` → BomService.item_detail đọc DB; strong ETag có ngữ cảnh BOM | QTV bị chặn; DTO chưa trả hai số đang giữ/còn dùng |
| POST `/api/v1/mat_hang` | `MatHangService.create_mat_hang` đã tạo kèm v1, mã server cấp, hai loại | Phụ thuộc đã có; R00 đã sửa, test tích hợp pass; tái sử dụng và bổ sung AC Catalog còn thiếu |
| PATCH `/api/v1/mat_hang/{id}` | `MatHangService.patch_mat_hang`, strong If-Match dưới khóa; mã/loại cấm sửa, phối hợp trạng thái Bom | R00 đã sửa; các field gửi lên nhưng giá trị không đổi vẫn có thể ghi audit; SKU cần Q2 |
| DELETE `/api/v1/mat_hang/{id}` | Ngừng mềm bằng `delete_mat_hang`, chỉ TP, đồng bộ Bom/audit | Phụ thuộc nghiệp vụ đã có, test BOM/tích hợp pass sau sửa R00 |
| GET `/api/v1/nha_cung_cap` | `SupplierService.list_suppliers`, SQL lọc AND/page/sort | Chỉ QLK, chưa cho QTV đọc |
| GET `/api/v1/nha_cung_cap/{id}` | `SupplierService.get_supplier` | Chỉ QLK; chưa ETag cho PATCH mới |
| POST `/api/v1/nha_cung_cap` | `SupplierService.create_supplier` | Nhận mã client, cho thiếu thông tin, cấp ID thủ công |
| PATCH `/api/v1/nha_cung_cap/{id}` | **Chưa có** | UC-44 chưa triển khai |

NCC không có DELETE hiện tại; giữ đúng BR/UC không xóa. Danh mục mặt hàng phụ trợ
đang tồn tại phải được đánh giá cùng UC-09, không tự gỡ endpoint đang được client dùng.
Đường dẫn/DTO/headers đích cụ thể sẽ trình ở plan sau khi spec được duyệt.

### 2.3. Phân tầng và dữ liệu

- Router dùng schema/dependency để nhận HTTP; service điều phối repository. Service
  chưa có đủ guard quyền nghiệp vụ khi được gọi trực tiếp; hiện quyền chủ yếu ở router.
- Mặt hàng/BOM đã dùng `MatHangMutation`: cache lock → transaction → prepare →
  commit → publish. Có `MatHangSynchronizer` LISTEN/NOTIFY và reconcile; giữ cơ chế
  này, tránh tạo cache thứ hai hoặc công bố cache trước commit.
- Mặt hàng ghi qua AuditService trong DI, NCC đang nhận trực tiếp
  SqlAlchemyAuditRepository. Luồng NCC cần đi qua AuditService trong cùng transaction.
- MatHang ORM đã đồng bộ hai loại, số đang giữ/cột sinh/created_at v4; truy vấn
  tham chiếu đã bỏ các bảng legacy không có trong SQL. MatHangRead vẫn chưa công khai
  số đang giữ/còn dùng; cần bổ sung DTO và các nguồn đọc/cache, không làm lại ORM đã có.
- NCC ORM đang là lớp `Supplier` map bảng `NhaCungCap`, ID không tự tăng và cho các
  trường nullable. V4 có Identity, created_at, mọi thông tin NOT NULL/nonblank, mã
  do trigger cấp và bất biến. Phải đồng bộ lớp `NhaCungCap` cùng các import trực tiếp.
- NCC query đang tìm literal không phân biệt hoa/thường trên mã/tên, tỉnh/phường
  so sánh bằng; input hiện strip khoảng trắng. Mặt hàng đang tìm thêm SKU và wildcard.
  UC chưa chốt đầy đủ nghĩa của chuỗi tìm kiếm; xem Q2/Q3.
- Phiếu nhập hiện chỉ trả `ncc_id`; chưa có DTO thông tin NCC hiện tại. UC-44/AC-8
  không được coi là đạt chỉ vì FK còn nguyên. Cần phần đọc tích hợp tại Q6.
- Phiếu xuất/sản xuất còn code cũ. Không tự refactor chúng để nghiệm thu giá tại
  lúc duyệt, giữ hàng hoặc tiếp tục yêu cầu đã gửi; các AC đó phải ghi phụ thuộc rõ.

## 3. Phạm vi nghiệp vụ đích

### 3.1. UC, actor, trigger và kết quả

Main flow và alternative flows gốc nằm trong từng UC đã liên kết ở §1. Phần sau
chuyển chúng thành điều kiện backend có thể kiểm thử, không thay quy tắc gốc.

| UC | Actor đang hoạt động | Trigger / tiền điều kiện | Kết quả chính |
|---|---|---|---|
| UC-09 | QTV, QLK, NV | Xem/tìm mặt hàng; đã đăng nhập | Chỉ đọc, AND filters, page/sort ổn định; trả tồn thực tế/đang giữ/còn dùng |
| UC-10 | QLK | Lưu mặt hàng mới; payload hợp lệ | Mã tự cấp, tồn 0, linh kiện active; thành phẩm active cùng Bom v1 trong một transaction |
| UC-11 | QLK | Lưu sửa mặt hàng tồn tại | Chỉ field cho phép, mã/loại/số dư bất biến; khóa ĐVT khi đã dùng; audit trước/sau |
| UC-12 | QLK | Ngừng/dùng lại thành phẩm tồn tại | Trạng thái thành phẩm/Bom đi cùng; chọn version gần kích hoạt nhất khi dùng lại |
| UC-13 | QTV, QLK | Xem/tìm NCC; đã đăng nhập | Chỉ đọc, lọc mã/tên/tỉnh/phường, page/sort ổn định; NV bị chặn |
| UC-14 | QLK | Lưu NCC mới, đủ mọi thông tin | Mã NCC tự cấp; lưu và audit cùng thành công hoặc rollback; không DELETE |
| UC-44 | QLK | Lưu sửa NCC tồn tại | Không đổi mã; thông tin bắt buộc; no-op không UPDATE/audit; phiếu nhập đọc thông tin NCC hiện tại |

### 3.2. Dữ liệu và chuyển trạng thái đã rõ

- Chỉ hai loại `thanh_pham`, `linh_kien`. Đơn giá JSON integer VND, không âm,
  phù hợp BIGINT; không tự chuyển thành Decimal string hoặc số có phần lẻ.
- Mã MH/NCC theo Identity/trigger SQL; không nhận mã khi tạo/sửa, không MAX+1 cấp ID
  thủ công. Hết dải mã là lỗi có kiểm soát, không tái sử dụng mã.
- `so_luong_ton`, `so_luong_dang_giu`, `so_luong_con_dung` chỉ đọc; số cuối lấy đúng
  tồn − đang giữ và không âm. Catalog không tự tạo giữ hàng, sửa số dư hoặc ghi ledger.
- Trạng thái chỉ áp dụng thành phẩm. Tạo TP cùng v1 active; ngừng TP thì active Bom
  thôi dùng; dùng lại chọn version có `kich_hoat_gan_nhat_at` gần nhất, không chọn
  theo số version lớn nhất. Không đổi version/định mức đã lưu hoặc snapshot yêu cầu cũ.
- Tiếp tục các quyết định BOM đã duyệt về no-op trạng thái catalog: ngừng thành phẩm
  đã inactive với tag hiện tại không ghi thêm lifecycle event; dùng lại thành phẩm
  đã active không thay thời gian kích hoạt. No-op sửa thông tin chung xem Q4.
- NCC có đủ `ten_ncc`, `so_dien_thoai`, `tinh`, `phuong`, `dia_chi`: string không rỗng
  hoặc toàn whitespace. Lưu nguyên giá trị văn bản đã nhập; không tra danh mục, sửa
  chính tả, kiểm tra quan hệ địa lý hoặc tự gộp địa chỉ. Chỉ kiểm tra điện thoại là
  thông tin bắt buộc không trắng, không tự thêm regex quốc gia chưa được yêu cầu.
- Không áp đặt unique tên/điện thoại NCC khi tài liệu/SQL chỉ chốt unique mã.
- UC-44 no-op là quyết định có sẵn, không hỏi lại. Không UPDATE/audit khi giá trị
  thực sự không đổi; so điều kiện đồng thời trước no-op nếu chính sách Q5 được duyệt.

### 3.3. Transaction và audit

```text
Router → Service / Use Case → Repository → PostgreSQL
                       └──→ AuditService → SqlAlchemyAuditRepository → PostgreSQL
```

Router không truy vấn SQL hay quyết định chính sách nghiệp vụ. Schema kiểm tra
cấu trúc; service kiểm tra role, tồn tại, tham chiếu, trạng thái và chuyển đổi.
Repository không commit hay quyết định HTTP. Luồng đọc có cache vẫn giữ ranh giới
service và cơ chế snapshot hiện hữu, không refactor toàn kiến trúc để ép mọi GET
chạy SQL nếu không cần. Chênh lệch này phải nêu trong plan.

Một lần ghi liên quan item/Bom/audit phải một commit/rollback. NCC và audit của nó
cũng cùng transaction. Cache publish sau commit; khi commit không chắc chắn cần
đánh dấu cache chưa sẵn sàng theo cơ chế đã có. Không sửa/xóa lịch sử hoặc lưu bí mật.
Snapshot audit trước/sau phản ánh dữ liệu thực đã lưu, không dùng lại payload client
làm snapshot khi DB có trigger chuẩn hóa/cấp mã.

## 4. Exceptions và AC backend dùng chung

AC gốc được giữ nguyên. `CAT-AC-nn` dưới đây là AC dùng chung; Q2–Q6 đã được dev
xác nhận. Việc phê duyệt backend không đồng nghĩa các phần UI/E2E đã đạt.

### CAT-AC-01 — Quyền từ tài khoản hiện tại

Given: Token hợp lệ nhưng role/trạng thái trong DB có thể đã đổi.\
When: Gọi endpoint hoặc service nghiệp vụ.\
Then: Đọc mặt hàng cho QTV/QLK/NV; đọc NCC cho QTV/QLK; ghi chỉ QLK. Thiếu/sai/hết
hạn token 401, account khóa hoặc role không được phép bị chặn theo auth hiện có;
không tin role client tự khai. Quyền xem catalog không mở quyền xem BOM cho QTV.

### CAT-AC-02 — Input không hợp lệ không làm thay đổi dữ liệu

Given: Payload thiếu/bị null/trắng ở field bắt buộc, field lạ, mã/số dư tự nhập,
loại bị cấm hoặc đơn giá boolean/phần lẻ/vượt giới hạn.\
When: Tạo/sửa catalog.\
Then: Trả 422 với trường lỗi; không ghi DB/audit thành công hoặc công bố cache mới.
Điều kiện phụ thuộc DB như ĐVT đã dùng được service kiểm tra, không đặt trong schema.

### CAT-AC-03 — Truy vấn và phân trang

Given: Nhiều bản ghi thỏa một số tiêu chí, có giá trị sort trùng nhau.\
When: Lọc nhiều tiêu chí và chuyển trang.\
Then: AND filters; total và data cùng bộ lọc; khóa phụ ID ổn định; không trùng giữa
các trang của cùng tập dữ liệu không đổi. Không kết quả/trang vượt phạm vi trả [];
query lạ/trùng, sort không được hỗ trợ, khoảng giá đảo trả 422. Không hứa snapshot
phân trang xuyên nhiều request khi tập dữ liệu bị người khác thay đổi giữa các lần đọc.

### CAT-AC-04 — Nguyên tử và cache

Given: Ghi hợp lệ cần cập nhật dữ liệu và audit, có thể thêm Bom khi tạo TP.\
When: Một bước ghi/audit/commit lỗi.\
Then: Rollback toàn bộ, không còn dữ liệu một phần, không publish cache bị rollback;
lỗi không được trả thành công. Test riêng lỗi trước commit và tình huống commit
không chắc chắn, không suy ra mất mạng thật đã kiểm chứng từ test mô phỏng.

### CAT-AC-05 — Đồng thời theo Q5

Given: Hai quản lý sửa cùng resource dựa trên một phiên bản đọc.\
When: Cùng ghi với If-Match.\
Then: So và ghi dưới cùng khóa/transaction; thiếu tag 428, stale/weak/wildcard 412;
không mất thay đổi, không audit thao tác thất bại. Tạo mới không cần If-Match.
Các no-op vẫn phải thỏa quyền và điều kiện đồng thời trước khi trả thành công.

### CAT-AC-06 — Không thay đổi kho/chứng từ cũ

Given: Item/NCC đã có tham chiếu và dữ liệu kho/chứng từ.\
When: Tạo/sửa/ngừng/dùng lại catalog.\
Then: Không sửa số dư, giữ hàng, ledger, giá đã chốt, định mức hoặc liên kết đã chốt;
riêng thông tin NCC hiển thị trên phiếu nhập là thông tin hiện tại theo UC-44/R8,
không tạo cột snapshot NCC. Các phần đọc/duyệt liên module phải được đánh dấu riêng.

### CAT-AC-07 — HTTP và chỉ đọc

Given: Request đã qua xác thực hoặc bị thiếu quyền/input.\
When: Gọi API catalog.\
Then: Schema/OpenAPI và envelope/status/header theo plan đã duyệt; phân biệt 401,
403, 404 không tồn tại, 409 xung đột nghiệp vụ, 422 sai input, 428/412 theo Q5.
GET không sửa trạng thái, audit, cache nghiệp vụ hoặc số dư; không trả hash/token/
chi tiết lỗi DB. Không có DELETE nhà cung cấp hoặc xóa cứng mặt hàng.

### CAT-AC-08 — Mã và schema thực tế

Given: PostgreSQL test mới/trống được bootstrap bằng init.sql thực.\
When: Hai request cùng tạo item hoặc NCC, hoặc ID vượt dải mã.\
Then: ID/mã không trùng; không nhận mã client; hết dải trả lỗi có kiểm soát; không
để lại audit/thực thể một phần. ORM đúng bảng/cột/kiểu/null/default/khóa/ràng buộc,
không dùng SQLite hoặc metadata.create_all để kết luận SQL v4 đã tương thích.

## 5. Quyết định đã được dev xác nhận ngày 14/11/2026 (Q1–Q6)

| Mã | Điểm đã chốt | Phương án được duyệt | Ảnh hưởng |
|---|---|---|---|
| Q1 — đã giải quyết | Source/test BOM đã có tại b9e1020 sau khi dev pull | Tái sử dụng nghiệp vụ/DTO/DI/test BOM đã có; không khôi phục toàn module. R00 đã được dev cho sửa riêng và 105 test BOM/tích hợp đã pass | Không còn cần phê duyệt việc đưa phần source bị thiếu vào scope Catalog; Q2–Q6 đã duyệt |
| Q2 | SQL yêu cầu SKU unique/not null, UC không nêu SKU trong các field được sửa; code BOM mới cho sửa SKU nếu không trùng | Giữ SKU bắt buộc khi tạo; đề xuất cho sửa khi item chưa có tham chiếu/tồn, từ chối khi đã dùng. Đây là siết thêm so với code vừa pull, cần dev xác nhận; không nới quyền sửa mã/loại | Cần xác định field request và test bảo vệ SKU; nếu dev muốn giữ code mới hoặc SKU luôn bất biến thì cập nhật spec trước plan |
| Q3 | Nghĩa chuỗi tìm kiếm và trạng thái TP chưa chốt đầy đủ | q là literal substring, không phân biệt hoa/thường, chỉ mã/tên, `%/_` không wildcard, không tìm SKU. Tỉnh/phường chứa chuỗi con sau bỏ whitespace ngoài, không phân biệt hoa/thường, giữ dấu, `%`/`_` literal; không thay nội dung lưu. Có is_active mà không chỉ loại thì chỉ tìm TP; kết hợp với loai=linh_kien trả 422 | Thống nhất cache/SQL và thay một số hành vi tìm kiếm cũ; vẫn lưu nguyên tỉnh/phường đã nhập theo UC-14 |
| Q4 | UC-11 chưa nói lưu item không đổi có ghi lịch sử không | Áp dụng như UC-44: 200 dữ liệu/tag hiện tại, không UPDATE/audit/cache publish nếu giá trị không đổi; If-Match cũ vẫn lỗi theo Q5 | Khác code hiện tại luôn audit khi PATCH item; không thay quyết định no-op NCC đã chốt |
| Q5 | NCC chưa có ETag/PATCH; mặt hàng sau pull đã có strong tag và ngữ cảnh BOM | Kế thừa validator/transaction của mặt hàng; áp dụng strong ETag cho GET detail NCC và bắt buộc If-Match ở PATCH NCC mới; thiếu 428, stale/weak/wildcard 412. Tag NCC từ representation hiện tại; GET/POST không bắt If-Match | Client PATCH NCC mới phải lấy tag; không triển khai lại ETag mặt hàng/BOM hoặc tạo cột version/migration chỉ để làm tag |
| Q6 | UC-44/AC-8 cần phiếu nhập hiển thị NCC hiện tại nhưng DTO hiện chỉ có ncc_id | Cho phép tích hợp phần đọc tối thiểu module phieu_nhap: bổ sung projection thông tin NCC hiện tại, không snapshot; cập nhật import trực tiếp khi đổi lớp ORM. Không refactor nghiệp vụ ghi/hoàn tất/tiền phiếu nhập. Phần duyệt giá phiếu xuất và E2E sản xuất của UC-11/12 vẫn hoãn như phạm vi liên module trước | Có thay đổi response GET phiếu nhập cần nêu trong plan. Nếu phần đọc bị chặn bởi schema khác, báo phụ thuộc, không tự mở rộng/refactor để làm xanh |

Nguồn v4, integer VND, ba vai trò, mã tự cấp/không sửa, mọi thông tin NCC bắt buộc,
không xóa NCC, no-op UC-44, raw địa chỉ nhập tay và không migration đã có quyết định;
không hỏi lại nghiệp vụ đã chốt. Q1 đã giải quyết bằng pull source; Q2–Q6 đã được duyệt.
Các cụm “đề xuất/cần xác nhận” trong bảng lưu lại câu hỏi trước lúc duyệt; không còn
là câu hỏi nghiệp vụ mở. Các lựa chọn kỹ thuật cụ thể nằm trong plan chờ duyệt riêng.

<a id="catalog-trace"></a>

## 6. Truy vết sau triển khai

Các AC ghi “đạt backend” đã được chạy trên PostgreSQL test riêng và actual app/auth.
Phần UI được hoãn theo phạm vi đã duyệt, không coi kiểm thử API thay cho kiểm thử UI.
Trong bảng, S = [test_catalog_service.py](../../../backend/tests/test_catalog_service.py),
A = [test_catalog_api.py](../../../backend/tests/test_catalog_api.py),
P = [test_catalog_postgres.py](../../../backend/tests/test_catalog_postgres.py),
MB = [test_mat_hang_bom.py](../../../backend/tests/test_mat_hang_bom.py),
BP = [test_bom_postgres.py](../../../backend/tests/test_bom_postgres.py).
Tên test ghi sau ký hiệu file là symbol thực tế, không phải tên dự kiến.

| UC / Spec | Endpoint → Service | AC | Test / kết quả và giới hạn |
|---|---|---|---|
| [UC-09](UC-09.md) | GET `/mat_hang` → MatHangReader.list_mat_hang | AC-1,4 | S:`test_uc09_ac04_ac05_combined_filters_stable_pages`, `test_uc09_cat_ac03_literal_code_name_only`, `test_uc09_cat_ac03_active_applies_only_to_finished_items` — đạt |
| UC-09 | Ba GET mặt hàng → MatHangReader | AC-2 | A:`test_cat_ac01_read_roles_from_database`, `test_uc10_uc11_uc12_cat_ac01_item_write_roles` — đạt quyền backend; ẩn nút UI chưa kiểm chứng |
| UC-09 | GET list/catalog/detail → reader và DTO | AC-3,6 | P:`test_uc09_ac06_stock_projection_and_read_only`; A:`test_uc11_cat_ac02_immutable_and_structural_fields` — đạt ba số tồn 10/3/7 và không ghi |
| UC-09 | GET list/detail → reader | AC-5 | A:`test_cat_ac02_invalid_queries`, `test_cat_ac02_detail_errors`, `test_uc09_cat_ac02_invalid_filter_combination`; S:test phân trang ở trên — đạt |
| [UC-10](UC-10.md) | POST `/mat_hang` → MatHangService.create_mat_hang → BomService.create_initial_formula | AC-1 | MB:`test_uc10_component_create_and_duplicate_sku` — đạt |
| UC-10 | Cùng endpoint/service | AC-2,3,4 | MB:`test_uc16_ac1_to4_bad_formula_never_creates_item`, `test_uc16_ac1_wrong_type_or_missing_item_rolls_back`, `test_uc10_uc16_create_response_and_reserved_input`; BP:`test_uc16_ac5_atomic_create_and_generated_code` — đạt |
| UC-10 | Cùng endpoint/service | AC-5,6 | MB:response/reserved input; P:`test_uc10_cat_ac08_concurrent_item_codes`; MB:`test_uc10_code_exhaustion_is_conflict_without_partial_write` — backend đạt, form không có ô mã/tồn chưa kiểm chứng |
| UC-10 | Cùng endpoint/service | AC-7 | A:`test_uc10_uc11_uc12_cat_ac01_item_write_roles` — đạt |
| UC-10 | Cùng endpoint/service | AC-8,9 | MB:`test_uc16_ac6_atomic_create_failure` và validation API/schema của MB — đạt backend, cùng transaction item/BOM/audit |
| [UC-11](UC-11.md) | PATCH `/mat_hang/{id}` → MatHangService.patch_mat_hang | AC-1 | P:`test_uc11_ac01_unreferenced_sku_unit_and_audit` — đạt |
| UC-11 | Cùng endpoint/service → MatHangRepository.get_references | AC-2,3 | P:`test_uc11_ac01_referenced_fields_locked`, `test_uc44_ac08_draft_receipt_projection_and_stale_tag`, `test_uc11_q2_stock_prevents_sku_change` — đạt BOM/phiếu nhập/stock refs |
| UC-11 | Giá lúc duyệt phiếu xuất | AC-4 | **Chưa kiểm chứng E2E**: duyệt xuất ngoài phạm vi Q6. Catalog không ghi lại giá chứng từ cũ; không kết luận toàn AC đạt |
| UC-11 | PATCH → diff/audit/mutation | AC-5 | P:`test_uc11_ac01_unreferenced_sku_unit_and_audit` — đạt snapshot trước/sau |
| UC-11 | PATCH → schema | AC-6 | A:`test_uc11_cat_ac02_immutable_and_structural_fields`; MB:`test_uc12_immutable_catalog_input` — backend đạt; UI chỉ hiển thị mã/loại chưa kiểm chứng |
| UC-11 | PATCH → diff/mutation | AC-7 | P:`test_uc11_ac07_noop_no_update_audit_or_cache_publish` — đạt SQL spy, audit và cache giữ nguyên |
| UC-11 | PATCH → transaction | AC-8 | P:`test_uc11_ac08_update_rollback_keeps_cache_and_audit`, `test_uc11_cat_ac05_two_independent_caches_one_winner` — đạt rollback và một request thắng |
| [UC-12](UC-12.md) | PATCH/DELETE `/mat_hang/{id}` → MatHangService → BomService lifecycle | AC-1 | BP:`test_uc17_uc18_uc19_lifecycle_and_stale_validators`; P:`test_uc12_ac01_repeated_stop_does_not_publish_or_audit` — đạt trạng thái cùng công thức và no-op |
| UC-12 | Tạo/thực hiện yêu cầu sản xuất | AC-2,3 | **E2E hoãn**; BP:`test_uc17_ac1_to4_uc19_ac6_preserves_committed_request_and_balances` chỉ kiểm chứng row/snapshot cũ không đổi, không thay cho chạy production |
| UC-12 | PATCH dùng lại → BomService | AC-4 | MB:`test_uc12_reuses_most_recently_activated_not_highest_version` — đạt |
| UC-12 | PATCH/DELETE LK | AC-5 | MB:`test_uc12_component_cannot_be_stopped` — backend đạt, ẩn điều khiển UI chưa kiểm chứng |
| UC-12 | Chứng từ/sản xuất cũ | AC-6 | BP:test bất biến request/balance nói trên và P:test phiếu hoàn tất giữ nguyên — đạt giới hạn dữ liệu; **E2E chứng từ/sản xuất chưa kiểm chứng** |
| UC-12 | PATCH/DELETE → mutation/audit | AC-7 | BP:`test_bom_ac04_state_and_audit_rollback`; MB:test atomic create/state regression — đạt |
| [UC-13](UC-13.md) | GET `/nha_cung_cap` → SupplierService.list_suppliers | AC-1,4 | P:`test_uc13_cat_ac03_literal_address_and_stable_pages`, `test_uc44_ac01_ac04_ac06_new_address_filters_and_audit` — đạt AND/literal/địa chỉ/page |
| UC-13 | GET NCC → service guards | AC-2,3 | A:`test_cat_ac01_read_roles_from_database`, `test_uc14_uc44_cat_ac01_write_roles`; S:`test_uc13_uc14_uc44_cat_ac01_service_guard` — quyền backend đạt; UI ẩn nút chưa kiểm chứng |
| UC-13 | GET `/{id}` → SupplierService.get_supplier | AC-5 | A:`test_uc14_uc44_http_roundtrip_and_unsupported_delete`, `test_cat_ac02_detail_errors`; P:`test_uc14_cat_ac08_identity_trigger_and_audit` — đạt body/tag/404 và đọc không thêm audit |
| [UC-14](UC-14.md) | POST `/nha_cung_cap` → SupplierService.create_supplier | AC-1,2,3 | A:test roundtrip/generated fields; S:`test_uc14_uc44_cat_ac02_reject_missing_information`, `test_uc14_ac04_preserve_raw_text_and_uc13_normalize_filters` — đạt đủ thông tin, raw text, không áp geography/phone regex |
| UC-14 | POST rồi GET list | AC-4 | P:`test_uc13_cat_ac03_literal_address_and_stable_pages` — đạt tìm địa chỉ vừa lưu, giữ dấu |
| UC-14 | Không có DELETE NCC | AC-5 | A:test roundtrip kiểm tra DELETE 405 — backend đạt, UI không có nút xóa chưa kiểm chứng |
| UC-14 | POST → repository/audit/transaction | AC-6 | P:`test_uc14_cat_ac08_identity_trigger_and_audit`, `test_uc14_uc44_cat_ac04_rollback`, `test_uc14_cat_ac04_concurrent_identity`, `test_uc14_cat_ac08_exhausted_code_returns_conflict`, `test_cat_ac08_supplier_mapping_matches_real_schema` — đạt |
| [UC-44](UC-44.md) | PATCH `/nha_cung_cap/{id}` → SupplierService.patch_supplier | AC-1,4,6 | P:`test_uc44_ac01_ac04_ac06_new_address_filters_and_audit` — đạt sửa nhiều field, lọc địa chỉ mới và audit trước/sau |
| UC-44 | PATCH → schema/service | AC-2,3 | A:`test_uc44_ac02_ac03_reject_bad_patch_without_changes`; S:test null/blank theo từng field — backend đạt; mã chỉ hiển thị ở form chưa kiểm chứng |
| UC-44 | PATCH → guard | AC-5 | A:`test_uc14_uc44_cat_ac01_write_roles`; S:test service guard — đạt |
| UC-44 | PATCH → diff | AC-7 | P:`test_uc44_ac07_noop_has_no_update_or_audit` — đạt cả `{}` và mọi giá trị không đổi |
| UC-44 | GET `/phieu_nhap`, `/{id}` và response sau tạo/sửa → PhieuNhapService/SqlAlchemyPhieuNhapRepository | AC-8 | P:`test_uc44_ac08_completed_receipt_live_supplier_and_tag_roundtrip`, `test_uc44_ac08_draft_receipt_projection_and_stale_tag` — đạt draft/hoàn tất, DTO locked và tag round-trip, audit không snapshot NCC |
| UC-44 | PATCH → row lock/transaction | AC-9 | P:`test_uc44_cat_ac05_two_sessions_one_winner`, `test_uc44_cat_ac05_independent_suppliers_both_update`, `test_uc14_uc44_cat_ac04_rollback`; A:`test_uc44_cat_ac05_required_strong_precondition`, `test_cat_ac05_repeated_if_match_is_rejected` — đạt |

### AC dùng chung

| AC | Kiểm chứng thực tế |
|---|---|
| CAT-AC-01 | Test role trong A/S và P:`test_cat_ac01_role_and_account_changes_apply_to_existing_token`: đổi role/khóa áp dụng ngay với token cũ, JWT khai role khác không vượt quyền. BOM regression vẫn chặn QTV |
| CAT-AC-02 | Validation API/schema theo bảng trên, không UPDATE khi input bị từ chối; mã/tồn không nhận từ client |
| CAT-AC-03 | S:test literal/AND/stable page, P:test địa chỉ/cùng sort/hết trang, A:test query/range/enum/lặp |
| CAT-AC-04 | Rollback create/patch NCC, patch item, create TP/BOM và audit/commit injection; no-op không publish. Commit failure mô phỏng không chứng minh mất kết nối mạng thật |
| CAT-AC-05 | Row/advisory lock với barrier và session/cache độc lập; stale/weak/wildcard/repeated headers 412, missing 428, một request cùng tag thắng |
| CAT-AC-06 | Đọc phiếu cũ cập nhật NCC mà giữ các field/tiền/dòng/kho/ledger; BOM regression giữ snapshot yêu cầu. **E2E sản xuất/duyệt giá xuất vẫn hoãn** |
| CAT-AC-07 | A:`test_cat_ac07_get_rejects_body`, `test_cat_ac07_openapi_matches_catalog_contract`, `test_cat_ac07_internal_error_does_not_leak_database_details`; roundtrip status/header/envelope, API quyền/401/403/404/409/422/428/412. GET không ghi qua SQL spy |
| CAT-AC-08 | Reflection bảng NhaCungCap và test Identity/trigger, cấp mã đồng thời item/NCC và hết dải; dùng init.sql thực trên DB test trống, không SQLite/create_all |

## 7. Bàn giao và giới hạn kiểm chứng

Spec và plan đã được dev duyệt riêng; T01–T10 đã thực hiện trong phạm vi backend.
Luồng chạy: Router → Service → Repository → Database. Luồng audit:
MatHangService/BomService hoặc SupplierService → AuditService → SqlAlchemyAuditRepository,
cùng transaction với thay đổi nguồn. Mã UC trong endpoint/service và test dẫn lại spec;
spec không phải thành phần runtime.

Thay đổi tương thích cần client biết:

- MatHangRead thêm `so_luong_dang_giu` và `so_luong_con_dung` bắt buộc, chỉ đọc.
- NCC POST bỏ `ma_ncc`, bắt buộc đủ năm chuỗi; GET NCC không còn nullable theo SQL v4.
- NCC GET/POST/PATCH có ETag, PATCH mới bắt buộc If-Match.
- Phiếu nhập thêm `nha_cung_cap` hiện tại. Đổi NCC làm tag phiếu thay đổi, client cần GET lại.
- q không còn wildcard/SKU; filter trạng thái chỉ TP. Frontend chưa được chỉnh theo yêu cầu.

Kết quả chạy cuối và lệnh tái kiểm tra ghi tại [plan, phần bàn giao](PLAN.md#kết-quả-triển-khai).
[HTTP chạy thật, đã bỏ Authorization](../../../docs/examples/catalog-http.json).
Sequence và PNG: [mat_hang](../../../docs/sequence/mat_hang.md),
[nha_cung_cap](../../../docs/sequence/nha_cung_cap.md), [phieu_nhap](../../../docs/sequence/phieu_nhap.md).

Không đổi frontend, bootstrap SQL/seed, migration, database ứng dụng hoặc module sản xuất.
Không commit/push. Không khẳng định toàn hệ thống đã đạt E2E. Tiền/posting phiếu nhập
legacy chưa được nâng đầy đủ theo SQL v4; chỉ phần đọc NCC và round-trip draft nêu trên
được kiểm chứng, không mở rộng nghiệp vụ để làm xanh test ngoài phạm vi.
