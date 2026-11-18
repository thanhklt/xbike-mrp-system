# Plan: Backend Catalog — UC-09–UC-14 và UC-44

**APPROVED 14/11/2026 — T01–T10 đã thực hiện trong phạm vi backend.**
Spec và Q2–Q6 đã được duyệt ngày 14/11/2026; Q1 đã giải quyết bằng pull BOM.
Hotfix R00 một dòng `@asynccontextmanager` đã được duyệt/sửa riêng, giữ nguyên diff đó.
Kết quả kiểm chứng thực tế và giới hạn nằm ở mục bàn giao cuối file; không coi
việc hoàn thành backend là xác nhận UI hoặc E2E sản xuất/duyệt xuất đã đạt.

## Goal

Hoàn thiện backend Catalog theo [spec đã duyệt](README.md): đúng quyền đọc/ghi,
tra cứu kết hợp, ba số tồn chỉ đọc, SKU/no-op, tạo/sửa NCC với mã hệ thống cấp và
audit nguyên tử; phiếu nhập đọc NCC hiện tại. Giữ toàn bộ hành vi BOM đã kiểm chứng,
không refactor frontend, sản xuất hoặc nghiệp vụ ghi sổ chứng từ.

## Context read

- [UC-09](UC-09.md), [UC-10](UC-10.md), [UC-11](UC-11.md), [UC-12](UC-12.md),
  [UC-13](UC-13.md), [UC-14](UC-14.md), [UC-44](UC-44.md), [spec tổng](README.md).
- [BR giai đoạn 1](../../business_requirements/BR-GIAIDOAN1.md),
  [model v4](../../entity_model/data_model_v4.md), [init.sql](../../../infra/postgres/init.sql),
  `AGENTS.md`, `backend/pyproject.toml` và spec/plan BOM đã duyệt.
- Source thực tế `mat_hang`, `nha_cung_cap`, phần context/DTO của `bom`,
  `dependencies.py`, `core/preconditions.py`, transaction/error handler/audit.
- Phần read model/repository/DTO/ETag/audit serialization của `phieu_nhap`, các import
  `Supplier` trực tiếp. Không xem schema tiền cũ của phiếu nhập là lý do đổi toàn module.
- Bốn file test BOM/tích hợp và test nhân viên hiện có; sequence tương ứng.
- Skill clean-code: plan, Python/FastAPI, test, concurrency và review; không dùng
  superpowers, không tạo `.clean/` hoặc abstraction kiến trúc tổng quát.

Baseline mới nhất: trên `feature/catalog`, commit `b9e1020` + hotfix R00 đã duyệt,
**105 test BOM/tích hợp pass** trên PostgreSQL test riêng. Có 8 lỗi nền nhân viên
thiếu `VaiTroRead.mo_ta`; không sửa để làm xanh suite trong tác vụ này.

## Existing code to reuse

| Thành phần hiện có | Cách dùng |
|---|---|
| MatHangReader/MatHangService và MatHangRepository | Bổ sung quyền/DTO/filter/SKU/no-op, không tạo service catalog thứ hai |
| MatHangCache, MatHangSynchronizer, MatHangMutation.scope | Giữ snapshot/cache lock/commit rồi publish; chỉ thêm khả năng scope không có thay đổi thì không publish |
| BomService.item_detail/create_initial_formula/lifecycle | Giữ tạo TP cùng v1 và trạng thái đi cùng công thức; QTV chỉ nhận DTO mặt hàng/tag, không nhận nội dung BOM |
| core.preconditions.make_etag/verify_if_match | Dùng strong validator hiện có cho NCC; giữ cách đối chiếu tag TP có ngữ cảnh BOM |
| SupplierService/SqlAlchemySupplierRepository/ports | Mở rộng owner hiện có cho UC-13/14/44; giữ tên service/repository, chỉ đổi lớp ORM theo quy ước bảng |
| AuditService.append + SqlAlchemyAuditRepository | DI NCC chuyển từ repository trực tiếp sang AuditService, cùng session/transaction |
| SqlAlchemyTransaction, request context, require_roles/current auth | Giữ commit/rollback và envelope/lỗi chung, đọc role/account từ DB |
| test_bom_postgres.database và test_bom_api.client/headers | Tái sử dụng bootstrap SQL thật, guard URL test, auth thật và cleanup test DB; không sao chép fixture DB ra bộ thứ hai |

## Placement

### A. File dự kiến thay đổi

File ghi **mới** chưa tồn tại; các file còn lại đã có. Chỉ sửa phần trực tiếp liên quan.

