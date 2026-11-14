# Plan: Backend Goods Issue — UC-34 đến UC-40

**APPROVED — spec, Q1–Q6 và plan/task đã được dev duyệt ngày 14/11/2026.**
Đã triển khai backend và kiểm thử trên PostgreSQL riêng; không thay đổi database ứng dụng.
Kết quả T01–T12 và giới hạn kiểm chứng được ghi ở cuối file, không phải toàn hệ thống đạt E2E.

## Goal

Phiếu xuất v4 lấy đúng đủ lượng đã chốt của yêu cầu, phân quyền NV/QLK đúng spec;
duyệt chốt giá, trừ tồn, kết thúc giữ, ghi ledger/audit và đóng yêu cầu TP nguyên tử,
chống ghi trùng; chứng minh bằng test service/API và PostgreSQL độc lập.

## Context read

- [Spec được duyệt](README.md), [UC-34](UC-34.md)–[UC-40](UC-40.md), Q1–Q6.
- [BR giai đoạn 1](../../business_requirements/BR-GIAIDOAN1.md),
  [data model v4](../../entity_model/data_model_v4.md),
  [entity model](../../entity_model/entity_model.md), [init.sql](../../../infra/postgres/init.sql).
- [UC-12](../catalog/UC-12.md), [UC-28](../production/UC-28.md), [UC-43](../audit/UC-43.md).
- Source `phieu_xuat`, `inventory`, `mat_hang`, `audit`, model/port/caller `san_xuat`,
  `app/dependencies.py`, `app/models.py`, core auth/request context/transaction.
- `docs/sequence/phieu_xuat.md`, source test nhân viên và `backend/pyproject.toml`.
- `AGENTS.md`; skill clean-code: Python/FastAPI, plan, test, concurrency và review.
  Không dùng superpowers/GitNexus skill để điều phối, không tạo `.clean/` giả.

Mốc khảo sát: `feature/phieu_xuat`, HEAD `f461ecd`. Trong checkout chỉ có test nhân
viên, chưa có test/BOM/Catalog mới từ các nhánh khác; không tự merge/cherry-pick.
Baseline đã chạy: import/OpenAPI có 9 endpoint phiếu xuất; Ruff module pass;
pytest hiện **8 fail** ở fixture nhân viên thiếu VaiTroRead.mo_ta, không sửa lỗi này.

Đã kiểm tra API thư viện cài tại máy: FastAPI 0.144.0, Pydantic 2.14.1,
SQLAlchemy 2.1.5, asyncpg 0.32.0, pytest 9.1.1, pytest-asyncio 1.4.0.
Query model Pydantic đã dùng trong router; SQLAlchemy Core table/column/text,
with_for_update, execution_options và AsyncSession.connection có sẵn. Không nâng
dependency hoặc tải thư viện mới để thực hiện plan.

## Existing code to reuse

| Thành phần | Cách sử dụng / thay đổi có mục đích |
|---|---|
| PhieuXuatService, PhieuXuatRepository, SqlAlchemyPhieuXuatRepository | Chủ sở hữu nghiệp vụ và persistence phiếu; sửa tại module hiện hữu, không tạo module goods_issue thứ hai |
| PhieuXuat / ChiTietPhieuXuat | Đồng bộ đúng hai bảng PascalCase trong init.sql; bỏ nguồn lệnh, bổ sung metadata/phien_ban/index/check v4 |
| create_issue/list_issues/get_issue/approve/response | Giữ tên, thay payload/guard/nguồn/ETag và luồng theo spec |
| transition, patch_issue, delete_issue công khai | Thay transition bằng hai thao tác có quyền rõ ràng: **mới** submit_issue/reject_issue; bỏ đường sửa/xóa công khai/về nháp theo Q2, dọn symbol không còn caller |
| _next_code và advisory key (20261022, 3) | Giữ mã PX theo tháng VN, xét cả row/audit lịch sử; dùng IDENTITY, không cấp ID bằng MAX |
| InventoryIssueWriter / SqlAlchemyInventoryRepository.issue_stock | Mở rộng đúng đường xuất với snapshot giữ/tồn/ledger; không viết cơ chế tồn thứ hai hoặc đổi đường nhập/điều chỉnh legacy |
| AuditService.append / SqlAlchemyAuditRepository.append / CreationAudit | Giữ luồng ghi qua audit service và cùng transaction; bổ sung trạng thái trước/sau và gui_lai |
| SqlAlchemyTransaction / get_db / require_roles | Cùng AsyncSession, một commit/rollback, auth từ DB; thêm guard service để gọi trực tiếp không vượt quyền |
| Các method tong_da_xuat_thanh_pham/co_phieu_da_ghi_so/huy_phieu_chua_ghi_so | Giữ chữ ký port cho caller sản xuất, chuyển truy vấn của phiếu sang nguồn yêu cầu v4; không gọi bảng LenhSanXuat |
| MatHangSynchronizer + trigger mat_hang_changed | Giữ LISTEN/NOTIFY/reconciliation hiện có, không dùng cache để quyết định giá/tồn khi xuất |

Không có fixture/test BOM để import trong nhánh này. Fixture phiếu xuất mới đặt tại
home test chung, không tự khôi phục test/source trên nhánh khác.

## Placement

### A. File dự kiến thay đổi và owner

