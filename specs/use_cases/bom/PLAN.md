# Plan: Backend BOM — UC-15 đến UC-19

**APPROVED — dev đã duyệt plan/task và yêu cầu triển khai/test ngày 14/11/2026.**
Phần backend đã triển khai; [kết quả thực tế và giới hạn](README.md#8-kết-quả-triển-khai-và-truy-vết-thực-tế).
T01–T10 hoàn thành trong phạm vi backend được duyệt; phần frontend/sản xuất v4 giữ hoãn.
Các đoạn “dự kiến/chờ duyệt” bên dưới lưu phương án trước triển khai, không thay thế kết quả thực tế.

## Goal

Triển khai phần backend BOM một cấp theo [spec đã duyệt](README.md), có truy vết
UC/AC, kiểm thử hành vi service/API và PostgreSQL thật cho transaction/đồng thời.
Các AC phụ thuộc sản xuất v4 và frontend được ghi riêng là chưa nghiệm thu theo Q3.

## Context read

- `AGENTS.md`, `backend/pyproject.toml`, `README.md` ở gốc.
- [UC-15](UC-15.md), [UC-16](UC-16.md), [UC-17](UC-17.md), [UC-18](UC-18.md),
  [UC-19](UC-19.md); UC-10/12 của catalog, UC-23/24 và phần gửi yêu cầu trong code.
- [BR-GIAIDOAN1](../../business_requirements/BR-GIAIDOAN1.md),
  [model v4](../../entity_model/data_model_v4.md),
  [init.sql](../../../infra/postgres/init.sql), `seed.sql` khi kiểm chứng fixture.
- Sáu file của module `bom`; `mat_hang` router/schema/model/ports/repository/service,
  cache/synchronizer; `audit` model/schema/ports/repository/service;
  `dependencies.py`, `core/errors.py`, `core/exceptions.py`, transaction adapter.
- `san_xuat/ports.py`, `_calculate/gui` trong service yêu cầu sản xuất để xác nhận
  `BomPlanningReader.lock_graph/active_graph` vẫn có caller và thứ tự khóa hiện tại.
- Test hiện có: `backend/tests/test_nhan_vien_create_code.py`.
- Skill clean-code: Python/FastAPI, transaction/concurrency, test và review; không
  áp dụng superpowers hay skill GitNexus để điều phối. Không có `.clean/` hiện hữu.

Các quyết định đã chốt: chỉ backend; nguồn v4; công thức không rỗng và một cấp;
tích hợp catalog/audit tối thiểu; không refactor sản xuất; BOM lặp sai trạng thái
trả 409; strong ETag bắt buộc cho ba thao tác đổi BOM. Không migration, không sửa
database đang có dữ liệu, không nâng dependency.

## Existing code to reuse

| Thành phần hiện có | Cách dùng |
|---|---|
| `BomService`, `SqlAlchemyBomRepository`, Protocol trong `bom/ports.py` | Sửa tại module hiện có; bỏ quy tắc nhiều cấp trong các UC này |
| `BomPlanningReader`, `ActiveBom`, advisory lock `(20261020, 2)` | Giữ hợp đồng nội bộ cho caller sản xuất cũ; graph trả công thức một cấp hợp lệ |
| `MatHangService._mutation`, `MatHangCache.prepare/publish` | Tách đúng khối transaction/cache thành collaborator dùng chung cho catalog và BOM, không tạo cơ chế cache thứ hai |
| `SqlAlchemyTransaction`, `get_db` | Một session và một commit/rollback cho toàn bộ thao tác |
| `AuditService.append`, `SqlAlchemyAuditRepository.append`, `CreationAudit` | Ghi audit qua service, không cho repository commit |
| Auth dependency, `require_roles` | Tái sử dụng auth đang có; bổ sung guard nghiệp vụ ở service |
| `PreconditionRequiredException`, `PreconditionFailedException` | Dùng đúng mã lỗi 428/412 đã được handler ánh xạ; không tạo HTTPException trong BomService |
| `generate_mat_hang_etag`, `verify_if_match` | Giữ điểm gọi công khai hiện có; dùng chung kiểm tra strong If-Match cho phần liên quan, không sửa các module chứng từ khác |

## Placement

Chỉ các file dưới đây được dự kiến thay đổi. File chưa tồn tại được ghi **mới**;
nếu phát hiện cần thêm file/phạm vi khác, phải giải thích trước khi thực hiện.

| File/nhóm file | Vai trò và thay đổi dự kiến |
|---|---|
| `backend/app/modules/bom/{router,service,ports,repository,models,schemas}.py` | Endpoint/DTO v4; guard, version, trạng thái, ETag; persistence đúng SQL |
| `backend/app/modules/mat_hang/{router,service,ports,repository,models,schemas}.py` | Tạo thành phẩm kèm công thức, mã hệ thống cấp; khóa và đổi trạng thái cùng Bom; đọc trạng thái để tính ETag; sửa truy vấn tham chiếu trực tiếp còn dùng bảng cũ |
| **Mới** `backend/app/modules/mat_hang/mutation.py` | Tách khối transaction/cache đang có ở `_mutation` để hai service dùng chung, tránh lặp hoặc nested commit/cache lock |
| **Mới** `backend/app/core/preconditions.py` | Helper thuần cho tạo canonical hash và kiểm tra một strong If-Match, được BOM và catalog liên quan dùng chung; không thay chính sách module khác |
| `backend/app/modules/audit/models.py`, `schemas.py` | Đồng bộ mapping trạng thái, constraint/index SQL v4; DTO đọc chấp nhận mã BOM mới, DTO ghi có trạng thái trước/sau |
| `backend/app/dependencies.py` | Ghép AuditService và collaborator transaction/cache dùng chung; không tạo vòng phụ thuộc giữa service |
| **Mới** `backend/tests/test_bom_service.py`, `test_bom_api.py`, `test_bom_postgres.py`, `test_mat_hang_bom.py` | Test có định danh UC/AC; test catalog chỉ cho phần phụ thuộc BOM |
| `docs/sequence/bom.md`, `docs/sequence/mat_hang.md` và PNG tương ứng | Cập nhật endpoint thực tế sau triển khai, auth/errors/transaction/audit và phần thay đổi catalog |
| `specs/use_cases/bom/{README,PLAN,UC-15,UC-16,UC-17,UC-18,UC-19}.md` | Trạng thái, task, bảng truy vết tới symbol/test thật và kết quả |
| **Mới** `docs/examples/bom-http.json` | Bằng chứng request/response thực chạy sau triển khai, che token/secret |

Không sửa frontend, bootstrap SQL/seed, migration, dependency manifests, cấu hình
database, các service sản xuất, phiếu nhập/xuất hoặc toàn bộ chức năng đọc audit UC-43.
`main.py` đã đăng ký router/model liên quan, không cần đổi đăng ký nếu tên module giữ nguyên.

### A. API đề xuất để dev duyệt

Các endpoint dưới đây là **đích của plan, chưa triển khai**. Giữ prefix và các GET
hiện có; đổi một đường dẫn POST để resource gốc dùng cho ETag được xác định rõ.

| UC | Method/path đích | Payload/query | Thành công và header |
|---|---|---|---|
| UC-15 | `GET /api/v1/bom` | `page`, `page_size`, `mat_hang_id`, `version`, `is_active`, `sort` | 200 `{data: [...], meta: {request_id, page, page_size, total, total_pages}}` |
| UC-15 | `GET /api/v1/bom/{id}` | Không query/body | 200 `{data: BomRead, meta: {request_id}}`, strong `ETag` |
| UC-15 | `GET /api/v1/bom/{id}/cau_truc` | Không query/body | 200, giữ shape cây hiện tại nhưng chỉ có linh kiện lá, `bom_id: null`, `children: []`; không phân rã node con |
| UC-10/16 | `POST /api/v1/mat_hang` | Thông tin mặt hàng; thành phẩm bắt buộc có `bom: {chi_tiet: [...]}` | 201 theo envelope mặt hàng hiện có, `Location`, ETag mặt hàng; không If-Match |
| UC-17 | **Mới** `POST /api/v1/bom/{id}/phien_ban` | `{chi_tiet: [...]}` + If-Match của GET chi tiết **đúng id này** | 201 với BomRead version mới, `Location: /api/v1/bom/{new_id}`, ETag của version mới |
| UC-18 | `POST /api/v1/bom/{id}/kich_hoat` | Body `{}` bắt buộc, If-Match của GET chi tiết đúng id | 200 BomRead và ETag sau kích hoạt |
| UC-19 | `DELETE /api/v1/bom/{id}` | Không body/query, If-Match của GET chi tiết đúng id | 204 rỗng; chỉ ngừng, không DELETE dòng SQL |

- `id` của POST tạo version là một version hiện hữu thuộc thành phẩm cần đổi;
  lấy thành phẩm từ version đó, không nhận lại `mat_hang_id` để client đổi chủ.
  Được dùng một version cũ làm nguồn thao tác, nhưng ETag của nó phải phản ánh trạng
  thái công thức hiện tại. Nội dung gửi lên là toàn bộ công thức mới, không sửa nguồn.
- **Bỏ `POST /api/v1/bom` cũ** khi thay bằng POST `/{id}/phien_ban`; gọi đường cũ
  trả 405, không để alias âm thầm tạo v1 riêng. Đây là thay đổi cần duyệt trong plan.
- Không thêm PATCH sửa Bom/ChiTietBom tại chỗ hoặc endpoint xóa cứng.
- Role đọc BOM QLK/NV; role ghi QLK. Không mở quyền QTV vào BOM hoặc thay quyền đọc
  catalog hiện có để hoàn thiện các UC catalog ngoài phạm vi.
- Giữ filter/default hiện tại: page 1, page_size 20, tối đa 100; sort mặc định `id`;
  whitelist `id/-id`, `version/-version`, `created_at/-created_at`,
  `kich_hoat_gan_nhat_at/-kich_hoat_gan_nhat_at`; thêm ID làm khóa phụ ổn định.
  Query lạ/trùng hoặc sort cũ `start_time/-start_time` trả 422; không thêm tìm kiếm
  nâng cao chưa có trong UC BOM.
- Giữ `BomRead`: `id`, `mat_hang_id`, `version`, `is_active`,
  `da_duoc_su_dung`, `chi_tiet`; thay `start_time/end_time` bằng hai timestamp v4.
  `da_duoc_su_dung` đọc `EXISTS YeuCauSanXuat.bom_id`, không đọc LenhSanXuat.
  ID và số lượng là integer trong giới hạn kiểu SQL; lượng boolean/phần lẻ bị 422.
  Thời gian đầu ra UTC; không nhận version, trạng thái hoặc thời gian từ client.
- Giữ envelope thành công/lỗi `{data, meta}` / `{error, meta}` đang áp dụng cho BOM
  và catalog; không đổi global handler hoặc các resource khác.
- Quy ước lỗi trong phần nghiệp vụ: không tồn tại 404; input sai 422; trạng thái/
  ràng buộc xung đột 409. Auth/role được kiểm tra trước nghiệp vụ. Với request đã
  qua validation và có resource: thiếu If-Match 428, cũ/weak/wildcard 412, sau đó mới
  xét 409 trạng thái. Không cam kết thứ tự giữa nhiều lỗi cấu trúc xảy ra đồng thời.

### B. Request catalog và các đường ghi trạng thái liên quan

- `MatHangCreate` bỏ mã client nhập; chỉ nhận `thanh_pham`/`linh_kien`. Thành phẩm
  bắt buộc có `bom.chi_tiet` không rỗng; linh kiện không nhận công thức có nội dung.
  Không cho client đặt `is_active`, số dư hoặc thời gian khi tạo; server tạo active.
- Dùng Identity/trigger cấp `MH-NNNNNN` đang có trong SQL; không dùng MAX+1 hay cấp
  ID thủ công. Adapter đọc lại giá trị trigger sau flush; hết dải mã phải được ánh
  xạ thành lỗi rõ ràng, không trả 500 chung hoặc tái sử dụng mã.
- `MatHangPatch` không nhận mã/loại sau khi tạo. Giữ các field sửa mô tả hiện có;
  nếu nhận `is_active` cho thành phẩm thì gọi cùng nghiệp vụ đổi Bom, không UPDATE
  riêng MatHang. Linh kiện không được đặt inactive.
- Giữ `DELETE /mat_hang/{id}` là ngừng mềm thành phẩm; không xóa cứng. Ngừng thành
  phẩm phải ngừng version active, dùng lại qua PATCH phải chọn version có thời điểm
  kích hoạt gần nhất, không mặc định chọn số version lớn nhất.
- Giữ tính lặp của route catalog: DELETE thành phẩm đã inactive với ETag hiện tại
  là no-op 204; PATCH trạng thái bằng giá trị hiện tại không tạo lifecycle event.
  Q5 áp dụng cho action BOM đích đã sai trạng thái, không tự biến DELETE catalog cũ
  thành một hành vi khác. Patch các thuộc tính khác vẫn được audit theo thay đổi.
- MatHangRead giữ các field đang công khai; không mở rộng API tồn/giữ hàng. ORM
  MatHang được đồng bộ cột/constraint v4 liên quan, gồm cột sinh `so_luong_con_dung`
  chỉ đọc; không cho schema ghi trực tiếp các số dư.
- `get_references` chỉ truy vấn bảng v4 thực có để bảo vệ đơn vị tính; bỏ tham chiếu
  `LenhSanXuat`, bảng điều chỉnh/ticket cũ trong truy vấn này. Không refactor module
  sở hữu các bảng cũ hoặc đổi luật tồn/giữ hàng.
- Nếu gặp thành phẩm cũ không có bất kỳ Bom nào: trả 409 khi cần dùng lại/đổi version;
  không tự tạo công thức rỗng hoặc sửa dữ liệu ứng dụng để “chữa” trạng thái.

### C. Ranh giới service, transaction và cache

Tên hiện có tiếp tục dùng; tên ghi **mới** là symbol dự kiến, chưa được tạo.

- `BomService.list_bom/get_bom/get_cau_truc`: guard quyền đọc và trả DTO thuần,
  không truy vấn SQL trong router, không ghi audit khi đọc.
- **Mới** `BomService.create_version`: triển khai UC-17 thay nghĩa tên tạo chung;
  `activate_bom/delete_bom` triển khai UC-18/19, có nguồn UC trong docstring.
- **Mới** `BomService.create_initial_formula`, `stop_for_item_in_transaction`,
  `reuse_last_for_item_in_transaction`: thao tác phối hợp UC-10/12/16 do catalog
  gọi qua service công khai, actor/điều kiện vẫn được kiểm tra. Các hàm này không
  tự mở transaction, giữ cache lock hoặc commit; caller phải sở hữu mutation scope.
  Chúng dùng cùng phần kiểm tra/chuyển trạng thái với action BOM, tránh hai bản luật.
- **Mới** `MatHangMutation` trong `mat_hang/mutation.py`: chuyển nguyên trách nhiệm
  context `_mutation` đang có sang một chỗ, được hai service tái sử dụng. Lý do tạo
  collaborator này là bảo vệ cùng bất biến DB/cache từ cả hai module, không tạo
  framework UnitOfWork tổng quát hoặc đổi transaction toàn ứng dụng.
- BomService phụ thuộc BomRepository và port MatHangRepository để đọc/ghi trạng
  thái mặt hàng. MatHangService gọi BomService; BomService không gọi ngược
  MatHangService. Collaborator mutation độc lập giúp không tạo import/call cycle.
- `dependencies.py` ghép các object với **cùng AsyncSession** qua DI hiện có;
  AuditWriter thực tế phải là AuditService, không phải SqlAlchemyAuditRepository.

Luồng tạo thành phẩm:

```text
MatHang router → MatHangService.create_mat_hang
  → MatHangMutation (cache lock + transaction của caller)
  → MatHangRepository.add
  → BomService.create_initial_formula → BomRepository
  → AuditService → SqlAlchemyAuditRepository (audit cả mặt hàng và công thức)
  → prepare cache → commit một lần → publish cache → trả response
```

Luồng action BOM:

```text
Bom router → BomService (guard role)
  → MatHangMutation (cache lock + transaction)
  → BomRepository / MatHangRepository (khóa, đọc lại, đối chiếu ETag)
  → chuyển trạng thái/version → AuditService → SqlAlchemyAuditRepository
  → prepare cache → commit một lần → publish cache → trả response
```

- Thứ tự khóa trong những đường ghi liên quan: cache lock của process → transaction
  → advisory lock BOM hiện có → hàng MatHang theo ID tăng → hàng Bom theo ID tăng.
  Không khóa item trước rồi mới đợi advisory lock. Giữ cùng advisory key với
  `BomPlanningReader.lock_graph`; caller sản xuất hiện cũng khóa graph trước đọc item.
- Một thao tác chỉ có một mutation scope; không lồng context commit của BomService
  bên trong transaction catalog. Validate cấu trúc trước scope; validate dữ liệu/
  trạng thái và so ETag bằng dữ liệu DB sau khi có khóa.
- Đóng version đang dùng phải flush trước khi kích hoạt/tạo version mới để tôn trọng
  partial unique index. Dùng lại giữ nguyên ID/version/created_at/chi tiết, chỉ đổi
  active và thời điểm kích hoạt; ngừng không đổi thời điểm kích hoạt.
- Trường hợp lỗi ghi/audit/commit: rollback toàn bộ, không publish; nếu kết quả commit
  không chắc chắn thì đánh dấu cache unavailable theo cơ chế sẵn có. Sau commit thành
  công, snapshot của process xử lý request phải cập nhật trước khi trả response.
- Giữ LISTEN/NOTIFY `mat_hang_changed` và reconciliation đang có cho process khác.
  Không hứa mọi instance cập nhật cache đồng bộ tức thì; GET cấp ETag và thao tác ghi
  dùng snapshot DB có thẩm quyền, không dựa trên cache trễ để chấp nhận ghi.

### D. Strong ETag và chống cập nhật dựa trên dữ liệu cũ

- `core/preconditions.py` là helper thuần được dùng chung, không SQL hoặc HTTP I/O.
  Hàm kiểm tra chỉ nhận một tag có dấu nháy kép đúng định dạng server sinh; không
  bỏ dấu nháy rồi so mơ hồ. Thiếu/rỗng là 428; weak, wildcard, danh sách nhiều tag,
  giá trị sai định dạng hoặc không khớp là 412. Dùng exception dự án đã có.
- ETag GET `/bom/{id}` băm canonical JSON của **DTO version được đọc**, kèm trạng
  thái công thức của thành phẩm: active version ID/thời điểm kích hoạt, version
  lớn nhất và `MatHang.is_active`. Không băm request_id hoặc dữ liệu nhạy cảm.
- Vì ngữ cảnh có active version và thời điểm kích hoạt, tag của version cũ cũng đổi
  khi quản lý khác dùng lại/ngừng/tạo version. Không bỏ lọt trường hợp quay lại cùng
  một active version sau nhiều lần chuyển trạng thái.
- Header dùng cho `POST /bom/{id}/phien_ban`, kích hoạt và DELETE đều lấy từ GET
  chi tiết **cùng id**. POST version mới trả tag của `new_id`; muốn thao tác tiếp
  trên id cũ thì GET lại id đó. Không dùng tag từ danh sách, cấu trúc cây hay mặt hàng
  thay cho tag chi tiết BOM.
- GET chi tiết mặt hàng thành phẩm cấp tag riêng, gồm DTO mặt hàng và ngữ cảnh BOM
  tương ứng. GET này đọc snapshot DB thay cho việc ghép cache cũ với trạng thái BOM
  mới; danh sách/catalog còn dùng cache hiện có. Các mutation catalog đối chiếu
  cùng loại tag trong DB dưới khóa. Linh kiện giữ cách tính tag từ dữ liệu mặt hàng.
- Repository lấy header/version và ngữ cảnh active từ cùng snapshot truy vấn; chi
  tiết version là dữ liệu bất biến. Không tính tag trước ghi từ cache, hoặc đọc
  trạng thái active ở một thời điểm rồi trả body/version ở một thời điểm khác.
- POST mới/kích hoạt/patch trả representation và tag được chuẩn bị trong transaction
  sau thay đổi; nếu một request khác đổi tiếp ngay sau commit thì tag có thể đã cũ,
  đây là tình huống hợp lệ và lần ghi kế tiếp phải bị chặn khi dùng tag đó.

### E. Audit tối thiểu và dữ liệu không được thay đổi

| Thao tác | Audit bắt buộc trong cùng transaction |
|---|---|
| UC-10/16 | `mat_hang/tao` và `cong_thuc/tao` |
| UC-17 | `cong_thuc/tao_phien_ban`; thêm `mat_hang/dung_lai` nếu thành phẩm chuyển inactive → active |
| UC-18 | `cong_thuc/dung_lai_phien_ban`; thêm `mat_hang/dung_lai` nếu thành phẩm chuyển inactive → active |
| UC-19 | `cong_thuc/ngung` và `mat_hang/ngung` |
| UC-12 phụ thuộc | Cùng hai đối tượng khi ngừng/dùng lại; không ghi lặp lifecycle event qua hai service |

- Snapshot trước/sau gồm version cũ/đích/mới liên quan và trạng thái thành phẩm đủ
  để truy lại chuyển đổi; khi tạo v1, trước là null. Đối tượng `cong_thuc` dùng ID
  version đích/mới. Trạng thái mô tả `dang_dung`/`da_ngung`; không bắt buộc lý do ngừng
  vì UC không quy định. Không sửa/xóa audit hay lưu token/password.
- Đồng bộ audit ORM với SQL v4 hiện có và bổ sung trường trạng thái trong DTO. Schema
  đọc phải đọc được mã BOM mới; giữ tương thích giá trị cũ ở bộ lọc đọc nếu có, không
  đổi API ghi của các module khác hoặc tự chuyển enum cũ của chúng.
- Giữ GET audit hiện có, chỉ sửa schema cần thiết; không thêm detail endpoint hay
  triển khai lại bộ lọc UC-43 trên nhánh này.
- Mọi test mutation phải đối chiếu tồn, phần đang giữ và ledger không thay đổi.
  Không ghi YeuCauSanXuat/NhuCauLinhKien khi chuyển version; dữ liệu fixture cho
  chúng chỉ được tạo trong test DB để kiểm chứng bất biến.

### F. Tương thích nội bộ và giới hạn sản xuất

- Giữ `ActiveBom`, `BomPlanningReader.lock_graph/active_graph` và shape kết quả mà
  `PlanningBomReader` đang dùng. Bỏ đệ quy trong các endpoint BOM, không xóa port
  còn được caller sản xuất sử dụng.
- Kiểm thử adapter trên dữ liệu v4 chứng minh graph một cấp và tương thích kiểu/
  lời gọi. Không coi đó là đã chuyển các endpoint sản xuất từ mô hình LenhSanXuat.
- Không sửa module sản xuất để “làm xanh” E2E. Nếu có caller cần hành vi nhiều cấp
  không thể tiếp tục với dữ liệu v4, dừng phần liên quan, báo cụ thể; không tự bổ
  sung bán thành phẩm hoặc đảo ngược schema v4.

## Steps

Mỗi task sau khi được duyệt làm theo vòng test hành vi thất bại → thay đổi nhỏ →
kiểm tra → cập nhật truy vết. Không viết một loạt test giả rồi đánh dấu toàn bộ đạt.

| Task | Kết quả dự kiến | Phụ thuộc | Tiêu chí hoàn thành | UC/AC |
|---|---|---|---|---|
| T01 | Ghi nhận baseline, dựng fixture/fake service và test DB độc lập | Duyệt plan | Test mới nhận diện UC/AC; đường dẫn DB test bắt buộc, không fallback DB ứng dụng; ghi rõ 8 lỗi nền nhân viên | Tất cả UC; BOM-AC-01–08 |
| T02 | Mapping Bom/ChiTietBom, phần MatHang/audit phụ thuộc đúng SQL v4 | T01 | Reflection kiểu/null/default/FK/unique/index/trigger đạt trên PG; không đổi bootstrap/migration | UC-16–19; BOM-AC-02/04/06 |
| T03 | GET BOM một cấp, query và snapshot/ETag cho đọc chi tiết | T02 | QLK/NV được đọc, QTV bị chặn, filter/count/page/sort và 404/422 đúng; không ghi DB; graph nội bộ còn tương thích | UC-15/AC-1–7; BOM-AC-01/03/07 |
| T04 | Mutation/cache scope và ghi audit qua service | T02 | DI cùng session, không vòng phụ thuộc/nested commit; test lỗi audit và commit không publish cache | BOM-AC-04; phần hạ tầng UC-16–19 |
| T05 | UC-16 tạo v1 qua tạo thành phẩm, mã hệ thống, validation | T03,T04 | Thành phẩm/Bom/audit tạo cùng lúc hoặc cùng rollback; LK vẫn tạo được không công thức; input mới/OpenAPI đúng | UC-16/AC-1–7; UC-10/AC-1–5,7; BOM-AC-01/02/04/07 |
| T06 | UC-17 tạo version qua POST mới và bỏ POST cũ | T03,T04 | Version tăng duy nhất, version trước bất biến, tự dùng lại thành phẩm, ETag cũ/thiếu bị chặn, audit đúng | UC-17/AC-5–7; phần dữ liệu AC-1–4; BOM-AC-02/04–07 |
| T07 | UC-18/19 và đồng bộ đường trạng thái catalog | T05,T06 | Dùng lại/ngừng nguyên tử, thời gian đúng, Q5 409, UC-12 chọn version gần kích hoạt nhất; cache/GET ETag đúng | UC-18/AC-1,3–6; UC-19/AC-1,6–8; phần phụ thuộc UC-12; BOM-AC-04–08 |
| T08 | PostgreSQL concurrency, failure injection và bảo vệ dữ liệu chốt | T05–T07 | Hai session độc lập cạnh tranh thật, không deadlock/hai active/trùng version; lỗi giữa bước rollback cả audit/Bom/item; dữ liệu chốt/kho giữ nguyên | BOM-AC-04/05/06; UC-17/AC-5–7, UC-18/AC-4–5, UC-19/AC-6–7 |
| T09 | API integration và regression phạm vi | T05–T08 | Auth thật qua DI test, status/envelope/schema/header/route mới/cũ đúng; GET audit hiện có đọc mã mới được; không thêm lỗi ngoài baseline | BOM-AC-01/07/08; AC backend của năm UC |
| T10 | Sequence/PNG, ví dụ HTTP, bảng truy vết và bàn giao | T09 | Diagram khớp endpoint thực, Mermaid render được; mọi AC có test thật hoặc trạng thái hoãn/phụ thuộc; báo kết quả thực | Tất cả UC/AC, không đánh dấu các phần hoãn đã đạt |

### Bảng truy vết test dự kiến

Tên dưới đây là **mới/dự kiến**, chưa phải test đã viết hoặc đã pass. Có thể dùng
parametrize cho các biến thể nhưng giữ mã UC/AC trong tên/docstring và bảng truy vết.

| UC / AC | Endpoint / service đích | Nhóm test dự kiến | Mức kiểm chứng |
|---|---|---|---|
| UC-15/AC-1,5–7; BOM-AC-03 | Ba GET BOM / `BomService.list_bom/get_bom/get_cau_truc` | `test_bom_api.py::test_uc15_*`, `test_bom_postgres.py::test_uc15_*` | Đọc version, query, DB không đổi |
| UC-15/AC-2–4; BOM-AC-01 | Router + service guard | `test_bom_api.py::test_uc15_roles_*`, `test_bom_service.py::test_bom_ac01_*` | Backend; phần hiển thị nút UI hoãn |
| UC-16/AC-1–4,7; BOM-AC-02 | POST mặt hàng / `MatHangService.create_mat_hang` + `BomService.create_initial_formula` | `test_mat_hang_bom.py::test_uc16_validation_*` | Schema/API/service, dữ liệu lỗi không lưu |
| UC-16/AC-5–6; BOM-AC-04 | Cùng hai service, mutation scope và audit | `test_bom_postgres.py::test_uc16_atomic_*`, `test_mat_hang_bom.py::test_uc16_cache_*` | PG thật, rollback và publish cache |
| UC-17/AC-5–7 | POST version / `BomService.create_version` | `test_bom_service.py::test_uc17_*`, `test_bom_postgres.py::test_uc17_*` | Version, bất biến, audit, concurrency |
| UC-17/AC-1–4 | Dữ liệu version và liên kết đã chốt; API sản xuất ngoài phạm vi | `test_bom_postgres.py::test_uc17_preserves_committed_request_*` | Chỉ bất biến dữ liệu; gửi/kiểm tra/lập yêu cầu thực còn phụ thuộc Q3 |
| UC-18/AC-1,3–6 | Kích hoạt / `BomService.activate_bom` | `test_bom_service.py::test_uc18_*`, `test_bom_api.py::test_uc18_*`, `test_bom_postgres.py::test_uc18_*` | Trạng thái, timestamp, rollback, 409; phần catalog sau dùng lại được test trong test_mat_hang_bom |
| UC-18/AC-2 | API gửi yêu cầu ngoài phạm vi | Chưa tự động hóa trong tác vụ này | Hoãn tích hợp sản xuất v4, không báo đạt |
| UC-19/AC-1,6–8 | DELETE BOM / `BomService.delete_bom` | `test_bom_service.py::test_uc19_*`, `test_bom_api.py::test_uc19_*`, `test_bom_postgres.py::test_uc19_*` | Ngừng, no hard delete, transaction, Q5 |
| UC-19/AC-2–5 | Trạng thái thành phẩm test được; các API lập/gửi/tiếp tục sản xuất ngoài phạm vi | `test_mat_hang_bom.py::test_uc19_item_state_*` cho phần trạng thái; E2E chưa tự động hóa | Không đánh dấu toàn bộ AC đạt khi mới có trạng thái DB |
| UC-10/12 phụ thuộc | POST/PATCH/DELETE mặt hàng / MatHangService phối hợp BomService | `test_mat_hang_bom.py::test_uc10_*`, `test_uc12_*` | Chỉ phạm vi BOM/catalog đã chốt; không tuyên bố toàn bộ UC-10/12 hoàn tất |
| BOM-AC-04–08 | Các mutation, repository, audit | `test_bom_postgres.py::test_bom_ac04_*` đến `test_bom_ac08_*`; `test_bom_api.py::test_bom_preconditions_*` | Transaction/SQL thật, lỗi HTTP và không thay đổi kho |

## Risk level and verification

**HIGH**: thay hợp đồng HTTP, chạm dữ liệu lưu trữ/ORM, phân quyền và đồng thời,
đi qua ranh giới BOM/catalog/audit. Plan không đổi schema ứng dụng hoặc dữ liệu thật.

Các lệnh dưới đây là **kiểm tra sẽ chạy sau triển khai**, không phải kết quả hiện có:

```powershell
# Tại repository root, chỉ các file thuộc diff được lint/format check.
.\.venv\Scripts\ruff.exe check backend/app/modules/bom backend/app/modules/mat_hang backend/app/modules/audit backend/app/core/preconditions.py backend/app/dependencies.py backend/tests/test_bom_service.py backend/tests/test_bom_api.py backend/tests/test_bom_postgres.py backend/tests/test_mat_hang_bom.py
.\.venv\Scripts\ruff.exe format --check backend/app/modules/bom backend/app/modules/mat_hang backend/app/modules/audit backend/app/core/preconditions.py backend/app/dependencies.py backend/tests/test_bom_service.py backend/tests/test_bom_api.py backend/tests/test_bom_postgres.py backend/tests/test_mat_hang_bom.py

# Tại backend; đặt BOM_TEST_DATABASE_URL tới PostgreSQL test riêng trước test PG.
..\.venv\Scripts\python.exe -m pytest tests/test_bom_service.py tests/test_bom_api.py tests/test_mat_hang_bom.py -q
..\.venv\Scripts\python.exe -m pytest tests/test_bom_postgres.py -q
..\.venv\Scripts\python.exe -m pytest tests -q
..\.venv\Scripts\mypy.exe --follow-imports=silent app/modules/bom app/modules/mat_hang app/modules/audit app/core/preconditions.py
```

- Guard URL test bắt buộc, không lấy `settings.database_url` làm fallback. Test DB
  mới/trống, tên ngẫu nhiên có tiền tố riêng; bootstrap bằng SQL thật, không app seed.
  Cleanup chỉ đúng tài nguyên test đã tạo, không database/volume ứng dụng. Thiếu môi
  trường PostgreSQL thì báo chưa kiểm chứng concurrency/transaction, không báo pass.
- Test ít nhất hai connection/session thật, đồng bộ bằng barrier/event thay vì
  sleep để hy vọng đụng nhau. Cùng ETag: tối đa một thao tác đổi thành công; thao tác
  còn lại 412 khi state đã đổi. Hai thành phẩm không được tác động lẫn nhau.
- Test failure injection sau ngừng version cũ, sau tạo header/detail, trước audit
  và khi commit; assert DB, cache, audit, stock/holds/ledger và dữ liệu chốt.
- Test trigger/version bất biến bằng SQL ở test DB; reflection đối chiếu SQL v4,
  không dùng metadata.create_all/SQLite để suy ra tương thích PostgreSQL.
- Test OpenAPI/router bằng app thực qua DI test, không chạy lifespan với URL ứng
  dụng. Ghi ví dụ HTTP thực, không đưa secret/JWT vào artifact.
- Dùng `map_structure.py --path backend/app/modules/bom` và phần catalog/audit liên
  quan ở chế độ chỉ đọc; `check_boundaries.py --root .` nếu có cấu hình. Hiện không
  có `.clean/architecture.md`: nếu tool không thể kết luận thì ghi rõ và kiểm tra
  imports/call graph bằng source, không tự tạo kiến trúc mới chỉ để chạy tool.
- Đối chiếu Mermaid từng endpoint sau triển khai; dùng mmdc đã có trong `.venv`,
  xuất PNG và kiểm tra ảnh. Không cập nhật diagram tương lai thành endpoint đang có.
- `git diff --check`, rà soát diff không frontend/SQL/migration/dependency/production;
  không stage/commit/push. Không sửa 8 test lỗi nền nhân viên để làm xanh toàn suite.

**Rollback note:** code cần quay lại theo các file trong diff được dev chốt; không
chạy git reset/restore tự động, không xóa dữ liệu hoặc volume. Không có migration
up/down. Code cũ dùng schema cũ không phải bản có thể chạy an toàn trên SQL v4;
nếu rollback triển khai phải đi cùng phiên bản backend/database tương thích do dev
chọn. Không sửa ngược database hoặc xóa version/audit đã ghi để khôi phục code cũ.

## Open questions

Không còn câu hỏi nghiệp vụ Q1–Q6; chúng đã được duyệt. Các lựa chọn kỹ thuật trong
plan này, đặc biệt POST `/{id}/phien_ban` thay POST cũ, request catalog, resource ETag,
scope mutation/cache và phần audit/catalog phụ thuộc, **chờ dev duyệt plan**.

Giới hạn đã biết: 8 test nền nhân viên chưa pass; chưa xác nhận schema database
ứng dụng đang chạy; chưa tích hợp sản xuất v4/E2E và frontend. Các trường hợp đó
không được giải quyết bằng tự mở rộng phạm vi, sửa kỳ vọng test hay thao tác DB thật.
