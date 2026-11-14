# Plan: Backend Goods Receipt — UC-20 đến UC-22

**APPROVED — dev đã duyệt spec, Q1–Q5 và plan/task ngày 14/11/2026.**
**IMPLEMENTED — backend T01–T12 hoàn tất kiểm chứng ngày 15/11/2026.**
Kiểm thử dùng PostgreSQL riêng, không DB ứng dụng. Nội dung phương án/task giữ làm
cơ sở đối chiếu; kết quả thực tế ở [cuối tài liệu](#kết-quả-thực-hiện-t01t12).

## Goal

Sáu API phiếu nhập chạy đúng UC-20–22/v4: nháp không đổi tồn, hoàn tất nguyên tử
một lần với metadata/ledger/audit đầy đủ, phân quyền QLK, strong ETag và tiền integer VND;
chứng minh bằng test service/API và PostgreSQL riêng theo 22 GR-AC của spec.

## Context read

- [Spec đã duyệt](README.md), [UC-20](UC-20.md), [UC-21](UC-21.md), [UC-22](UC-22.md), Q1–Q5.
- [BR giai đoạn 1](../../business_requirements/BR-GIAIDOAN1.md) BR-001/003/004/006/015/016;
  [data model v4](../../entity_model/data_model_v4.md) §3.2/3.4/3.7/3.8;
  [entity model](../../entity_model/entity_model.md), [init.sql](../../../infra/postgres/init.sql),
  [UC-44 R8](../catalog/UC-44.md).
- `phieu_nhap/{router,schemas,service,ports,repository,models,errors}.py`,
  `inventory/{ports,repository,models,service,router}.py`, `audit` và caller/dependency;
  `mat_hang/{models,service,synchronizer}.py`, `core/{request_context,sqlalchemy_transaction,transactions}.py`.
- [Sequence phiếu nhập hiện có](../../../docs/sequence/phieu_nhap.md), test nhân viên,
  `backend/pyproject.toml`, `AGENTS.md`; skill clean-code Python/FastAPI, plan/test/concurrency.
  Không superpowers, không tự tạo `.clean/` hoặc dùng GitNexus skill điều phối.

Checkout `feature/phieu_nhap`, HEAD `f461ecd`. Trước lập plan chỉ có spec mới;
chưa có source/test phiếu xuất/BOM/Catalog mới từ các nhánh khác. Không tự merge.
Baseline đã chạy ở khảo sát: import/OpenAPI có sáu endpoint; Ruff phieu_nhap pass;
pytest hiện **8 fail** do fixture nhân viên thiếu VaiTroRead.mo_ta, không sửa ngoài phạm vi.

Bản cài đã xác minh: Python 3.13.2, FastAPI 0.144.0, Pydantic 2.14.1,
SQLAlchemy 2.1.5, asyncpg 0.32.0, pytest 9.1.1, pytest-asyncio 1.4.0.
`AsyncSession.connection(execution_options=...)`, `with_for_update`, SQLAlchemy
Core/text và `Update.returning` có trên bản cài. Query model/ASGITransport/async pytest
đã dùng trong project. Mermaid CLI tại `.venv/mermaid/node_modules/.bin/mmdc.cmd` có sẵn.
Không nâng dependency hoặc tải thư viện mới.

## Existing code to reuse

| Thành phần hiện hữu | Dùng lại / thay đổi có mục đích |
|---|---|
| phieu_nhap.router, sáu service method | Giữ method/path và tên public method; thêm actor cho service đọc, guard ở mọi service nghiệp vụ, description/docstring UC |
| PhieuNhapCreate/Patch/Read/ActionRead, GoodsReceiptNoteCreate/ReceiptItemCreate | Giữ tên DTO; tiền integer, metadata v4, strict input; tách field client/server như hiện hữu |
| SqlAlchemyPhieuNhapRepository | Giữ owner persistence, Identity, khóa phiếu/chi tiết và cấp mã; cập nhật metadata, snapshot đọc và conditional hoàn tất |
| _next_code, advisory (20261022,1) | Giữ mã tháng giờ VN, xét bảng + audit để không reuse mã xóa; không cấp ID bằng MAX |
| ReceivingRepository / ReceiptPart / ReceiptPosting | Bổ sung snapshot/method cần cho luồng mới, tiếp tục DTO detached; không trả ORM vào service |
| InventoryWriter.receive_receipt / SqlAlchemyInventoryRepository | Giữ chữ ký receive_receipt hiện tại, sửa đúng đường nhận; thêm port snapshot khóa cho service kiểm tra số dư và giới hạn |
| AuditService.append → SqlAlchemyAuditRepository.append | Giữ luồng append, cùng session/transaction; thêm trạng thái vào DTO/ORM, không refactor UC-43 |
| SqlAlchemyTransaction / get_db / require_roles / request_id | Giữ commit/rollback, auth DB và error envelope đang có; không đặt SQL ở router |
| MatHangSynchronizer và trigger mat_hang_changed | Dùng cơ chế NOTIFY sau commit/reconciliation hiện hữu, không thêm cache lock hoặc lấy cache làm chuẩn tồn |

Không có fixture BOM/phiếu xuất để import trong checkout. Không tạo receiving/goods_receipt
runtime song song hoặc khôi phục route /receiving. POST tạo lặp vẫn là các nháp riêng
như hiện tại; không tự thêm idempotency key/dedup nội dung. Chống ghi sổ trùng áp dụng
hoàn tất trên cùng một phiếu theo Q4.

## Placement

### A. File và trách nhiệm

| File | Owner / thay đổi trong phạm vi |
|---|---|
| `backend/app/modules/phieu_nhap/router.py` | Sáu endpoint; actor service đọc, local If-Match, validation body/query, UC/OpenAPI/header/status; không SQL/kiểm tra tồn |
| `phieu_nhap/schemas.py` | Tiền strict integer/BIGINT, kiểm tra cấu trúc/tổng input, DTO metadata/UTC, PATCH semantics và read constraints theo v4 |
| `phieu_nhap/models.py` | PhieuNhap/ChiTietPhieuNhap đúng init.sql: tiền BIGINT, nullable, metadata/default/version/FK/check/index, giữ Identity |
| `phieu_nhap/ports.py` | Read snapshot, mark_completed nhận actor/time/expected_version, DTO/port persistence cần thiết |
| `phieu_nhap/repository.py` | Query/khóa/Identity/code, read snapshot, metadata patch, conditional hoàn tất và đọc postings; không policy tồn/quyền hoặc commit riêng |
| `phieu_nhap/service.py` | UC-20/21/22, quyền QLK, nội dung, ETag, số dư/range, workflow/replay, điều phối inventory/audit/TX; comment nguồn UC |
| `phieu_nhap/errors.py` | Giữ mã lỗi hiện có, sửa thông báo chỉ LK; bổ sung lỗi riêng chỉ nếu mã dùng chung không đủ |
| `inventory/ports.py` | **Mới** ReceiptStock frozen dataclass và InventoryWriter.lock_receipt_stock; không đổi port xuất/điều chỉnh hiện có |
| `inventory/repository.py` | **Mới** lock_receipt_stock và sửa receive_receipt v4; giữ nguyên logic issue_stock/lock_balances/adjust_stock/list_stock/list_movements |
| `audit/models.py`, `audit/schemas.py` | Hai cột trạng thái nullable trong write/read DTO/ORM; đối chiếu CHECK/index owner với v4, field mới có default None cho caller khác |
| `backend/tests/conftest.py` — **mới** | Fixture prefix goods_receipt_ explicit, không autouse, DB test riêng/raw SQL v4/HTTP auth thật |
| `backend/tests/test_phieu_nhap_service.py` — **mới** | Unit business/role/header/tiền/điều kiện với port fake, đánh dấu UC/GR-AC |
| `backend/tests/test_phieu_nhap_api.py` — **mới** | HTTP integration, actual auth/DB role, schema/envelope/status/header/OpenAPI/route |
| `backend/tests/test_phieu_nhap_postgres.py` — **mới** | Reflection/constraint/trigger, concurrency, rollback, số dư/ledger/giữ và mã |
| `docs/sequence/phieu_nhap.md` và 6 PNG đang liên kết | Cập nhật sáu endpoint thực tế, metadata/khóa/audit/replay/tiền v4 |
| `docs/sequence/audit.md`; `docs/sequence/inventory.md` — file inventory **mới nếu cần** | Chỉ mô tả phụ thuộc receipt mới và endpoint legacy thực sự có; ghi rõ chưa nâng read/xuất/điều chỉnh inventory |
| PNG audit/inventory được liên kết — **mới/cập nhật nếu sơ đồ đổi** | Render/preview sơ đồ liên quan, không vẽ chức năng chưa triển khai |
| `docs/examples/goods-receipt-http.json` — **mới** | Request/response/header thực tế từ test, không Authorization/JWT/hash |
| `specs/use_cases/goods_receipt/{README,PLAN}.md` | Tiến độ task, kết quả thật và bảng UC/AC/test; giữ ba UC gốc |

Không dự kiến đổi `app/main.py`, model registry hoặc `app/dependencies.py`: module đã
được đăng ký, get_receiving_service đã truyền repository/audit/transaction/inventory
cùng get_db. Giữ constructor và wiring đó. Không sửa MatHang ORM/Catalog/cache,
NhaCungCap ORM/CRUD, auth, production, phieu_xuat, dieu_chinh_kho, core transaction,
SQL/seed/config/Docker manifests/migration hoặc frontend.

Q5 cho phép phụ thuộc inventory/audit tối thiểu; không phải phép đồng bộ toàn bộ
ORM legacy. Trường tồn/giữ cần đọc thêm dùng Core/text trong repository inventory,
không tạo ORM MatHang/GiuHang/GiaoDichKho trùng owner. Không thay đổi thông tin NCC
trên API receipt: vẫn ncc_id, UI đọc NCC hiện tại qua API danh mục sau này.

### B. Hợp đồng HTTP và DTO

Giữ prefix `/api/v1/phieu_nhap` và envelope `{data,meta}` / `{error,meta}`.

| Endpoint | Request / quyền | Output |
|---|---|---|
| GET collection | QLK, query Q3 | 200 list + meta page/count, không ETag list |
| GET /{id} | QLK, không query/body | 200 read + ETag, thiếu/quá dải INTEGER 404 |
| POST collection | QLK; ncc_id, ngay_nhap, ghi_chu optional/null, chi_tiet | 201 draft + Location + ETag |
| PATCH /{id} | QLK; các field patch hiện có; một If-Match | 200 read + ETag; chỉ nháp |
| DELETE /{id} | QLK; một If-Match; không query/body | 204 không body; chỉ nháp |
| POST /{id}/hoan_tat | QLK; `{}` bắt buộc; một If-Match | 200 action read + ETag + ledger IDs/replay |

- ReceiptMoney đổi sang strict int `0..2**63-1`, lượng/ID body strict positive int
  `<=2**31-1`. Không bool/float/chuỗi tiền; JSON schema mô tả integer. Tổng input
  vượt BIGINT trả 422; dữ liệu persisted không nhất quán chặn hoàn tất 409.
- Đơn giá nhập thực tế nhận từ client, tong_gia/tong_tien chỉ server tính. Giá danh
  mục không tham gia tính/không bị thay đổi. Không làm tròn/chuyển tiền Decimal cũ.
- Read thêm updated_at, hoan_thanh_at, nguoi_hoan_thanh_id, phien_ban. created_at/
  updated_at bắt buộc theo v4; ngày DATE, timestamp UTC/Z, total nullable theo DDL;
  giá/tổng chi tiết không nullable. DB v3.1 có NULL không được tự nâng/fill trong tác vụ.
- Giữ PATCH field bỏ qua/ghi_chu=null, chi_tiet thay toàn bộ không rỗng, ncc/ngày/
  chi_tiet explicit null bị 422. Giữ phép so sánh nội dung/chi tiết hiện tại cho no-op,
  không thêm policy chuẩn hóa thứ tự dòng. No-op hợp lệ giữ version/time/ETag/audit.
- GET không body; các endpoint khác không query trừ list. DELETE không nhận body.
  Unknown/repeated query, field server gửi lên và validation cấu trúc trả 422.
  Error response không echo hash/token/input nhạy cảm. Không đổi shared error handler.
- Service list_receipts/get_receipt nhận thêm actor; cả sáu service kiểm role QLK.
  Router vẫn kiểm JWT/account/role bằng dependency hiện hữu. Đây không phải nâng
  toàn auth sang phien_ban_dang_nhap v4; test pwdv hiện hữu/account/role từ DB.

### C. Strong ETag và If-Match

Giữ helper detail_response, dùng SHA-256 trên JSON canonical của đúng PhieuNhapRead,
bao gồm toàn bộ chi tiết theo ID và metadata/phien_ban; loại request_id. Tag dạng
`"<64 ký tự hex thường>"`, strong validator. Metadata/version đổi khi mutation thật,
chống A→B→A quay lại tag cũ. Không đưa thông tin NCC/cache ngoài resource vào hash.

**Mới** dependency local `get_phieu_nhap_if_match` tại router lấy đủ physical headers;
không để shared get_if_match biến header lặp thành 422. Không sửa shared dependency
để tránh thay đổi policy module khác. Service validate/so sánh dưới khóa:

- Không có hoặc một header trắng: 428.
- Nhiều header, compound tags, weak, wildcard, sai format: 412.
- Một tag đúng format nhưng không khớp: 412 cho PATCH/DELETE/hoàn tất lần đầu.
- Đã hoàn tất: quyền hiện tại + một tag đúng format vẫn bắt buộc, cho tag cũ;
  kiểm ledger đủ/đúng rồi trả cũ, replay=true. Không kiểm lại giá/tồn hiện tại để
  quyết định thành công trước đó; không thêm ledger/audit hoặc sửa metadata.
- Ledger thiếu/sai của phiếu hoàn tất: 409, không repair. Không có ngoại lệ replay
  cho sửa/xóa. Service direct call cũng tuân guard này.

### D. Luồng persistence và transaction

**Đọc:** thêm **mới** ReceivingRepository.begin_read_snapshot và adapter tương ứng.
Sau guard QLK, kết thúc transaction chỉ đọc của auth nếu có rồi dùng REPEATABLE READ
READ ONLY. COUNT/page/header/ordered lines cùng snapshot, không FOR SHARE trên GET.
Repository get_receipt/list_receipts không tự bắt đầu/rollback transaction; service
đọc mới gọi begin_read_snapshot, tránh rollback khi repo được gọi trong mutation.
Giữ load chi tiết theo batch/selectin cho cả trang, không N+1. Session close kết thúc
đọc, không commit hoặc viết lịch sử truy cập.

**Tạo:** QLK guard → supplier key-share → MatHang theo ID tăng FOR UPDATE để validate
LK → tính giá/tổng → advisory code lock → insert header/dòng → AuditService.append
tao → một commit. created_at UTC được dùng thống nhất để lấy tháng mã giờ VN,
không lấy tháng từ ngay_nhap. Repository luôn cấp mã, không cho internal DTO ghi
đè mã tùy ý. IDENTITY cấp ID, giữ `_flush` xử lý exhausted ID hiện hữu khi phù hợp.

**PATCH:** khóa phiếu rồi dòng theo ID, kiểm tag/nháp/chưa ledger; khóa NCC nếu đổi,
khóa các LK mới theo ID; tính tổng rồi thay dòng/header cần thiết. Thay đổi thật
cập nhật updated_at/phien_ban +1 và audit sua, no-op không ghi. Chỉ một TX, không
commit khi đang thay dòng; snapshot audit trước lấy từ detached DTO chưa bị sửa.

**DELETE:** khóa phiếu/dòng, tag/nháp/chưa ledger → xóa dòng/header → audit xoa_nhap
giữ full before/code/state → commit. Lỗi audit/constraint rollback cả xóa. Không
cascade ledger/audit; mã đã xóa vẫn được xét khi cấp mã mới.

**Hoàn tất lần đầu:** một SqlAlchemyTransaction/session từ dependency, thứ tự:

1. Guard QLK; khóa PhieuNhap FOR UPDATE rồi ChiTietPhieuNhap theo ID. Tìm resource/
   validate tag/current version/state và chưa có postings.
2. Validate nội dung persisted: NCC/linh kiện hợp lệ, không trùng dòng, tiền integer,
   mọi tong_gia/tong_tien đúng input đã lưu. Không tự sửa dữ liệu lỗi để hoàn tất.
3. **Mới** InventoryWriter.lock_receipt_stock(item_ids) khóa MatHang theo ID, đọc
   số dư/đang giữ/loại và SUM ledger trong repo, trả ReceiptStock detached.
   Service kiểm tra loại/số dư = ledger, nonnegative và tồn + lượng <= INTEGER_MAX.
   Không đọc tồn từ cache; không cần khóa/sửa GiuHang để thực hiện nhận hàng.
4. mark_completed nhận expected_version/actor/time; UPDATE có điều kiện id + nhap +
   phien_ban, ghi state/hoan_thanh_at/nguoi_hoan_thanh_id/updated_at/version +1.
   UPDATE 0 row trả kết quả không cập nhật qua port để service báo 412; không giấu
   bằng cách tải lại và coi như đã thành công. Không sửa lại các dòng tiền khi hoàn tất.
5. receive_receipt giữ chữ ký hiện tại, chỉ persist dữ liệu đã được service validate:
   UPDATE tăng so_luong_ton + timestamp, RETURNING tồn sau; không sửa don_gia,
   so_luong_dang_giu hay computed available. INSERT ledger nhap_linh_kien dương,
   đúng chi_tiet_phieu_nhap_id/item/qty/actor/time/so_luong_ton_sau.
   Parent hoàn tất trước INSERT để qua trigger nguồn trong cùng TX.
6. AuditService.append hoan_tat state/before/after; một commit flush audit và toàn
   bộ dữ liệu. Bất kỳ lỗi header/stock/ledger/audit/commit rollback mọi bước.

**Replay:** vẫn khóa/kiểm quyền/format; đọc postings theo line FK. Đủ mỗi dòng đúng
type/item/quantity → response cũ/current ETag, không có SQL INSERT/UPDATE/DELETE.
Không cập nhật metadata, catalog price hoặc nguồn sản xuất; incomplete posting 409.

Không lấy thêm khóa cache sau DB locks hoặc gọi mutation service mặt hàng. Code
advisory lock chỉ lúc tạo, sau khi lấy các khóa dữ liệu cần validate; không thêm
khóa tồn/nguồn khác sau code lock. Post-commit MatHang notification do trigger hiện
có, cache module khác hội tụ theo listener/reconciliation; không hứa đồng bộ tức thì.

### E. Biên inventory/audit và caller

ReceiptStock **mới**, frozen dataclass trong inventory.ports, tối thiểu có item ID,
loại/active, stock, held, ledger balance. Core/text projection ở inventory repository
đọc thêm so_luong_dang_giu đang không có trong MatHang ORM, không mở rộng Catalog.
Quyết định đủ tồn/giới hạn/balance/loại thuộc service; repository writer không tiếp
tục quyết định policy này. Không tạo InventoryReceiptService thứ hai.

InventoryWriter là port dùng chung với dieu_chinh_kho; thêm method nhận snapshot
và giữ nguyên các method cũ. Caller receive_receipt hiện chỉ PhieuNhapService (đã
search), nên không cần đổi nghiệp vụ module khác. Các method issue/adjust/read/
lock_balances và schema/model legacy không bị refactor. Khi diff review đối chiếu
AST/source của các method không thuộc receipt để tránh thay đổi ngoài Q5.

CreationAudit/AuditLogResponse thêm nullable trang_thai_truoc/sau với default None;
ORM mapping đồng bộ cột và CHECK/index với v4. PhieuNhapService append tao/sua/
xoa_nhap/hoan_tat với snapshot/state đúng; snapshot sau xóa null. AuditService và
SqlAlchemyAuditRepository.append hiện session.add đúng, giữ nguyên, không commit con.
Không đổi router/filter/quyền/endpoint audit hoặc áp toàn bộ UC-43 mới từ nhánh khác.

Không merge/khôi phục goods_issue/BOM/Catalog. Raw SQL fixture source/giữ v4 chỉ
chứng minh bất biến liên quan; không báo E2E production v4 đạt hoặc sửa production
legacy để chạy kiểm thử. Chức năng nào lệch spec mới phát hiện sẽ dừng phần phụ thuộc
và đề xuất spec sửa, tiếp tục phần độc lập, không tự chọn chính sách.

## Steps

Viết test hành vi tái hiện trước phần source tương ứng, quan sát fail → sửa → pass.
Không tạo hàng loạt test giả/đổi kỳ vọng/skip để làm xanh. Mỗi task là diff tập trung;
không commit/push trong quy trình này khi chưa được yêu cầu.

| Task | Kết quả dự kiến | Phụ thuộc | Tiêu chí hoàn thành | UC / AC |
|---|---|---|---|---|
| T01 | Fixture/test baseline thiếu, DB riêng và scenario v4 | Duyệt plan | Guard URL/UUID, bootstrap trống, không lifespan/autouse/DB ứng dụng; test tái hiện chênh lệch | Tất cả; GR-AC-01–22 |
| T02 | DTO/ORM/port phiếu theo v4 | T01 | Integer VND, nullable/default/metadata/check/index đúng SQL; input/client fields/UTC/PATCH/Identity | UC-20/22; GR-AC-02/03/08/17/19 |
| T03 | Metadata audit tối thiểu Q5 | T02 | State DTO/ORM đọc/ghi được, caller cũ default None, shared TX; không đổi audit API/quyền | UC-20/21; GR-AC-18/19 |
| T04 | Quyền service, GET snapshot, ETag/query/header local | T02 | Sáu service QLK-only, GET không ghi, Q3/count/page/UTC, header Q4, UC links trong OpenAPI | UC-22/AC-1–2; GR-AC-01/10/15–17/22 |
| T05 | Tạo nháp/cấp mã/audit | T03,T04 | Đúng LK/NCC/ngày/giá/tổng, Identity/mã tháng không trùng/reuse, 201/header, không đổi kho/giữ | UC-20/AC-1–3; GR-AC-02–04/08/18/19 |
| T06 | PATCH/DELETE nháp và metadata | T05 | Field semantics/replacement/no-op/ABA, version/audit đúng; hoàn tất không sửa/xóa; lỗi rollback | UC-20/AC-2–5; GR-AC-05/06/10/13/18 |
| T07 | Snapshot tồn và đường nhận inventory v4 | T02 | ReceiptStock/lock_receipt_stock detached; policy ở service; nhận ghi tồn sau/type mới, không sửa held/giá; đường khác giữ nguyên | UC-21; GR-AC-07–09/14/21 |
| T08 | Hoàn tất và replay Q4 trong một TX | T03,T04,T06,T07 | Guard/current tag/version, conditional metadata, ledger/stock/audit nguyên tử; replay no writes/không repair | UC-21/AC-2–5; GR-AC-07–14/17/18 |
| T09 | PostgreSQL concurrency có barrier | T05,T06,T08 | Hai complete, complete-vs-patch/delete, create mã đồng thời, hai phiếu chung item; không lost update/double ledger/audit | GR-AC-10–12/19/21 |
| T10 | Reflection/trigger/rollback và dữ liệu lệch | T08 | Mapping đúng SQL, posted immutable, incomplete ledger bị chặn, inject từng bước/commit rollback đầy đủ, giữ/source không đổi | UC-20/21; GR-AC-06/09/13/14/18–20 |
| T11 | HTTP security/contract/OpenAPI/regression/lint/type | T09,T10 | Auth DB, schema/envelope/status/header/route và 22 AC; chạy toàn suite, tách 8 lỗi baseline và type legacy nếu còn | Tất cả AC backend |
| T12 | Sequence PNG/evidence/trace và bàn giao | T11 | Sáu sơ đồ thật render/preview, evidence không secrets, từng AC có test hoặc lý do hoãn UI/E2E; báo file/check/giới hạn | UC-20–22; GR-AC-01–22 |

### Bảng truy vết kiểm chứng của phương án đã duyệt

S = **mới** test_phieu_nhap_service.py, A = **mới** test_phieu_nhap_api.py,
P = **mới** test_phieu_nhap_postgres.py. Test function đánh dấu mã UC/GR-AC trong tên.
Symbol thực tế và kết quả từng AC được cập nhật ở [spec §8](README.md#8-truy-vết-triển-khai-và-kiểm-chứng).
Bảng dưới giữ mô tả hành vi cần kiểm chứng của phương án, không thay cho log chạy test.

| UC / AC | Endpoint → service | Test / kết quả quan sát cần có |
|---|---|---|
| UC-20 AC-1; GR-AC-04 | POST → create_receipt | A/P: stock10, tạo nháp50 giữ stock10, không ledger/giữ; code/actor/tổng/audit đúng |
| UC-20 AC-2/3; GR-AC-02/03/08 | POST/PATCH → create_receipt/patch_receipt | S/A: only LK, duplicate, strict type/range/overflow, giá nhập khác catalog, giá catalog không đổi |
| UC-20 AC-4/5; GR-AC-05/06/10/18 | PATCH/DELETE → patch_receipt/delete_receipt | S/A/P: posted immutable, stale/ABA, field omission/null, no-op, audit before/sau xóa null; mã không reuse |
| UC-21 AC-2/3; GR-AC-07/11/12 | POST hoan_tat → complete_receipt | A/P: stock10+50=60, ledger +50/stockafter60, metadata, replay IDs cũ, một lần ghi thực sự |
| UC-21 AC-4; GR-AC-09 | POST hoan_tat → complete_receipt | P: source chờ/nhu cầu/giữ từ fixture v4 nguyên trạng; E2E API sản xuất legacy hoãn Q5 |
| UC-21 AC-5; GR-AC-10 | Mutations → service guard + expected_version | S/A/P: A→B→A tag cũ412; hai session không ghi dựa phiên bản đã đổi |
| UC-21 AC-1 | Đóng hộp thoại → không service call | UI chưa nghiệm thu; backend chỉ chứng minh đọc/lưu nháp không ghi kho, action mới ghi |
| UC-22 AC-1/2; GR-AC-01/15–17 | GET list/detail → list_receipts/get_receipt | A/P: QLK-only, DB role/account/pwdv, hai trạng thái, AND filters/count/page/date VN/literal %, _, SQL spy no writes |
| GR-AC-13/14/18 | Complete/TX/audit | P: mismatch stock/ledger409 không repair, tồn INTEGER max/overflow, lỗi header/stock/giữ nguyên/ledger/audit/commit rollback |
| GR-AC-19/21 | Persistence và locks | P: reflection/Identity/unique/FK/check/trigger, code concurrent/exhaustion, hai receipt chung item và giữ nguồn khác không đổi |
| GR-AC-20 | ncc_id → lookup NCC hiện tại | P: không snapshot NCC vào receipt; đổi NCC từ fixture thì ID liên kết giữ; UI UC-44 R8 chưa nghiệm thu |
| GR-AC-22 | Router/contract | A: sáu routes, không /receiving/duyệt/điều chỉnh/ticket, required empty action body, unknown/repeated query/body/IDs |

## Risk level and verification

**HIGH**: thay hợp đồng tiền, ORM persisted metadata, quyền service, transaction kho/
ledger/audit và concurrency. Không thay schema/seed hoặc dữ liệu database ứng dụng.

### Môi trường test và dữ liệu

- Fixture **mới** goods_receipt_database chỉ nhận `GOODS_RECEIPT_TEST_DATABASE_URL`:
  driver postgresql+asyncpg, localhost/127.0.0.1, user **goods_receipt_test**, port
  **55466**, database khởi điểm **xbike_goods_receipt_test**. Không fallback app URL.
- PostgreSQL test container riêng, tmpfs, không mount volume ứng dụng. Kiểm cổng,
  ghi ID/label container; sau test xác minh đúng ID/nhãn/mount trước cleanup.
- Mỗi fixture tạo `goods_receipt_<uuid>_test`, kiểm database trống rồi chạy nguyên
  init.sql thực. Không seed app, không metadata.create_all/SQLite thay cho kiểm chứng
  PostgreSQL. Finally chỉ drop đúng UUID DB đã tạo và đóng engine/session.
- Thiếu URL thì integration test skip rõ lý do; khi nghiệm thu phải chạy với URL
  test riêng để không có skip bị hiểu thành pass. Không chạy app lifespan/traffic
  recorder/cache listener chạm DB ứng dụng; AsyncClient/ASGITransport override get_db.
- Scenario raw SQL tạo vai trò/nhân viên QLK/NV/QTV/khóa; NCC và LK/TP, Bom/yêu cầu/
  nhu cầu/giữ khi AC cần. Tồn ban đầu có nguồn receipt hoàn tất và ledger hợp lệ,
  metadata đầy đủ, insert dòng trước khi parent hoàn tất để qua trigger.
  Không đặt stock giả rồi coi như ledger đúng; corruption test phải ghi rõ chủ đích.
- Tokens dùng helper security hiện có, pwdv theo hash fixture. Không lưu JWT/hash
  trong evidence/log bàn giao. Claims role cũ/giả không thay role hiện tại từ DB.

### Kiểm chứng cần chạy

- Unit service: quyền mọi method (kể cả gọi trực tiếp), content/state/price/range,
  ETag/metadata/format/missing/replay, no-op và điều phối audit qua service.
- API: request/response integer/UTC/meta/request_id, POST201 Location/ETag, DELETE204,
  action200/ledger IDs, 401/403/404/409/412/422/428, physical header lặp, query lặp/
  unknown, raw GET/DELETE body, path quá INTEGER không tạo asyncpg overflow, OpenAPI.
- Repository/PG: count/page/ordered lines/read snapshot, mapping/types/null/default/
  Identity/FK/unique/check/index, SQL trigger source/immutable, code tháng VN/cấp đồng
  thời/exhaustion/history nonreuse, totals/stockafter/held/computed available.
- Dùng ít nhất hai session/connection độc lập, barrier/event + timeout; không dùng
  sleep để hy vọng cạnh tranh. Chứng minh hai complete cùng phiếu, complete-vs-patch/
  delete, hai receipt khác nhau chung item, code generation giữa hai create.
- Replay có SQL spy không INSERT/UPDATE/DELETE, kể cả old tag đúng format; missing/
  blank/weak/wildcard/repeated/compound tag không vượt guard. Incomplete posting
  simulated bằng SQL v4 hợp lệ bị409 và giữ nguyên, không repair bằng test fixture.
- Failure injection sau đổi metadata, sau stock, giữa các INSERT ledger, khi append/
  flush audit và lúc commit; so snapshot PhieuNhap/ChiTiet/MatHang/GiaoDichKho/
  LichSuThaoTac/GiuHang/YeuCauSanXuat trước-sau. Không suy ra crash/kết nối rớt thật
  chỉ từ mock commit raise. Không sửa expectations để bỏ bất biến bị lỗi.
- Full suite và kiểm tra scope/diff sau scoped pass; tách baseline8 test nhân viên,
  type errors legacy nếu gặp, không tự sửa ngoài phạm vi để làm xanh toàn backend.
- Mermaid render/preview, link/file/UTF-8 và UC/AC completeness; source/spec/test/
  sequence nhất quán. Các AC UI/E2E hoãn trong spec vẫn ghi chưa nghiệm thu.

### Lệnh kiểm chứng — đối chiếu kết quả thực tế bên dưới

```powershell
# Tại backend, sau khi cấu hình URL test riêng đúng guard fixture.
..\.venv\Scripts\python.exe -m pytest tests/test_phieu_nhap_service.py tests/test_phieu_nhap_api.py tests/test_phieu_nhap_postgres.py -q
..\.venv\Scripts\python.exe -m pytest tests -q --tb=line
..\.venv\Scripts\mypy.exe app/modules/phieu_nhap app/modules/inventory/ports.py app/modules/inventory/repository.py app/modules/audit/models.py app/modules/audit/schemas.py --follow-imports=silent --ignore-missing-imports
# Tại root, chỉ kiểm tra source/test thực sự được sửa.
.\.venv\Scripts\ruff.exe check <cac-file-da-sua>
.\.venv\Scripts\ruff.exe format --check <cac-file-da-sua>
.\.venv\Scripts\python.exe .agents/skills/clean-code/scripts/map_structure.py --path backend/app/modules/phieu_nhap
.\.venv\Scripts\python.exe .agents/skills/clean-code/scripts/check_boundaries.py
.\.venv\mermaid\node_modules\.bin\mmdc.cmd -i docs/sequence/phieu_nhap.md -o .venv/goods-receipt-sequence.png -e png -b white --size 3000 -s 1.5 -j 2
git diff --check
```

Mypy follow-imports silent không phải strict toàn backend. Boundary checker hiện
chưa có architecture declaration; nếu vẫn thiếu sẽ báo giới hạn và đối chiếu import
thủ công, không tạo config giả. CLI Chromium/Docker có thể cần quyền công cụ; dùng
cơ chế quyền môi trường, không tự thay bằng DB ứng dụng hoặc bịa kết quả pass.

### Rollback và giới hạn

Chưa có migration up/down. Backend mới cần schema v4 tương thích; bản v3.1 không
tự chạy đúng với DB v4. Rollback triển khai phải do dev chọn code/schema phù hợp;
không tự git reset/revert, xóa DB/volume hoặc hoàn tác ledger/chứng từ đã ghi sổ.
init.sql sửa/không sửa không tự cập nhật database đang chạy; không chạy seed/reset.

Không frontend, API sản xuất E2E hoặc bảo đảm cache module khác đồng bộ tức thì.
Không refactor auth/UC-43 toàn phần, đồng bộ MatHang owner/Catalog hoặc inventory
legacy ngoài đường nhận. Source/test được viết sau khi dev duyệt plan/task và truy
vết spec/AC. Không commit/push nếu chưa được yêu cầu rõ ràng.

## Open questions

Không còn câu hỏi nghiệp vụ Q1–Q5; spec và các lựa chọn kỹ thuật ở plan/task này
đã được dev duyệt trước khi triển khai (DTO/port snapshot, đọc read-only,
khóa/conditional update, header local, fixture và chia task).
Nếu cần thay đổi spec hoặc vượt Q5 sẽ dừng phần phụ thuộc, đề xuất và chờ xác nhận.

## Kết quả thực hiện T01–T12

### Tiến độ và file thực tế

| Task | Trạng thái / kết quả |
|---|---|
| T01 | Đạt: thêm conftest explicit goods_receipt_ và ba file test; DB UUID mới/trống từ init.sql, không seed/autouse/lifespan hoặc dùng DB ứng dụng. Bộ test đầu tiên quan sát 12 fail/4 pass trước sửa source. |
| T02 | Đạt: phieu_nhap schemas/models/ports đồng bộ integer VND, Identity, metadata, version, CHECK/FK/index của SQL v4; reflection PostgreSQL pass. |
| T03 | Đạt: audit models/schemas thêm state nullable/default None; AuditService/Repository và quyền/filter audit giữ nguyên. |
| T04 | Đạt: router/service/repository kiểm QLK ở cả HTTP và service, header local, strong tag, GET snapshot REPEATABLE READ READ ONLY; test chèn giữa COUNT và đọc trang pass. |
| T05 | Đạt: tạo nháp đúng tổng/actor/mã server, không đổi kho; code tháng VN, cấp đồng thời, lịch sử mã đã xóa và hết dải có test. |
| T06 | Đạt: sửa/xóa nháp, metadata/version/audit, no-op không ghi, ABA/stale bị 412; không sửa/xóa hoàn tất. |
| T07 | Đạt: inventory ReceiptStock/lock_receipt_stock/receive_receipt nâng đúng đường nhận v4. Đối chiếu AST với HEAD xác nhận issue_stock, lock_balances, adjust_stock, list_stock, list_movements không đổi. |
| T08 | Đạt: hoàn tất conditional expected_version, phiếu/tồn/ledger/audit một transaction; replay cho tag cũ đúng format và không DML, không tự repair ledger thiếu. |
| T09 | Đạt: test hai session hoàn tất cùng phiếu, cạnh tranh PATCH/DELETE, mã tạo đồng thời, hai phiếu chung mặt hàng có barrier/event. |
| T10 | Đạt: reflection/trigger immutable, stock lệch/overflow, dữ liệu tổng sai, rollback tại năm bước hoàn tất và lỗi audit của tạo/sửa/xóa; giữ/nguồn sản xuất không đổi. |
| T11 | Đạt phạm vi receipt: 80 test pass; Ruff check/format và mypy 11 file source pass. Full suite còn 8 lỗi fixture nhân viên từ baseline; mypy kèm inventory repository còn 4 lỗi legacy ngoài đường nhận. |
| T12 | Đạt: spec/plan/22 GR-AC liên kết test, sequence sáu endpoint + audit/inventory, render PNG và preview, evidence HTTP thực tế không JWT/hash. UI/production E2E vẫn hoãn. |

File runtime đã sửa: `phieu_nhap/{router,service,repository,ports,schemas,models,errors}.py`,
`inventory/{ports,repository}.py`, `audit/{models,schemas}.py`. Các file test và tài liệu
đúng bảng Placement phía trên; không thay app/main/dependencies/core, auth, MatHang,
Catalog, sản xuất, phiếu xuất, SQL/seed/migration/config hoặc frontend.

### Kết quả đã chạy

| Kiểm tra | Kết quả thực tế |
|---|---|
| `pytest tests -q --tb=line --junitxml=../.venv/goods-receipt-result.xml` | **80 pass, 8 fail, 0 skip**, 18.24s; receipt service 31, API 22, PostgreSQL 27 pass |
| 8 fail baseline | Đều ở `test_nhan_vien_create_code.py:86`: fixture tạo VaiTroRead thiếu `mo_ta`, đã tái hiện từ trước triển khai; không sửa test/module nhân viên |
| Ruff check source/test thay đổi | Pass |
| Ruff format --check source/test thay đổi | Pass: 16 file đã đúng format |
| Mypy receipt + inventory/ports + audit/models,schemas (`--follow-imports=silent --ignore-missing-imports`) | Pass: **11 file source**; không phải strict toàn backend |
| Mypy thêm inventory/repository.py | 4 lỗi legacy ở issue_stock/lock_balances/adjust_stock: thiếu annotation balances/ledger (dòng 44/93) và stock có thể None (130/131); các method này đối chiếu AST không đổi, không sửa ngoài Q5 |
| Mermaid CLI | Render được **10 PNG**: receipt 6, inventory 3, audit 1; xem [sequence receipt](../../../docs/sequence/phieu_nhap.md), [inventory](../../../docs/sequence/inventory.md), [audit](../../../docs/sequence/audit.md) |
| Kiến trúc | Đối chiếu import/layer trực tiếp; không có `.clean/architecture.md` nên boundary checker không thể kết luận tự động |
| Structure map | Không có cycle/misplaced/mixed/unreferenced trong phạm vi; hai nhóm duplicate do constructor cùng mẫu và begin_read_snapshot giống adapter phiếu xuất, giữ riêng owner, không mở refactor module khác |
| Tài liệu/evidence/diff | 52 liên kết file nội bộ hợp lệ, UTF-8 đúng, đủ 22 hàng AC/12 task/12 kết quả; 10 PNG qua CRC/decompression và preview; HTTP JSON parse và kiểm không JWT/Authorization/hash; git diff --check pass |
| Cleanup PostgreSQL test | Không còn DB goods_receipt_UUID_test sau fixture; xác minh đúng ID/label/cổng 55466/tmpfs rồi dừng container 8522b8c0afb9. Container ứng dụng 484c7efeb50c vẫn chạy cổng 5432, không sửa dữ liệu/volume |

Không chạy lại full suite chỉ vì thay tài liệu/PNG. Log JUnit nằm trong `.venv/`
(không đưa vào Git); số test tính theo từng case tham số hóa, không theo số hàm test.
[Bảng truy vết](README.md#8-truy-vết-triển-khai-và-kiểm-chứng) ghi symbol test cho 22 GR-AC.
[Evidence HTTP](../../../docs/examples/goods-receipt-http.json) được tạo bằng HTTP test thật,
chỉ ghi payload/status/ETag/Location an toàn, không ghi Authorization/JWT/hash.

### Giới hạn bàn giao

- Tiền đổi chuỗi Decimal → JSON integer VND; response thêm metadata v4. Frontend
  chưa cập nhật; payload cũ cần điều chỉnh. Không coi init.sql là migration DB đang chạy.
- Backend yêu cầu schema v4. Không thay dữ liệu/seed/volume DB ứng dụng và không
  tự tạo/chạy migration. Test dùng container PostgreSQL 16 riêng, cổng 55466/tmpfs;
  fixture drop đúng DB UUID đã tạo, container test được dừng sau kiểm chứng.
- UC-21 AC-1 (dialog xác nhận), UC-44 R8 (UI NCC), E2E sản xuất/kiểm tra giữ hàng
  qua API legacy chưa nghiệm thu. Không mô phỏng mất kết nối/crash PostgreSQL thực;
  rollback commit được kiểm bằng failure injection.
- Auth vẫn dùng pwdv hiện có; chưa nâng toàn login version v4. Không tuyên bố read/
  issue/adjust inventory legacy hoặc toàn API audit đã đồng bộ v4. Không kiểm thử
  cache UI cập nhật tức thì; stock đọc/ghi trong transaction lấy trực tiếp PostgreSQL.
- Không commit/push hoặc merge nhánh khác.