| File | Vai trò / phạm vi |
|---|---|
| `backend/app/modules/phieu_xuat/router.py` | Còn 6 endpoint; role, schema/dependency, strong header, UC links/OpenAPI; không quy tắc lượng/tồn hoặc SQL |
| `phieu_xuat/schemas.py` | Input chỉ loại + ID yêu cầu, không chi tiết/giá; metadata read/action/query v4; bỏ Patch DTO không còn dùng |
| `phieu_xuat/service.py` | Quyền, nguồn/snapshot, chuyển trạng thái, kiểm tra giữ/tồn, giá/retry, điều phối repository/inventory/audit; docstring UC |
| `phieu_xuat/ports.py` | Mở rộng IssueSource/IssuePart và các port theo snapshot v4, bỏ operation sửa dòng/nguồn lệnh không còn caller |
| `phieu_xuat/repository.py` | ORM phiếu; SQL Core projection nguồn v4, khóa, đọc snapshot, cấp mã, metadata và cập nhật yêu cầu khi xuất TP; không commit/HTTP |
| `phieu_xuat/models.py` | Chỉ PhieuXuat/ChiTietPhieuXuat đúng init.sql, không map ORM trùng bảng sản xuất |
| `phieu_xuat/errors.py` | Tái sử dụng lỗi nghiệp vụ; chỉ thêm lỗi cụ thể khi exception hiện có chưa đủ, dọn lỗi orphan trong module nếu không còn caller |
| `backend/app/modules/inventory/ports.py` | **Mới** detached snapshot tồn/giữ: IssueStockContext/IssueReservation; **mới** lock_issue_stock, mở rộng tham số issue_stock cần thiết; giữ port khác |
| `inventory/repository.py` | Chỉ đường xuất: projection/khóa MatHang/GiuHang/ledger, ghi hai số dư đồng thời, kết thúc giữ, INSERT ledger đúng v4; giữ read/receipt/adjustment legacy ngoài scope |
| `backend/app/modules/audit/{models,schemas}.py` | Metadata trạng thái và gui_lai; mapping check/index theo SQL trong phần owner audit, read DTO nhận event mới; không triển khai lại UC-43 hay đổi quyền/route audit |
| `backend/app/dependencies.py` | Giữ/điều chỉnh wiring cùng session cho service và writer nếu chữ ký thay; không transaction con |
| **Mới** `backend/tests/conftest.py` | Fixture goods_issue_database/client/auth/scenario có tên riêng, không autouse; bootstrap DB test trống/guard URL/cleanup; không thay fixture nhân viên |
| **Mới** `backend/tests/test_phieu_xuat_service.py` | Test quyền/quy tắc/metadata/retry theo UC/GI-AC, fake port cho phần không cần HTTP/SQL |
| **Mới** `backend/tests/test_phieu_xuat_api.py` | Actual app/auth qua DI test, schema/status/header/role/routes gỡ/OpenAPI |
| **Mới** `backend/tests/test_phieu_xuat_postgres.py` | Reflection, snapshot lượng, nguồn/giữ/tồn/ledger/audit, barrier concurrency, failure injection và trigger trên init.sql thực |
| `docs/sequence/phieu_xuat.md` + PNG hiện có liên quan | Chỉ endpoint thực tế sau sửa; bỏ mục/asset route gỡ trong phạm vi docs nếu không còn tham chiếu; không để hình v3 mang nghĩa v4 |
| `docs/sequence/inventory.md`, `audit.md` và PNG liên quan nếu lời gọi/projection thực tế thay đổi | Chỉ điều chỉnh phần bị ảnh hưởng trực tiếp, không mô tả GET kho legacy như đã chạy v4 |
| **Mới** `docs/examples/goods-issue-http.json` | Request/response chạy thật, bỏ JWT/secret, phân biệt lần duyệt đầu và replay |
| `specs/use_cases/goods_issue/{README,PLAN}.md` | Task/result/trace thực tế; UC gốc được giữ, có thể thêm ghi chú backend/approval liên kết rõ ràng nếu cần |

Không dự kiến sửa `main.py`/`app/models.py`: module/model/route đã đăng ký, không thêm
owner ORM hoặc module mới. Không sửa SQL/seed, migration, frontend, dependency,
config, các service sản xuất hoặc CRUD mặt hàng/nhà cung cấp. Mọi file mới khác
ngoài danh sách phải có lý do và được review trước khi mở rộng.

### B. Hợp đồng API đích để duyệt

Giữ prefix `/api/v1/phieu_xuat`; envelope `{data, meta}` / `{error, meta}` hiện có,
request_id trong mọi response theo handler. QTV bị chặn; role/account kiểm tra từ DB.

| UC | Endpoint | Actor / input | Thành công |
|---|---|---|---|
| UC-40 | GET `/api/v1/phieu_xuat` | QLK; PhieuXuatQuery đã bỏ nguồn lệnh | 200 data + meta page/page_size/total/total_pages/request_id |
| UC-34/36/37/39/40 | GET `/api/v1/phieu_xuat/{id}` | QLK hoặc NV được giao yêu cầu hiện tại | 200 PhieuXuatResponse + ETag |
| UC-34/37 | POST `/api/v1/phieu_xuat` | NV được giao; `{loai_phieu, yeu_cau_san_xuat_id}` | 201 nháp + Location + ETag |
| UC-34/37 | POST `/api/v1/phieu_xuat/{id}/gui` | NV được giao, body `{}`, If-Match | 200 resource + ETag; nhap gửi lần đầu hoặc tu_choi gửi lại cùng ID |
| UC-35/38 | POST `/api/v1/phieu_xuat/{id}/duyet` | QLK, body `{}`, If-Match | 200 PhieuXuatActionResponse + ETag; ledger IDs và da_ghi_so_truoc_do |
| UC-36/39 | POST `/api/v1/phieu_xuat/{id}/tu_choi` | QLK, `{ly_do: string không trắng}`, If-Match | 200 resource + ETag |