| File | Vai trò và thay đổi |
|---|---|
| `backend/app/modules/mat_hang/router.py` | Actor đọc cả ba vai trò; Query DTO, validation HTTP, UC links/OpenAPI, response tồn |
| `mat_hang/schemas.py` | MatHangRead thêm hai số tồn chỉ đọc; **mới** MatHangListQuery; validation input/SKU |
| `mat_hang/service.py` | Guard đọc/ghi, Q3 query policy, Q2 SKU refs, Q4 no-op thực sự, audit/changed fields |
| `mat_hang/cache.py` | Literal search chỉ mã/tên; stable ID ties; bỏ quyết định lỗi HTTP/input ra schema/service |
| `mat_hang/mutation.py` | Giữ decorator đã sửa; scope rỗng không prepare/publish cache, vẫn kết thúc transaction đúng |
| `mat_hang/repository.py`, `ports.py` | Chỉ bổ sung điều kiện tham chiếu SKU nếu thiếu; dùng `get_references` v4 sẵn có. Không làm lại ORM/stock writer |
| `backend/app/modules/nha_cung_cap/{router,schemas,service,ports,repository,models}.py` | UC-13/14/44; mapping NhaCungCap đúng SQL, tạo mã trigger, PATCH có tag/lock, filter/audit/no-op |
| `backend/app/dependencies.py` | DI NCC qua AuditService; actor reader/catalog wiring khi chữ ký thay đổi |
| `backend/app/core/request_context.py` | Tái sử dụng reject_query/repeated query; bổ sung reject_body nếu cần cho các GET/DELETE Catalog, không đổi middleware/resource khác |
| `backend/app/modules/phieu_nhap/{models,schemas,repository,service,router}.py` | Q6: chỉ read projection NCC hiện tại, hydration, ETag/serialization và import trực tiếp; không đổi luật ghi/hoàn tất/tồn/tiền |
| **Mới** `backend/tests/test_catalog_service.py` | Test hành vi service/cache/query/no-op, có mã UC/AC |
| **Mới** `backend/tests/test_catalog_api.py` | API thật qua DI/auth: role/schema/query/body/headers/status |
| **Mới** `backend/tests/test_catalog_postgres.py` | Mapping, ID/trigger, tham chiếu, transaction/concurrency, NCC hiện tại trên phiếu nhập |
| `docs/sequence/mat_hang.md`, `nha_cung_cap.md`, `phieu_nhap.md` và PNG liên quan | Cập nhật theo endpoint đã triển khai, không viết luồng tương lai như đang có |
| `specs/use_cases/catalog/{README,PLAN,UC-09,UC-10,UC-11,UC-12,UC-13,UC-14,UC-44}.md` | Truy vết, trạng thái task và kết quả thật |
| **Mới** `docs/examples/catalog-http.json` | Request/response chạy thật sau triển khai, không JWT/secret |

Không đổi tên folder/module, không tạo module backend `catalog`; không sửa SQL/seed,
migration, dependency manifests, cấu hình hay database ứng dụng. Không sửa runtime
BOM endpoints, giá khi duyệt xuất, sản xuất/giữ hàng hoặc test nhân viên ngoài phạm vi.
`app/models.py` đăng ký module models nên không cần sửa nếu không có import symbol trực tiếp.

### B. API/DTO đích cần duyệt trong plan

Giữ route hiện hữu, chỉ thêm PATCH NCC. Envelope `{data, meta}` và `{error, meta}`
đang có được giữ; gắn UC và đường dẫn spec vào mô tả endpoint, docstring service.

| UC | Endpoint đích | Quyền | Thành công/headers |
|---|---|---|---|
| UC-09 | GET `/api/v1/danh_muc_mat_hang/` | QTV/QLK/NV | 200 danh mục + meta, giữ endpoint phụ trợ hiện tại |
| UC-09 | GET `/api/v1/mat_hang` | QTV/QLK/NV | 200 data/page/meta |
| UC-09 | GET `/api/v1/mat_hang/{id}` | QTV/QLK/NV | 200 DTO mặt hàng + strong ETag của mặt hàng |
| UC-10 | POST `/api/v1/mat_hang` | QLK | 201 + Location/ETag; giữ tạo kèm `bom.chi_tiet` cho TP |
| UC-11/12 | PATCH `/api/v1/mat_hang/{id}` | QLK | 200 DTO/ETag; If-Match bắt buộc, no-op không ghi |
| UC-12 | DELETE `/api/v1/mat_hang/{id}` | QLK | 204 ngừng mềm TP, If-Match bắt buộc |
| UC-13 | GET `/api/v1/nha_cung_cap` | QTV/QLK | 200 data/page/meta |
| UC-13 | GET `/api/v1/nha_cung_cap/{id}` | QTV/QLK | 200 DTO NCC + strong ETag |
| UC-14 | POST `/api/v1/nha_cung_cap` | QLK | 201 + Location/ETag; mã do DB cấp |
| UC-44 | **Mới** PATCH `/api/v1/nha_cung_cap/{id}` | QLK | 200 DTO/ETag, If-Match bắt buộc; không thay đổi thì tag giữ nguyên |
| UC-44/AC-8 | GET `/api/v1/phieu_nhap` và `/{id}` | Quyền hiện tại QLK | Giữ payload phiếu, thêm field `nha_cung_cap` là DTO thông tin hiện tại; detail tag tính trên representation mới |