- Gỡ PATCH và DELETE `/{id}`: method không còn trong OpenAPI; vì URL GET vẫn có,
  gọi hai method cũ trả **405**. Gỡ POST `/{id}/ve_nhap`: trả **404**. Không thêm alias
  hoặc route gui_lai; dùng chính `/gui` theo trạng thái nguồn, ghi đúng audit gui_lai.
- PhieuXuatCreate extra forbid, chỉ hai loại xuat_linh_kien/xuat_thanh_pham và một
  ID yêu cầu nguyên dương trong dải INT. Mã v3 xuat_vat_tu, lenh_san_xuat_id,
  chi_tiet, người lập/xử lý, mã phiếu, giá/tổng/trạng thái client gửi đều bị **422**.
- EmptyInput `{}` bắt buộc cho gửi/duyệt; không nhận query ở detail/write; GET
  và endpoint không có body không nhận body lạ. Query lạ/lặp, sort/khoảng ngày sai 422.
- Read giữ id/ma_phieu_xuat/nhan_vien_id/loai_phieu/yeu_cau_san_xuat_id/tong_tien/
  trang_thai/created_at/chi_tiet; **bỏ lenh_san_xuat_id**, thêm updated_at/gui_at/
  nguoi_xu_ly_id/xu_ly_at/ly_do_tu_choi/phien_ban. Chi tiết giữ id/item/quantity/giá/tổng.
- Tiền JSON integer VND, dải BIGINT; giá/tổng NULL trước duyệt, đầy đủ sau duyệt.
  Không tự biến dữ liệu NULL/inconsistent thành 0 để trả thành công.
- Timestamps aware UTC `Z`; ngày query vẫn là YYYY-MM-DD theo giờ Việt Nam.
- Danh sách theo Q3: q literal mã phiếu, trim ngoài/blank thành không lọc; AND các
  filter, page 1/20/max100, default -created_at, ID ASC phụ cho ties; không lọc theo lệnh.
- Không tồn tại/ID vượt INT trả 404 trước khi gửi giá trị tràn vào asyncpg; sai
  cấu trúc 422, thiếu/sai quyền 401/403, xung đột nguồn/trạng thái/dữ liệu 409.
  NV ngoài nguồn được giao trả 403, không trả dữ liệu phiếu đó.

Đây là breaking change đối với API v3; frontend và client cũ phải cập nhật sau.
Plan không thêm chức năng giao hàng/bán hàng/xuất từng phần hoặc sửa chứng từ.

### C. Source projection và quyền sở hữu dữ liệu

- PhieuXuat/ChiTietPhieuXuat tiếp tục sở hữu tại `phieu_xuat/models.py`; ORM class
  trùng chính xác tên bảng, Identity/FK/index/check/null/default/metadata theo init.sql.
- Không import `san_xuat.models.LenhSanXuat/ChiTietLenhSanXuat` để xác định nguồn v4.
  Không tạo lớp YeuCauSanXuat hoặc ChungTuHoanThanhSx thứ hai trong module phiếu.
- Repo phiếu dùng SQL Core/text có parameter và tên PascalCase để lấy projection
  YeuCauSanXuat, NhuCauLinhKien, ChungTuHoanThanhSx. Kết quả detached qua IssueSource:
  ID/type/status/assignee/output/quantity, lượng đã chốt, metadata cần kiểm tra/audit.
- Nguồn LK lấy nguyên NhuCauLinhKien, kiểm tra set/quantity đúng toàn bộ và item là LK;
  TP lấy đúng một item/so_luong yêu cầu dap_ung và trạng thái hoàn thành tương ứng.
- Phần giữ/tồn/ledger dùng projection trong inventory repository, trả qua port mới;
  không map ORM GiuHang/GiaoDichKho trùng owner. MatHang có thể đọc/ghi cột cần thiết
  bằng projection Core nên **không cần refactor MatHang ORM/CRUD/cache/DTO** trong plan này.
- Giữ MatHangCache/Synchronizer hiện có: writer quyết định bằng DB dưới khóa;
  trigger thông báo sau commit và reconciliation giữ nguyên. Không hứa GET cache
  của module khác cập nhật tức thì; không dùng cache trễ để chấp nhận xuất/chốt giá.
- Audit owner cập nhật trạng thái trước/sau và gui_lai trong CreationAudit,
  LichSuThaoTac và read DTO/enum. Tham chiếu index/check đối chiếu init.sql, không
  đổi schema thật. Bổ sung field audit nullable là thay đổi response additive cần ghi rõ.
- Các API `/inventory/stock`, movement/reporting và sản xuất legacy còn có mapping
  cũ chưa chuyển; không dùng bản sửa phiếu để tuyên bố toàn inventory/sản xuất chạy v4.

### D. Service/use case và metadata

- create_issue: UC-34/37. Guard NV → transaction → khóa nguồn → kiểm tra được giao,
  loại/status/chốt lượng/giữ → check chưa có cùng loại → cấp mã/Identity → tạo nháp
  với dòng hệ thống sinh → audit tao. Không nhận giá/chi tiết từ client, không xuất kho.
- **Mới** submit_issue: UC-34/37. Guard NV và nguồn được giao → khóa/If-Match →
  nhap hoặc tu_choi → cho_duyet; gui_at/updated_at = thời điểm gửi hiện tại, tăng
  phien_ban. Gửi lại xóa metadata xử lý cũ trên row (nguoi_xu_ly_id/xu_ly_at/
  ly_do_tu_choi = NULL); snapshot audit trước giữ nguyên lý do cũ. Audit gui/gui_lai.
- **Mới** reject_issue: UC-36/39. Guard QLK → khóa/If-Match → chỉ cho_duyet → tu_choi,
  lưu lý do nonblank và actor/time từ server, tăng phien_ban/updated_at; audit tu_choi.
  Không đổi dòng/giá/tồn/giữ/ledger hoặc đóng yêu cầu.