- NCC create nhận đúng `ten_ncc`, `so_dien_thoai`, `tinh`, `phuong`, `dia_chi`, đều
  string bắt buộc không null/trắng. Lưu nguyên text nhập, không global strip các field
  ghi. Không có field `ma_ncc`, id, created_at; field lạ bị 422.
- **Mới** NhaCungCapPatch: các field trên được gửi từng phần, field vắng giữ nguyên;
  explicit null/trắng bị 422. `{}` là no-op sau khi kiểm tra actor/resource/If-Match.
  Read giữ `id`, `ma_ncc` và năm field thông tin; nâng nullable cũ sang bắt buộc theo v4.
- MatHangRead thêm `so_luong_dang_giu`, `so_luong_con_dung` là integer chỉ đọc,
  không dùng default 0 để che việc nguồn đọc chưa hydrate đúng. Giữ field đang có.
  Kiểm chứng ba số trong cùng bản ghi và computed column đúng; không đọc TonKho cũ.
- Giữ price integer VND/BIGINT và raw SKU hiện có; SKU bắt buộc/nonblank/unique khi
  tạo. PATCH SKU chỉ khi chưa tham chiếu hoặc tồn theo Q2; mã/loại không sửa được.
  Thành phẩm vừa tạo đã có Bom nên SKU của nó đã có tham chiếu, không được sửa.
- Sort mặt hàng giữ `id`, `ma_mat_hang`, `ten_mat_hang`, `don_gia` và tiền tố `-`;
  NCC giữ `id`, `ma_ncc`, `ten_ncc` và tiền tố `-`. Default `id`, page 1/page_size 20,
  max 100, ID ASC làm khóa phụ khi primary key sort trùng nhau.
- Request/query lạ hoặc trùng, path/kiểu/range sai trả 422; detail ID không tồn tại
  hoặc lớn hơn dải integer trả 404 mà không gửi ID vượt giới hạn xuống asyncpg.
  Không nhận body trên GET/DELETE. Unsupported DELETE NCC trả 405, không thêm route xóa.
- Auth/role được kiểm tra trước nghiệp vụ. Khi resource hợp lệ: thiếu tag 428,
  stale/weak/wildcard/nhiều tag 412; vi phạm tham chiếu/unique/nghiệp vụ 409.
  Không hứa thứ tự lỗi khi request đồng thời có nhiều lỗi validation cấu trúc.

### C. Tìm kiếm, cache và phân tầng đọc

- **Mới** MatHangListQuery trong schemas: typed params, extra forbid, range giá/page,
  whitelist sort và validation khoảng giá. Router chỉ bind schema/actor rồi gọi reader.
- MatHangReader nhận actor ở các thao tác đọc và kiểm tra đủ ba vai trò. NhaCungCap
  service đọc nhận actor và chặn NV; mọi đường ghi vẫn kiểm tra QLK ở service.
- `q` strip whitespace ngoài, rỗng thành không lọc; literal substring không phân biệt
  hoa/thường trên mã/tên, giữ dấu; không tìm SKU, không wildcard `%/_`. Dùng thao tác
  text chuẩn, không ghép user input thành regex/SQL. Cache và SQL có test UTF-8 thực.
- `tinh`/`phuong` query trống sau trim coi như không lọc. **Cập nhật dev duyệt
  17/11/2026, UC-13 R6/AC-6:** tìm một phần, không phân biệt hoa/thường và dấu
  tiếng Việt (cả Unicode dựng sẵn/tổ hợp), kết hợp AND. Normalize ở predicate bằng
  `normalize`/`translate` có sẵn trong PostgreSQL 16, escape literal khi tìm chuỗi;
  không thêm extension/schema/migration, không sửa giá trị NCC lưu/response. COUNT
  và SELECT dùng cùng bộ lọc trước phân trang. Cho lọc phường một mình, không suy
  luận địa giới. Quy tắc `q` trên mã/tên giữ nguyên.
- Có `is_active` thì chỉ lọc TP; kết hợp loai=linh_kien bị service từ chối 422 theo
  chính sách Q3. Nếu không có filter trạng thái, linh kiện active vẫn có trong danh sách.
- Tổng số và data áp dụng cùng bộ lọc; sort tường minh có tie-break ID; page vượt
  phạm vi trả []. Không cam kết nhiều request phân trang thuộc cùng snapshot DB khi
  có thay đổi đồng thời; không tự thêm cursor/snapshot API.
- Giữ list/danh mục mặt hàng đọc snapshot MatHangCache. Detail dùng DB qua
  BomService.item_detail hiện có để cấp tag cùng representation. Đây là kiến trúc
  cache đọc đã có, không ép mọi GET chạy SQL hoặc thêm repository cache mới.
- Loại bỏ lỗi HTTP từ helper filter để service/schema quyết định lỗi; không chuyển
  query nghiệp vụ hoặc SQL vào router. Không thay cơ chế LISTEN/NOTIFY/reconcile.

### D. Ghi mặt hàng, SKU, no-op và cache

- Giữ create TP/Bom v1 và UC-12 qua BomService đã có; không viết bản thứ hai của luật
  công thức. Giữ ETag có ngữ cảnh BOM và thứ tự khóa cache → advisory BOM → item → versions.
- Sau khóa và If-Match, tạo tập field **thực sự đổi** từ payload đã validate so với
  DB snapshot. Kiểm tra refs khi SKU/ĐVT thực sự đổi, không từ chối vì gửi lại giá trị cũ.
  SKU đổi với `refs.has_any` bị 409; ĐVT đổi khi có công thức/chứng từ vẫn bị 409.
- No-op PATCH, kể cả `{}` hoặc gửi lại trạng thái/thuộc tính hiện tại: 200 dữ liệu
  và tag hiện tại; không UPDATE/audit hoặc append cache change. Tag cũ vẫn bị 412.
  Không bỏ kiểm tra quyền/điều kiện đồng thời chỉ vì payload không có thay đổi.
- MatHangMutation.scope giữ transaction nhưng scope rỗng không prepare/publish cache.
  Khi có thay đổi thì vẫn prepare trước commit, publish sau commit; lỗi ghi/audit
  rollback, lỗi commit không chắc chắn xử lý unavailable như hiện có. Giữ decorator R00.
- Tạo/sửa/ngừng/dùng lại không sửa số dư/giữ hàng/ledger/định mức/chứng từ cũ. Trạng
  thái được audit một lần theo mỗi đối tượng thực đổi, không thêm sự kiện do no-op.

### E. NCC, audit, Identity và transaction

- Đổi ORM `Supplier` thành `NhaCungCap`, trùng tên bảng. Map đúng Identity, created_at,
  NOT NULL, unique/check của init.sql. `ma_ncc` là giá trị DB trigger sinh; dùng cơ chế
  fetched value/refresh phù hợp, không thêm SQL default giả và không MAX+1/ID cấp tay.
- Cập nhật import trực tiếp ở NCC repository và phieu_nhap repository. Không giữ
  class ORM thứ hai cùng map bảng, không đổi tên service/repository không cần thiết.
- SupplierService.list_suppliers/get_supplier tiếp tục là owner đọc; **mới**
  SupplierService.patch_supplier triển khai UC-44. **Mới** NhaCungCapPatch; mở rộng
  query schema đang có và các port `get_for_update`, `update`/read projection khi cần.
- NCC không có cache mới. DI dùng AuditService(SqlAlchemyAuditRepository(db)), cùng
  AsyncSession với SqlAlchemySupplierRepository và SqlAlchemyTransaction.
- POST tạo thực thể, flush/refresh mã DB, audit `nha_cung_cap/tao`, commit một lần.
  Hai request tạo dùng Identity/unique constraint, không cần advisory lock cấp mã tay.
  Hết dải NCC-NNNNNN phải thành lỗi 409 được kiểm thử, không 500 hoặc tái sử dụng mã.
- PATCH guard QLK → transaction → row FOR UPDATE → đọc snapshot → verify tag → diff.
  Có diff: update/refresh → audit `sua` trước/sau → commit; không diff: giữ nguyên row,
  không audit. Repository chỉ truy cập dữ liệu, không commit hoặc quyết định HTTP.
- Tag từ canonical JSON của NhaCungCapRead hiện tại, không request_id/secret. POST,
  GET detail và PATCH phải tạo cùng tag khi representation không đổi; GET/POST không
  yêu cầu If-Match. Không tạo cột phien_ban/migration để ghi số lần sửa NCC.
- Audit snapshot lấy từ record thật đã lưu, raw địa chỉ giữ nguyên; no-op không
  được gọi append. Không triển khai lại toàn bộ UC-43 hoặc sửa caller audit legacy khác.

### F. Phiếu nhập đọc thông tin NCC hiện tại — phần Q6