- approve: UC-35/38. Guard QLK → khóa/validate header → replay hoặc xử lý lần đầu
  theo phần E/F. Không tự started_at cho sản xuất, không đổi nhu cầu/BOM đã chốt.
- get_issue/list_issues: UC-34/36/37/39/40 đọc theo đúng role/scope. Giữ snapshot
  REPEATABLE READ read-only của request GET hiện có để COUNT/data/body/tag nhất quán;
  không gọi thao tác mở snapshot GET bên trong transaction ghi/caller sản xuất.
- Q6: với source đã gửi hợp lệ theo v4, không chặn chỉ vì TP hiện inactive. Vẫn
  kiểm tra trạng thái/loại/nhu cầu/giữ; không sửa việc tạo/gửi yêu cầu mới của sản xuất.
- Dọn PhieuXuatPatch, patch_issue/delete_issue công khai, transition cũ và operation
  sửa dòng/approved_quantities nếu không còn caller sau chuyển sang xuất toàn lượng.
  Giữ delete_draft nội bộ và aggregate/public port cho sản xuất; đối chiếu rg trước xóa.

### E. Transaction, khóa và ghi sổ

Một AsyncSession/caller-owned SqlAlchemyTransaction, một commit/rollback. Mỗi action
chọn một `now` UTC dùng chung cho metadata, holds/ledger/audit liên quan; không commit
trong repository/inventory/audit. Router không điều phối các bước ghi rời nhau.

Thứ tự dự kiến cho thao tác ghi liên quan:

```text
YeuCauSanXuat FOR UPDATE
→ PhieuXuat/chi tiết hiện hữu theo ID (nếu có)
→ projection chứng từ hoàn thành cần kiểm tra (TP)
→ MatHang theo ID tăng
→ GiuHang theo item/ID tăng
→ ghi phiếu/giá/số dư/giữ/ledger/yêu cầu/audit
→ COMMIT một lần
```

- Request lock chung cho hai loại phiếu và port hủy giúp serialize nguồn/trạng thái.
  Không khóa phiếu trước rồi đợi request ở đường khác. Nhu cầu chốt/chi tiết đã duyệt
  bất biến, không cần lock graph BOM hoặc tính lại công thức. Không lấy cache lock sau DB lock.
- Cấp mã giữ advisory key hiện có sau khi đã lấy các khóa dữ liệu cần thiết; sau
  khi giữ khóa mã không đi lấy thêm khóa stock/source mới gây đảo thứ tự. Code xét
  cả row/audit, dải tháng từ 000001–999999, hết dải 409; không tái dùng mã của nháp đã xóa.
- InventoryIssueWriter **mới** lock_issue_stock(request_id, item_ids) trả snapshot
  stock/held/ledger/giữ theo nguồn (IssueStockContext/IssueReservation). PhieuXuatService
  kiểm tra điều kiện nghiệp vụ: đúng lượng/set, giữ đúng nguồn/loại, tổng held khớp,
  tồn khớp ledger, không thiếu hàng/chiếm phần của nguồn khác, giá/int/overflow.
- Repo chỉ thao tác dữ liệu theo kế hoạch đã validate, trả affected rows/IDs/values
  để service xác nhận đủ; không chọn thay chính sách xuất khi thiếu/sai dữ liệu.
- Trước ledger: ghi giá từng dòng khi phiếu còn cho_duyet rồi cập nhật phiếu da_duyet,
  tổng/actor/time/updated_at/phien_ban. Trigger nguồn ledger yêu cầu trạng thái đã duyệt;
  transaction bảo đảm trạng thái này không lộ thành công trước các bước sau.
- Cập nhật so_luong_ton và so_luong_dang_giu **trong cùng UPDATE mỗi MatHang**,
  giảm cùng lượng để không vi phạm CHECK held <= stock ở trạng thái trung gian.
  Không ghi so_luong_con_dung vì đó là cột sinh. Kết thúc đúng các khoản GiuHang nguồn
  (da_xuat/phieu_xuat_id/ket_thuc_at), giữ mọi khoản của nguồn khác nguyên vẹn.
- INSERT GiaoDichKho âm, loại xuat_linh_kien hoặc xuat_thanh_pham, đủ
  so_luong_ton_sau, actor/posted_at, đúng một FK chi_tiet_phieu_xuat_id. UNIQUE nguồn
  và trigger hiện có được giữ; kiểm chứng bằng PostgreSQL thật, không SQLite.
- TP: cùng transaction chuyển nguồn dap_ung sang hoan_thanh, cập nhật completed_at/
  updated_at/phien_ban. Audit phieu_xuat/duyet; thêm audit yeu_cau_san_xuat/hoan_tat
  khi nguồn thực sự chuyển trạng thái để không mất truy vết thay đổi quan trọng.
- Lỗi giữa bất kỳ bước nào/flush/audit/commit rollback toàn bộ. Retry hợp lệ không
  thực hiện lại các bước này. Không tự sửa chênh lệch ledger/held để cho phép duyệt.
- Protocol khóa cho request/items/holds cần được module sản xuất v4 tương lai tuân
  theo; plan này chưa chứng minh tương thích khóa của mọi API sản xuất legacy.

### F. Strong ETag và replay Q4

- Giữ PhieuXuatService.response làm điểm dựng response/tag; canonical JSON SHA-256
  từ PhieuXuatRead đã hydrate đầy đủ và thứ tự dòng ổn định, không request_id/secret.
  Metadata/phien_ban tham gia body/tag nên vòng từ chối → gửi lại không hồi sinh tag cũ.
- **Mới** dependency cục bộ get_phieu_xuat_if_match trong router gom tất cả header
  cùng tên thành giá trị đầy đủ, chuyển service so dưới khóa. Không đổi get_if_match
  dùng chung của module khác đang có chính sách header lặp 422.