Đây là thay đổi liên module đã duyệt ở spec, cần review chi tiết tương thích tại plan:

1. Thêm field chỉ đọc `nha_cung_cap: NhaCungCapRead` vào DTO receipt được trả về,
   giữ `ncc_id` và các field/kiểu tiền hiện có của phiếu. Không thêm cột snapshot NCC.
2. Hydrate bằng read projection/quan hệ ORM view-only trên FK hiện có, từ cùng DB
   của request. Nếu dùng quan hệ, bổ sung tại PhieuNhap.models là mapping chỉ đọc,
   không DDL/FK mới; repository load tường minh/batch để tránh N+1 hoặc async lazy I/O
   khi serialize. Ncc role của người đọc phiếu không được mở rộng quyền đọc phiếu.
3. Tất cả đường dựng PhieuNhapRead (`list_receipts`, `get_receipt`, `lock_receipt`,
   trả DTO sau add/update/completed) phải được hydrate nhất quán; không gán snapshot
   cũ hoặc default null để né lỗi. Dùng populate_existing/refresh khi cần để không
   trả dữ liệu NCC cũ từ identity map.
4. Strong ETag phiếu nhập hiện băm PhieuNhapRead: field NCC mới phải nhất quán giữa
   GET và `_check_etag` dưới khóa. **Sửa NCC làm ETag của phiếu thay đổi** dù row phiếu
   không đổi; client dùng tag cũ sẽ cần GET lại trước khi ghi. Không để GET trả một
   tag không thể dùng được ở mutation do hai bên băm hai DTO khác nhau.
5. Service phiếu nhập chỉ thay phần trình bày/hashing/snapshot serialization liên
   quan: không sửa trạng thái, validation vật tư/tiền, posting/ledger/idempotency.
   Audit phiếu loại field projection NCC khỏi snapshot persistence để không
   biến thông tin đọc liên kết thành nguồn snapshot NCC; audit NCC vẫn ghi trước/sau.
6. Test GET phiếu **đã hoàn tất** trước/sau PATCH NCC: tên/địa chỉ mới hiển thị, row
   phiếu/chi tiết/tiền/kho không đổi. Thêm test GET/lock DTO cùng tag và tag cũ bị
   chặn khi NCC thay đổi. Fixture hoàn tất được tạo hợp lệ bằng SQL test, không tuyên
   bố đã chạy thành công nghiệp vụ hoàn tất phiếu nếu không chạy endpoint đó.

Nếu phần đọc này bị chặn bởi bất tương thích schema khác, giữ phần độc lập, báo rõ
phụ thuộc và dừng phần bị ảnh hưởng; không refactor cả module phiếu nhập để làm xanh.
Không tự đổi numeric/Decimal cũ của phiếu thành integer trong tác vụ Catalog này.

## Steps

Mỗi task bắt đầu bằng test hành vi chưa đạt thích hợp, thay đổi nhỏ, kiểm tra rồi
cập nhật truy vết. Test dưới đây là **dự kiến**, chưa được viết hay báo pass.

| Task | Kết quả dự kiến | Phụ thuộc | Tiêu chí hoàn thành | UC/AC |
|---|---|---|---|---|
| T01 | Ghi nhận baseline/reuse fixture, lập test hành vi thiếu | Duyệt plan | Giữ R00 và 105 test; ghi riêng 8 lỗi nền; test mới không dùng app URL/DB | Tất cả; CAT-AC-01–08 |
| T02 | DTO tồn/query/guard và read Catalog | T01 | QTV đọc item, QTV/QLK đọc NCC, NV bị chặn NCC; đủ ba số tồn, không lộ BOM | UC-09/AC-2,3,6; UC-13/AC-2,3,5 |
| T03 | Query policy và pagination/filter nhất quán | T02 | Literal mã/tên, raw address không đổi, is_active TP-only, invalid query 422, stable ties/count/pages | UC-09/AC-1,4,5; UC-13/AC-1,4; CAT-AC-03 |
| T04 | SKU/reference/no-op/cache trong item writes | T02 | Chặn SKU/ĐVT đúng refs; no-op không UPDATE/audit/publish; tag/rollback và create/Bom/state regression giữ đúng | UC-10/AC-1–9; UC-11/AC-1–3,5–8; UC-12/AC-1,4,5,7; CAT-AC-02/04/05 |
| T05 | ORM NhaCungCap + Identity/trigger và read/write ports | T01 | Reflection đúng SQL v4, mã tự cấp, bắt buộc/raw fields, hết dải/unique có kiểm soát; cập nhật import trực tiếp | UC-14/AC-1–6; CAT-AC-02/08 |
| T06 | PATCH NCC + strong ETag/audit/no-op | T05 | QLK-only, row lock, 428/412/404/409/422, diff đúng, rollback và no-op; không DELETE | UC-44/AC-1–7,9; CAT-AC-01/04/05/07 |
| T07 | Read projection NCC hiện tại trên phiếu nhập | T06 | GET list/detail/DTO locked đồng bộ; tag round-trip; phiếu cũ đọc thông tin mới, không đổi storage/kho | UC-44/AC-8; UC-14 hậu điều kiện chọn được NCC; CAT-AC-06 |
| T08 | PostgreSQL/repository/concurrency/failure injection | T03,T04,T06,T07 | Hai session/cache độc lập; tạo mã không trùng, cùng tag không lost update; lỗi không lưu/audit/cache một phần | CAT-AC-04/05/06/08; UC-10/AC-8, UC-14/AC-6, UC-44/AC-9 |
| T09 | API integration và regression toàn phạm vi | T08 | Auth thật/DB roles, OpenAPI, headers/envelope/status, schema và 105 test BOM không hồi quy; báo đúng lỗi nền | CAT-AC-01/02/07 và các AC API |
| T10 | Sequence PNG, ví dụ HTTP, task/AC trace và bàn giao | T09 | Diagram khớp thực tế; mỗi AC có test hoặc lý do chưa E2E/UI; kết quả không khẳng định quá phạm vi | Tất cả UC/AC |

### Test trace after implementation

See [UC/AC/Endpoint/Service/Test trace](README.md#catalog-trace).

## Risk level and verification

**HIGH**: đổi public DTO/role/filter, ORM NCC, concurrency và projection liên module.
Không đổi schema/database thật. Xác minh từ hẹp đến rộng, không sửa test kỳ vọng để xanh.

- Baseline giữ 105 test BOM pass và ghi riêng 8 lỗi nhân viên. Test mới có UC/AC trong
  tên/docstring và bảng truy vết; không thêm test lặp chỉ để tăng số lượng.
- Test DB dùng fixture hiện có, bắt buộc `BOM_TEST_DATABASE_URL` trỏ server test
  `bom_test@127.0.0.1:55464/xbike_bom_test`, driver asyncpg; fixture tạo DB ngẫu nhiên,
  kiểm tra trống rồi chạy init.sql thật. Không seed app hoặc fallback app URL.
- PostgreSQL test tạm tách biệt, cleanup chỉ DB/container do task tạo. Thiếu môi
  trường PG: báo skip/chưa kiểm chứng, không coi là pass. Không SQLite/create_all
  để kết luận Identity/trigger/locking/computed column đúng.
- Auth/API dùng actual app qua DI test, không lifespan kết nối DB ứng dụng; kiểm tra
  thay role/khóa ngay cả JWT tự khai role khác. Response/evidence không ghi token/secret.
- Concurrency: hai connection độc lập, barrier/event thay sleep; cùng tag chỉ một
  thay đổi thắng, request stale 412, không audit lặp. Hai NCC khác nhau không ghi
  chồng; tạo đồng thời không trùng mã. Không tuyên bố stress/disconnect thật từ test mô phỏng.
- No-op: đối chiếu row/xmin hoặc update spy, count audit và publish cache; request
  stale vẫn bị chặn. Mapping NCC reflection gồm tên bảng/lớp, kiểu/null/default,
  Identity/trigger/unique/check/FK; không sửa SQL ngược theo ORM.
- Receipt Q6: kiểm tra đầy đủ list/detail/locked DTO cùng projection, ETag mới
  round-trip; không thay giá/trạng thái/row phiếu và không tạo snapshot NCC trên bảng.
- Ruff check/format, mypy scoped file đã sửa (ghi rõ cấu hình/stubs thiếu), import và
  OpenAPI đúng. Map structure chỉ đọc; boundary checker hiện thiếu architecture
  declaration nên ghi giới hạn, đối chiếu imports bằng source, không tạo cấu hình giả.
- Mermaid render/kiểm tra PNG, link spec/task/trace/test thật, `git diff --check` và
  scope diff không frontend/SQL/migration/production/dependency/test nhân viên.

Lệnh dự kiến sau triển khai (không phải kết quả đã chạy của Catalog):

```powershell
# Tại backend, với URL PostgreSQL test riêng đúng guard fixture.
..\.venv\Scripts\python.exe -m pytest tests/test_catalog_service.py tests/test_catalog_api.py tests/test_catalog_postgres.py -q
..\.venv\Scripts\python.exe -m pytest tests/test_bom_service.py tests/test_bom_api.py tests/test_bom_postgres.py tests/test_mat_hang_bom.py -q
..\.venv\Scripts\python.exe -m pytest tests -q --tb=line
# Tại root; chỉ file liên quan trong danh sách Placement và các test mới.
.\.venv\Scripts\ruff.exe check <cac-file-da-sua>
.\.venv\Scripts\ruff.exe format --check <cac-file-da-sua>
.\.venv\Scripts\mypy.exe --follow-imports=silent --disable-error-code import-untyped <cac-module-da-sua>
git diff --check
```

**Rollback note:** không migration up/down. Giữ diff hotfix R00 đã duyệt; nếu phải
hoàn tác code Catalog thì dev review đúng diff của tác vụ, không reset toàn branch
hoặc ghi đè thay đổi đang có. Backend cũ/schema cũ không tự tương thích SQL v4;
không reset/seed/xóa version/audit/database để quay về. Nếu áp dụng vào DB có dữ liệu,
cần tác vụ đồng bộ riêng do dev xác nhận, không nằm trong plan này.

## Open questions

Không còn câu hỏi nghiệp vụ Q1–Q6. Dev đã duyệt plan/task, gồm field tồn,
PATCH NCC và projection/ETag phiếu nhập; các phần này đã được triển khai.

Giới hạn giữ nguyên: không frontend; E2E duyệt xuất/sản xuất hoãn; không migration/
DB ứng dụng; lỗi nền nhân viên không sửa.

## Kết quả triển khai

T01–T10 hoàn thành trong phạm vi backend đã duyệt. Bảng
[truy vết từng UC/AC → endpoint/service → test](README.md#catalog-trace) ghi rõ
những AC đạt backend và phần UI/E2E chưa kiểm chứng.

| Nhóm file chính | Kết quả |
|---|---|
| `mat_hang/{router,schemas,service,cache,mutation,repository}.py` | Quyền đọc ba vai trò, Query DTO/literal/AND/stable sort, đủ ba số tồn; SKU theo refs, no-op không UPDATE/audit/publish; refresh cột tồn tính toán sau UPDATE; giữ R00 và nghiệp vụ BOM |
| `nha_cung_cap/{models,ports,repository,schemas,service,router}.py` | ORM NhaCungCap theo SQL v4; Identity/trigger cấp mã, raw fields bắt buộc; GET/POST ETag, PATCH QLK/row lock/If-Match/audit/no-op |
| `dependencies.py`, `core/request_context.py` | Audit NCC qua AuditService, cùng session; cấm body GET/DELETE, bảo toàn nhiều If-Match để service trả 412 |
| `phieu_nhap/{models,schemas,repository,service,router}.py` | Chỉ projection NCC hiện tại/view-only và hydration/tag/audit serialization/OpenAPI; giữ tiền/posting/trạng thái cũ |
| Ba file `tests/test_catalog_*.py` | Schema/service/API/real PostgreSQL, reflection, SQL no-op, rollback, concurrency và receipt projection |
| `docs/sequence/{mat_hang,nha_cung_cap,phieu_nhap}.md` + assets PNG | Render 16 sơ đồ thành công; preview ảnh PATCH NCC; cập nhật đúng tầng audit và dữ liệu đọc |
| `docs/examples/catalog-http.json` | 7 request/response chạy thật qua ASGI/auth và PostgreSQL test riêng, không lưu Authorization |
| Các spec Catalog | Giữ nội dung UC gốc, bổ sung AC/approval và truy vết kết quả |

Kiểm thử dùng PostgreSQL 16 tmpfs riêng tại cổng 55464. Fixture hiện có tạo DB ngẫu
nhiên, kiểm tra trống, chạy init.sql thực rồi cleanup chính DB vừa tạo; không kết
nối/nạp seed vào DB ứng dụng. Container test do tác vụ tạo được dừng sau kiểm chứng.

Kết quả:

- Catalog: **138 test pass**; BOM/tích hợp giữ nguyên: **105 test pass**.
- Toàn bộ `pytest tests -q --tb=line`: **243 pass, 8 fail**. Tám lỗi nền thuộc
  `test_nhan_vien_create_code.py:86`, fixture thiếu field `VaiTroRead.mo_ta`;
  không sửa module/test nhân viên ngoài phạm vi để làm xanh suite.
- Ruff check/format các source và test liên quan: pass. Import app và OpenAPI pass.
- Mypy scoped mặt hàng/NCC/request_context: pass, 18 source files, cấu hình
  `--follow-imports=silent --disable-error-code import-untyped` (asyncpg thiếu stubs).
- Mypy phiếu nhập: **15 lỗi type legacy còn tồn tại** ở service/repository/router.
  Đối chiếu bản HEAD trích riêng cho thấy cùng 15 nhóm lỗi, cộng thêm import Supplier
  cũ nay đã được sửa thành NhaCungCap. Không mở rộng refactor nghiệp vụ phiếu nhập.
- Mermaid CLI render **16/16** sơ đồ; ảnh PNG có liên kết trong sequence Markdown.
- Kiểm tra liên kết/file/test symbol, giữ phần UC gốc, diff/whitespace và scope đã
  thực hiện. Không có sửa frontend/SQL/seed/migration/module sản xuất/dependency manifest.
- Boundary checker không có `.clean/architecture.md` để chạy theo declaration;
  đã đối chiếu imports trực tiếp, không tạo cấu hình giả. Không báo toàn E2E đạt.

Lệnh kiểm tra chính (tại `backend`, URL test do người chạy cung cấp đúng guard fixture):

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_catalog_service.py tests/test_catalog_api.py tests/test_catalog_postgres.py -q
..\.venv\Scripts\python.exe -m pytest tests/test_bom_service.py tests/test_bom_api.py tests/test_bom_postgres.py tests/test_mat_hang_bom.py -q
..\.venv\Scripts\python.exe -m pytest tests -q --tb=line
..\.venv\Scripts\mypy.exe --follow-imports=silent --disable-error-code import-untyped app/modules/mat_hang app/modules/nha_cung_cap app/core/request_context.py
```

Giới hạn: chưa frontend; chưa E2E duyệt giá xuất/sản xuất; phiếu nhập legacy chưa nâng
đầy đủ tiền/posting theo SQL v4. Thay đổi bootstrap không được thực hiện và không
tự cập nhật database đang chạy. Không commit/push/stage thay đổi.

## Bổ sung UC-13 — tìm địa phương một phần, không dấu (17/11/2026)

Dev đã duyệt thay phần so khớp toàn bộ tên của Q3 bằng UC-13 R6/AC-6.
Không đổi payload, quyền, dữ liệu địa chỉ hay cách tìm `q` theo mã/tên.

| File | Thay đổi |
|---|---|
| `backend/app/modules/nha_cung_cap/repository.py` | Chuẩn hóa dấu/hoa thường tại predicate, contains literal trên tỉnh/phường; lọc SQL trước COUNT/phân trang, không cần extension |
| `backend/app/modules/nha_cung_cap/schemas.py` | Mô tả cách tìm mới trên OpenAPI, giữ nguyên kiểu/tham số |
| `backend/tests/test_catalog_api.py` | Test HTTP tìm không dấu, AND, total/page, QTV và giữ nguyên response có dấu |
| `backend/tests/test_catalog_postgres.py` | Test Unicode dựng sẵn/tổ hợp, đ/Đ, một phần tên, wildcard literal, blank, AND và dữ liệu/ETag/audit không đổi; sửa dữ liệu mẫu UC-44 để địa chỉ cũ/mới không chứa nhau |
| `specs/use_cases/catalog/UC-13.md` | R6/AC-6 và truy vết test |
| `specs/use_cases/catalog/README.md` | Quyết định Q3 mới và bảng truy vết |
| `specs/use_cases/catalog/PLAN.md` | Phương án, phạm vi và kết quả lượt bổ sung |
| `docs/sequence/nha_cung_cap.md` | GET list phản ánh predicate mới |
| `docs/sequence/assets/nha_cung_cap/nha-cung-cap-1.png` | Render lại sơ đồ GET list bằng Mermaid CLI/Chrome; đã xem ảnh |

Kết quả thực tế:

- Nhóm test tìm kiếm: **20 pass** trên PostgreSQL 16 test riêng cổng 55464.
- Toàn bộ ba file Catalog service/API/PostgreSQL: **169 pass, 1 fail, 0 skip**.
  Lỗi còn lại `test_uc12_ac01_repeated_stop_does_not_publish_or_audit` thuộc cache
  ngừng mặt hàng; đã tái hiện cùng lỗi khi nạp repository/schema NCC nguyên bản từ
  HEAD vào tiến trình test riêng. Không sửa ngoài phạm vi UC-13, không bỏ/skip test.
- Ruff check/format đạt; Mypy module NCC đạt (7 source files); `git diff --check` đạt.
- Chrome kết nối API thật: **6/6** ca lọc đạt, HTTP 200, không lỗi JavaScript;
  `ha noi` trả NCC-000002 (`Thành phố Hà Nội`), `ho chi minh` + `minh hoa` trả
  NCC-000001, kết hợp không khớp trả rỗng; lọc riêng phường và ký tự `%` đúng.
- Test ghi dữ liệu chỉ dùng database tạm do fixture BOM tạo trong container test
  riêng; không nạp seed, thay schema hoặc ghi thử NCC vào database ứng dụng.
- Uvicorn đã được khởi động lại để nạp code mới. Frontend không cần sửa trong lượt
  bổ sung này; giữ nguyên các thay đổi giao diện có sẵn. Không commit/push/stage.