- Một validator phải đúng dạng ETag server sinh: quoted SHA-256 hex 64 ký tự. Thiếu/
  blank 428; weak/wildcard/compound/repeated/không đúng dạng 412. Lần ghi đầu còn
  phải bằng tag hiện tại, so sau khóa/đọc lại và trước điều kiện chuyển trạng thái.
- Duyệt khi da_duyet: vẫn kiểm tra account/role và cú pháp một If-Match, nhưng cho
  hash cũ; đọc/đối chiếu ledger nguồn đã lưu đầy đủ rồi trả resource hiện tại + IDs
  cũ + da_ghi_so_truoc_do=true. Không kiểm tra lại giá/tồn hiện tại để chốt lại,
  không chặn chỉ vì nguồn đã hoàn thành/TP đã ngừng, không thêm audit lần hai.
- Nếu phiếu đã duyệt nhưng ledger thiếu/không nhất quán: 409, không tự bù ledger.
  Q4 không áp dụng cho gửi/từ chối hoặc phiếu cho_duyet/tu_choi chưa ghi sổ.

### G. Port sản xuất và giới hạn Q5

- Giữ chữ ký tong_da_xuat_thanh_pham(yeu_cau_ids),
  co_phieu_da_ghi_so(yeu_cau_id, lenh_ids),
  huy_phieu_chua_ghi_so(yeu_cau_id, lenh_ids, ly_do, actor_id).
- lenh_ids chỉ còn tham số tương thích cho caller cũ; **không dùng để truy vấn bảng
  lệnh**. Nguồn v4 của mọi phiếu là yeu_cau_san_xuat_id. Không đổi port/schema/service
  sản xuất để làm toàn luồng legacy chạy trên v4 trong tác vụ này.
- Port hủy không mở transaction/commit riêng, caller phải sở hữu transaction và
  khóa nguồn theo cùng thứ tự. Chặn nếu đã có phiếu da_duyet; xóa nháp/các dòng và
  audit xoa_nhap; chờ duyệt thành tu_choi, lưu actor/time/version và lý do row
  `Yêu cầu đã hủy`. Audit giữ lý do hủy người gọi và snapshot trước/sau.
- Phiếu đã từ chối giữ nguyên; nguồn bị hủy không cho NV gửi lại. Không giải phóng
  toàn bộ holds thay parent service trong port phiếu: nghiệp vụ hủy yêu cầu sở hữu
  việc trả hàng giữ. Phần duyệt phiếu chỉ kết thúc holds khi xuất thật.
- Kiểm chứng port/data guard và rollback riêng. UC-35/AC-4 qua API hủy sản xuất
  cùng các E2E giữ hàng/hoàn thành sản xuất vẫn hoãn theo Q5, không đánh dấu toàn AC đạt.

## Steps

Task dưới đây là kế hoạch đã duyệt. Kết quả thực hiện tại cuối file và bảng UC/AC/test
thực tế ở [spec mục 7](README.md#7-truy-vết-triển-khai-và-kiểm-thử). Không sửa test nhân viên.

| Task | Kết quả dự kiến | Phụ thuộc | Tiêu chí hoàn thành | UC/AC |
|---|---|---|---|---|
| T01 | Fixture/app/auth/scenario và baseline test thiếu | Duyệt plan | Guard URL test riêng, DB trống/init.sql thật, cleanup riêng; không autouse/khởi động app lifespan; ghi riêng 8 lỗi nền | Tất cả; GI-AC-01–22 |
| T02 | DTO/ORM phiếu và projection nguồn v4/ports | T01 | Đúng SQL hai bảng phiếu; không Lenh ORM/duplicate owner; input server-owned lines; metadata/read/ID bounds | GI-AC-02–06/11/21; UC-34/37 |
| T03 | Snapshot/khóa và đường ghi inventory issue | T02 | Phần giữ/tồn/ledger đúng nguồn, cập nhật stock+held cùng UPDATE; không sửa đường nhập/read/điều chỉnh legacy | GI-AC-08/09/15/16/21 |
| T04 | Audit metadata và DI cùng session | T02 | Đọc/ghi gui_lai và trạng thái; không commit con; caller cũ với field mới nullable không bị bắt buộc ngoài scope | GI-AC-07/10/11/16 |
| T05 | GET list/detail + ETag/auth/query/header dependency | T02 | QLK-only list, NV detail đúng nguồn, Q3/count/page/sort/UTC, tag canonical/metadata, GET read-only | UC-40/AC-1–3; GI-AC-01/02/11/12/18/19 |
| T06 | Tạo nháp LK/TP bằng lượng hệ thống | T03,T04,T05 | NV được giao, nguồn/đủ điều kiện, giá NULL, exact demand, một phiếu mỗi loại/code unique, audit/rollback | UC-34/AC-1–5; UC-37/AC-1–4; GI-AC-03–05/16/20/21 |
| T07 | Gửi/gửi lại và từ chối, gỡ route cũ | T06 | Đúng actor/status/metadata/gui_lai/reason, không đổi tồn/giữ; PATCH/DELETE 405, về nháp 404; không orphan caller | UC-34/AC-6; UC-36/AC-1–3; UC-39/AC-1–2; GI-AC-06/07/10–12 |
| T08 | Duyệt LK/TP và replay Q4 | T03,T04,T06,T07 | Giá/tồn/giữ/ledger/phiếu/nguồn/audit nguyên tử; một nguồn một lần, replay không ghi; TP cũ inactive vẫn hoàn tất | UC-35/AC-1–3; UC-38/AC-1–3; GI-AC-08/09/12–17/20 |
| T09 | Port sản xuất và guard hủy tối thiểu | T07,T08 | Giữ chữ ký, không query lệnh, chặn đã xuất, cleanup nháp/chờ đúng Q5 trong caller transaction; E2E hoãn rõ | UC-35/AC-4 phần guard; GI-AC-22 |
| T10 | PostgreSQL concurrency/failure/trigger/reflection | T06–T09 | Hai session thật với barrier/event; không lost update/double posting/chiếm giữ; rollback mọi điểm, unchanged source khác | GI-AC-04/12–17/21/22 |
| T11 | API integration/regression, OpenAPI và type/lint | T10 | Actual auth/DB roles, status/header/schema/route, toàn phạm vi không hồi quy ngoài 8 lỗi nền; báo đúng skip/lỗi | Tất cả AC backend |
| T12 | Sequence PNG/HTTP evidence/task/trace và bàn giao | T11 | Chỉ endpoint đã triển khai, diagram render/preview; mỗi AC có test thật hoặc lý do hoãn UI/E2E | Tất cả UC/AC |

### Nhóm kiểm chứng trong plan đã duyệt

S = test_phieu_xuat_service.py, A = test_phieu_xuat_api.py,
P = test_phieu_xuat_postgres.py. Bảng này giữ nhóm kiểm chứng của plan; các symbol
thực tế tại bảng spec; không báo test pass từ việc đã ghi tên trong tài liệu.

| UC / AC | Endpoint → service | Test/cách kiểm chứng đề xuất |
|---|---|---|
| UC-34/AC-1–6 | POST + gui → create_issue/submit_issue | S/A/P: exact LK snapshot, reject chưa đủ/source sai, unique create, role NV/QLK, gửi không đổi tồn/giữ, gửi lại không về nháp |
| UC-35/AC-1–3 | duyet → approve → inventory writer | P: 10 tồn/7 giữ → 3 tồn/0 giữ nguồn, giá tại duyệt, ledger -7/tồn sau 3, hai quản lý chỉ ghi một lần; A/S: NV không duyệt |
| UC-35/AC-4 | Port guard hủy → co_phieu_da_ghi_so | P/S: có approved issue chặn hủy trong caller transaction; **E2E API hủy sản xuất hoãn Q5**, không báo toàn AC đạt |
| UC-36/AC-1–3 | tu_choi/detail/gui → reject_issue/get_issue/submit_issue | S/A/P: blank reason 422, giữ LK nguyên, lý do đọc được bởi NV nguồn, gửi lại; UI nút/ẩn về nháp chưa kiểm chứng |
| UC-37/AC-1–4 | POST/gui → create_issue/submit_issue | S/A/P: đủ TP có sẵn, cần SX nhưng hoàn thành chưa duyệt, đúng toàn lượng, nguồn cho_kho bị chặn, gửi không xuất |
| UC-38/AC-1–3 | duyet → approve/update_progress | P: giữ TP có sẵn + vừa SX → cùng da_xuat, chỉ duyệt mới đóng nguồn, concurrency/failure; E2E hoàn thành sản xuất hoãn |
| UC-39/AC-1–2 | tu_choi → reject_issue | S/A/P: lý do bắt buộc, không đổi tồn/giữ/nguồn, actor/time/audit |
| UC-40/AC-1–3 | GET → list_issues/get_issue | A/P: QLK-only list, filter type/state/request/date/q/employee AND, stable ties/count/[]; NV/QTV 403 |
| GI-AC-01/02/11 | Router/guard/scope/read DTO | A: token thiếu/sai/hết hạn/pwdv cũ, account khóa/role DB khác claim, đổi role với token cũ; S: gọi thẳng guard trước I/O |
| GI-AC-06/12/14 | Routes/schema/header/response | A: legacy body bị 422, removed routes 404/405/OpenAPI; repeated/compound/weak/wildcard/missing tag; Q4 stale tag replay đúng, không thêm audit |
| GI-AC-13/15/16 | Request/item/hold locks + transaction | P: hai create, hai approve, approve-vs-reject, submit-vs-reject/replay, nhiều nguồn cùng item; inject lỗi sau giá/phiếu/stock/holds/ledger/nguồn/audit/commit |
| GI-AC-17/19/20 | Price/read-only/old source | P: giá đổi trước/sau, NULL pair/overflow; GET SQL spy; source cũ với TP inactive vẫn hoàn tất và không sửa data chốt |
| GI-AC-21/22 | DB mapping/guard/port | P: reflection/Identity/index/FK/check/trigger, mã tháng/hết dải không reuse; port hủy snapshot/data giữ đúng, caller rollback; UI/E2E hoãn nêu trên |

## Risk level and verification

**HIGH**: breaking API, quyền NV/QLK, persisted metadata, tồn/giữ/ledger, concurrency
và phụ thuộc audit/sản xuất. Không có migration hoặc cập nhật database ứng dụng.

### Môi trường và test hành vi

- Fixture **mới** goods_issue_database nhận `GOODS_ISSUE_TEST_DATABASE_URL`, chỉ cho
  driver postgresql+asyncpg, localhost/127.0.0.1, user goods_issue_test, port **55465**,
  database khởi điểm xbike_goods_issue_test. Không fallback settings.database_url.
- Dùng server PostgreSQL test riêng/tmpfs không volume ứng dụng. Fixture tạo DB
  `goods_issue_<uuid>_test`, kiểm tra trống rồi chạy nguyên init.sql thực, cleanup đúng
  DB có UUID/prefix đã xác minh. Không seed/reset DB có dữ liệu, không metadata.create_all.
- Scenario tạo qua SQL v4 hợp lệ: nhân viên/role, LK/TP/Bom, yêu cầu/chốt nhu cầu,
  nguồn nhập/hoàn thành đã duyệt và ledger hợp lệ trước khi đặt giữ. Không đặt stock
  giả rồi gọi đó là dữ liệu ledger hợp lệ; test corruption riêng phải ghi mục tiêu.
- API fixture override get_db và dùng app qua ASGITransport, không lifespan/app DB;
  token từ helper bảo mật đang có, claims role không thay DB role. Không dump secret.
- Concurrency ít nhất hai session/connection độc lập, dùng barrier/event/timeouts,
  không dùng sleep để hy vọng cạnh tranh. Kiểm chứng riêng cùng nguồn, cùng item
  khác nguồn và replay; không suy ra mất kết nối/worker crash thật từ mock commit fail.
- Failure injection qua từng bước, so snapshot bảng PhieuXuat/chi tiết/MatHang/
  GiuHang/GiaoDichKho/YeuCauSanXuat/LichSuThaoTac trước-sau. No-op replay dùng SQL spy
  và count audit; test thiếu ledger của phiếu approved không tự sửa.
- Mapping/check SQL có thể chưa tự bảo vệ mọi trường hợp NULL; service kiểm tra
  dữ liệu đầy đủ trước ghi sổ, không coi CHECK là thay thế validation nghiệp vụ.
- Đối chiếu sync API/code/spec/test/UC links. Sau pass phạm vi, chạy toàn suite và
  giữ riêng baseline 8 lỗi nhân viên, không sửa kỳ vọng hoặc thêm skip để làm xanh.

### Lệnh kiểm chứng dự kiến, chưa phải kết quả đã chạy

```powershell
# Tại backend, với URL test riêng đúng guard fixture đã được thiết lập.
..\.venv\Scripts\python.exe -m pytest tests/test_phieu_xuat_service.py tests/test_phieu_xuat_api.py tests/test_phieu_xuat_postgres.py -q
..\.venv\Scripts\python.exe -m pytest tests -q --tb=line
..\.venv\Scripts\mypy.exe --follow-imports=silent --disable-error-code import-untyped app/modules/phieu_xuat app/modules/inventory/ports.py app/modules/inventory/repository.py app/modules/audit
# Tại root; chỉ source/test đã sửa, không format toàn project.
.\.venv\Scripts\ruff.exe check <cac-file-da-sua>
.\.venv\Scripts\ruff.exe format --check <cac-file-da-sua>
.\.venv\mermaid\node_modules\.bin\mmdc.cmd -i docs/sequence/phieu_xuat.md -o .venv/goods-issue-sequence.png -e png -b white --size 3000 -s 1.5 -j 2
git diff --check
```

Mypy thiếu asyncpg stubs dùng cấu hình đã nêu, không tuyên bố strict toàn backend;
module legacy có lỗi type ngoài phần sửa được báo riêng, không refactor để làm xanh.
Boundary checker hiện không có architecture declaration: đối chiếu imports/source,
map_structure chỉ đọc, không tạo file kiến trúc giả. Kiểm tra Mermaid render và preview
PNG, links, original UC và diff scope trước bàn giao.

### Rollback và giới hạn

Không migration up/down. Dev review đúng diff phiếu và phần phụ thuộc đã duyệt;
không tự reset branch, xóa database/volume hoặc hoàn tác chứng từ/giữ/ledger đã ghi.
Nếu cần rollback triển khai phải dùng backend/schema tương thích do dev chốt;
backend v3 không tự chạy đúng trên SQL v4. Không coi sửa ORM là đã sửa DB đang chạy.

Không frontend/production E2E hoặc bảo đảm cache module khác hội tụ tức thì. Giới
hạn và từng AC hoãn ghi trong spec/result. Không commit/push nếu chưa được yêu cầu.

## Open questions

Không còn câu hỏi nghiệp vụ Q1–Q6; spec và plan/task đã được dev duyệt.
Phạm vi UI/E2E sản xuất tiếp tục hoãn theo quyết định Q5, không tự mở rộng.

## Kết quả thực hiện ngày 14/11/2026

| Task | Kết quả |
|---|---|
| T01 | Fixture explicit, guard URL/UUID, DB trống + nguyên init.sql thực; JWT thật, ASGITransport không lifespan, không DB ứng dụng |
| T02 | ORM PhieuXuat/ChiTietPhieuXuat đúng v4; source-only input, read metadata, source Core projection; không lệnh/duplicate ORM |
| T03 | Khóa MatHang/GiuHang theo thứ tự, snapshot detached cho service; stock+held cùng UPDATE, ledger có tồn sau, chỉ kết thúc giữ nguồn |
| T04 | Audit state metadata/gui_lai, mapping SQL v4; service audit trong cùng session/transaction; GET audit đọc được trạng thái mới |
| T05 | GET QLK-only list/NV detail đúng nguồn; query AND/date VN/page/sort/empty, strong ETag gồm metadata; local If-Match không đổi dependency chung |
| T06 | NV tạo bằng lượng đã chốt, một phiếu mỗi loại, giá NULL; code tháng VN/advisory/Identity/audit history; concurrency và exhaustion có test |
| T07 | Gửi/gửi lại và từ chối đúng vai trò, metadata/audit, giữ ID/dòng; PATCH/DELETE 405 và về nháp 404 |
| T08 | Duyệt LK/TP nguyên tử, freeze giá dưới khóa, ghi ledger/giữ/tồn/audit; TP đóng nguồn/audit nguồn; replay không ghi, vẫn kiểm tra header format |
| T09 | Giữ ba port sản xuất, bỏ query lệnh; guard hủy, xóa nháp, từ chối chờ với lý do cố định; caller rollback được; E2E sản xuất hoãn |
| T10 | Hai session thật với barrier, create/duyệt/từ chối/gửi/replay, nhiều nguồn cùng item; 6 điểm lỗi rollback, reflection/trigger và dữ liệu lệch |
| T11 | Test tính năng pass; chạy toàn suite, Ruff/type/OpenAPI. Tách riêng 8 lỗi fixture nhân viên và 4 lỗi type đường tồn legacy bên dưới |
| T12 | Spec truy vết đủ 22 GI-AC, 6 sequence phiếu + PNG, inventory/audit sequence liên quan + PNG, HTTP evidence không chứa JWT |

### File đã thay đổi và vai trò

- `backend/app/modules/phieu_xuat/router.py`: sáu endpoint/dependency/UC OpenAPI;
  `schemas.py`: hợp đồng v4 và metadata; `models.py`: mapping đúng bootstrap;
  `ports.py`: snapshot/contract persistence; `repository.py`: projection/khóa/mã/ghi;
  `service.py`: UC-34–40 và điều phối transaction/audit; `errors.py`: bỏ lỗi ngừng mặt
  hàng không còn caller, vì Q6 cho phép hoàn tất yêu cầu cũ.
- `backend/app/modules/inventory/ports.py`: snapshot tồn/giữ và writer contract;
  `repository.py`: chỉ thay `issue_stock`, thêm `lock_issue_stock`. AST đối chiếu HEAD
  xác nhận `lock_balances`, `adjust_stock`, `receive_receipt`, `list_stock`,
  `list_movements` không đổi logic. Không sửa MatHang ORM/cache/CRUD hoặc production.
- `backend/app/modules/audit/{models,schemas}.py`: cột trạng thái nullable, gui_lai,
  mapping CHECK/index v4; không refactor quyền/API UC-43.
- `backend/tests/conftest.py`, `test_phieu_xuat_service.py`, `test_phieu_xuat_api.py`,
  `test_phieu_xuat_postgres.py`: fixture riêng và kiểm chứng S/A/P theo UC/GI-AC.
- `docs/sequence/{phieu_xuat,inventory,audit}.md`, PNG tương ứng (6/3/1 ảnh):
  phản ánh endpoint thật và giới hạn legacy, bỏ ba ảnh sửa/xóa/về nháp xuất đã gỡ và
  không còn tham chiếu. Đã render 10 sơ đồ, preview các ảnh tạo/duyệt/inventory/audit.
- `docs/examples/goods-issue-http.json`: request/body/status/response/header lấy từ
  HTTP test LK lập/gửi/duyệt/replay; chỉ dữ liệu fixture, không lưu Authorization/JWT.
- `specs/use_cases/goods_issue/{README,PLAN}.md`: quyết định đã duyệt, task/kết quả và
  bảng UC → endpoint → service → spec → AC → test. Giữ nguyên bảy UC gốc.

### Kết quả kiểm tra và giới hạn

- Test phiếu xuất: **71 pass**, không skip khi đã cấu hình server test riêng.
- Toàn suite: phần phiếu xuất pass; **8 fail baseline** tại
  `test_nhan_vien_create_code.py:86`, fixture thiếu `VaiTroRead.mo_ta`. Không sửa kỳ vọng,
  fixture hoặc thêm skip cho các test này.
- Ruff check/format phần source/test sửa và `git diff --check`: pass.
- Mypy **11 source file** phiếu xuất + inventory port + audit models/schemas: pass,
  với `--follow-imports=silent --ignore-missing-imports`, không phải strict toàn backend.
  Khi kiểm cả inventory repository: **4 lỗi sẵn có** ở `lock_balances`/`adjust_stock`/
  `receive_receipt` (ledger cần annotation, stock có thể None). Đối chiếu AST không
  đổi các method này và kiểm baseline riêng; không mở rộng để làm xanh type legacy.
- OpenAPI import và tập endpoint kiểm tra đúng 6 route; input cũ không còn trong schema.
- Mermaid CLI render thành công 10 sơ đồ PNG, preview mẫu; link tài liệu/PNG được kiểm tra.
- Structure map: không cycle/misplaced/mixed/unreferenced trong module; các tên DTO
  phổ biến và handler cùng hình dạng không phải lý do tạo abstraction ngoài plan.
  Boundary checker không chạy được kiểm tra phân tầng vì repo chưa có architecture
  declaration; đã đối chiếu import và source thủ công, không tạo config giả.
- Test server riêng port 55465/tmpfs; mỗi test DB `goods_issue_<uuid>_test` tạo từ
  bootstrap trống và cleanup đúng tên. Không dùng app lifespan, application URL hay seed.
  Đã xác minh không còn DB UUID của fixture và dừng đúng container test sau kiểm thử;
  container PostgreSQL ứng dụng cổng 5432 vẫn chạy nguyên trạng.
- Auth hiện hữu xác thực bằng credential hash version `pwdv`, account/role từ DB;
  chưa nâng auth sang cột `phien_ban_dang_nhap` v4. Không tuyên bố đã nâng toàn auth.
- Frontend, API sản xuất/hủy yêu cầu E2E, đường đọc/nhập/điều chỉnh inventory legacy
  chưa nghiệm thu v4. GI-AC-22 chỉ đạt phần guard/port; UC-35 AC-4 E2E vẫn hoãn Q5.
  Không mô phỏng mất kết nối/crash thật bằng test lỗi commit; không bảo đảm cache
  module khác hội tụ tức thì. Bảng AC phân biệt rõ các phần này.

Không sửa SQL/seed/config/dependency/migration, không thay DB ứng dụng, không commit/push.
Rollback note phía trên vẫn áp dụng: backend phải đi với schema tương thích, không
tự hoàn tác ledger/chứng từ hoặc dữ liệu đã ghi sổ.
