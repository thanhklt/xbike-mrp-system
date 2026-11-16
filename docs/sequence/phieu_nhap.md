# Sequence phiếu nhập v4 — UC-20 đến UC-22

Nguồn: [UC-20](../../specs/use_cases/goods_receipt/UC-20.md),
[UC-21](../../specs/use_cases/goods_receipt/UC-21.md),
[UC-22](../../specs/use_cases/goods_receipt/UC-22.md),
[plan đã duyệt](../plans/PR-08-phieu-nhap.md),
`phieu_nhap/{router,service,repository,schemas,models,ports}.py`, `inventory/{ports,repository}.py`,
`audit/{service,repository,schemas,models}.py`, dependencies/core transaction và init.sql v4.

| Endpoint thực tế | UC | PNG |
|---|---|---|
| GET `/api/v1/phieu_nhap` | UC-22 | [Danh sách](assets/phieu_nhap/01-danh-sach.png) |
| GET `/api/v1/phieu_nhap/{id}` | UC-22 | [Chi tiết](assets/phieu_nhap/02-chi-tiet.png) |
| POST `/api/v1/phieu_nhap` | UC-20 | [Tạo nháp](assets/phieu_nhap/03-tao-nhap.png) |
| PATCH `/api/v1/phieu_nhap/{id}` | UC-20 | [Sửa nháp](assets/phieu_nhap/04-sua-nhap.png) |
| DELETE `/api/v1/phieu_nhap/{id}` | UC-20 | [Xóa nháp](assets/phieu_nhap/05-xoa-nhap.png) |
| POST `/api/v1/phieu_nhap/{id}/hoan_tat` | UC-21 | [Hoàn tất](assets/phieu_nhap/06-hoan-tat.png) |

Chỉ `quan_ly` (QLK) dùng cả sáu endpoint; QTV/NV bị chặn, QLK không bị giới hạn
chỉ phiếu mình lập. Mỗi endpoint nhận `actor` qua `Depends(receipt_actor)`;
APIRouter không khai báo thêm dependency quyền trùng. Dependency dùng
`get_current_user_payload` / `AuthService.current_payload` để xác thực người dùng
và kiểm vai trò hiện tại. Service giữ `_require_manager` để bảo vệ lời gọi trực tiếp.
Không phục hồi /receiving hoặc thêm route duyệt.

Response success `{data,meta}`; lỗi `{error:{code,message,details},meta:{request_id}}`.
Tiền integer VND/BIGINT, không Decimal/chuỗi. Timestamp UTC/Z; ngay_nhap là DATE.
Chi tiết có updated_at, hoan_thanh_at, nguoi_hoan_thanh_id, phien_ban. ETag strong
SHA-256 JSON canonical của toàn resource/dòng theo ID/metadata, không gồm request_id.
Phien_ban đổi khi patch thực tế hoặc hoàn tất, không đổi khi no-op/replay.

PATCH/DELETE/hoan_tat yêu cầu một If-Match dạng quoted 64 hex thường. Thiếu/trắng
428; weak/wildcard/nhiều physical header/compound/sai định dạng 412. Tag cũ 412,
ngoại lệ replay hoàn tất bên dưới. GET không body; DELETE không body; mọi endpoint
trừ GET list không nhận query. Khi cùng sai auth và cấu trúc không cam kết ưu tiên lỗi.

## GET /api/v1/phieu_nhap

Query AND: q tìm mã không phân biệt hoa/thường (`%`/`_` literal), trang_thai,
ncc_id, nhan_vien_id, tu_ngay/den_ngay theo **created_at** giờ Asia/Ho_Chi_Minh,
bao gồm cả ngày. Không thêm lọc ngay_nhap. Page1/size20/max100, sort id/created_at/
ma_phieu_nhap hoặc `-`, mặc định id tăng, ID tăng làm tiêu chí phụ. Không ETag list.

```mermaid
%%{init: {"sequence": {"width": 220, "wrap": true, "actorMargin": 40}}}%%
sequenceDiagram
    autonumber
    actor C as QLK
    participant R as phieu_nhap.router<br/>dependencies
    participant A as AuthService
    participant S as PhieuNhapService
    participant P as SqlAlchemy<br/>PhieuNhapRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/phieu_nhap + JWT + query
    R->>A: current_payload(token) via get_current_user_payload
    A-->>R: Authenticated actor with current roles
    R->>R: receipt_actor requires quan_ly
    break Invalid credentials / locked or forbidden role
        R-->>C: 401 / 403
    end
    R->>R: Validate query, reject repeated keys and GET body
    break Invalid / unknown filters or input
        R-->>C: 422
    end
    R->>S: list_receipts(query, actor, request_id)
    S->>S: Require quan_ly
    S->>P: begin_read_snapshot
    P->>DB: Release auth read TX, REPEATABLE READ READ ONLY
    S->>P: list_receipts(query)
    P->>DB: COUNT and sorted page with AND filters
    opt Page nonempty
        P->>DB: Batch/selectin load page lines
    end
    P-->>S: Detached DTOs and count in same snapshot
    S-->>R: List data/meta with page/count/request_id
    R-->>C: 200, empty page is valid
    Note over S,DB: No row locks or INSERT/UPDATE/DELETE, closing session ends read TX
```

## GET /api/v1/phieu_nhap/{id}

ID positive, quá PostgreSQL INTEGER hoặc không tồn tại trả 404. ncc_id tham chiếu
NCC hiện tại, không có snapshot NCC trong resource; UI lookup NCC để hiển thị sau này.

```mermaid
%%{init: {"sequence": {"width": 220, "wrap": true, "actorMargin": 40}}}%%
sequenceDiagram
    autonumber
    actor C as QLK
    participant R as phieu_nhap.router<br/>dependencies
    participant A as AuthService
    participant S as PhieuNhapService
    participant P as SqlAlchemy<br/>PhieuNhapRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/phieu_nhap/{id} + JWT
    R->>A: current_payload(token) via get_current_user_payload
    A-->>R: Authenticated actor with current roles
    R->>R: receipt_actor requires quan_ly
    break Invalid credentials / not active QLK
        R-->>C: 401 / 403
    end
    R->>R: Validate positive ID, no body or query
    break Structural error
        R-->>C: 422
    end
    R->>S: get_receipt(id, actor, request_id)
    S->>S: Require quan_ly
    S->>P: begin_read_snapshot
    P->>DB: REPEATABLE READ READ ONLY after releasing auth read TX
    S->>P: get_receipt(id)
    P->>DB: Read PhieuNhap and selectin lines in same snapshot
    break Missing / out-of-range ID
        S-->>C: 404
    end
    S->>S: Canonical resource hash including metadata/version
    S-->>R: Read DTO and strong ETag
    R-->>C: 200 data/meta + ETag
    Note over S,DB: Same resource version for header, lines and ETag, no writes
```

## POST /api/v1/phieu_nhap

Input ncc_id, ngay_nhap, ghi_chu optional/null, chi_tiet gồm LK/quantity/đơn giá nhập.
ID/lượng strict positive INTEGER, tiền strict nonnegative BIGINT, không float/bool/
chuỗi. Server tính tổng; mã/actor/state/metadata không do client đặt. Giá danh mục
không bị sửa và không thay giá nhập. NCC key-share và LK theo ID tăng FOR UPDATE
trước cấp mã; advisory (20261022,1) chỉ bảo vệ PN-YYYYMM-NNNNNN theo tháng created_at
giờ VN, gồm cả history audit để không reuse mã xóa. ID do Identity, có thể khuyết khi rollback.

```mermaid
%%{init: {"sequence": {"width": 220, "wrap": true, "actorMargin": 40}}}%%
sequenceDiagram
    autonumber
    actor C as QLK
    participant R as phieu_nhap.router<br/>dependencies
    participant A as AuthService
    participant S as PhieuNhapService
    participant P as SqlAlchemy<br/>PhieuNhapRepository
    participant AU as AuditService
    participant AR as SqlAlchemy<br/>AuditRepository
    participant T as SqlAlchemy<br/>Transaction
    participant DB as PostgreSQL
    C->>R: POST /api/v1/phieu_nhap + JWT + JSON
    R->>A: current_payload(token) via get_current_user_payload
    A-->>R: Authenticated actor with current roles
    R->>R: receipt_actor requires quan_ly
    break Invalid credentials / not active QLK
        R-->>C: 401 / 403
    end
    R->>R: Validate schema, unique lines, money range, forbid extras/query
    break Invalid input / extra fields
        R-->>C: 422
    end
    R->>S: create_receipt(payload, actor, request_id)
    S->>S: Require quan_ly
    S->>T: Enter shared transaction
    S->>P: lock_supplier, lock_parts
    P->>DB: NCC FOR KEY SHARE then ordered MatHang FOR UPDATE
    S->>S: Require existing supplier/items and only active linh_kien
    break Missing supplier (404) / missing, inactive or non-component item (409)
        S->>T: Roll back
        S-->>C: 404 / 409
    end
    S->>S: Calculate actual line amounts and total
    S->>P: add_draft with server-owned actor/time
    P->>DB: Advisory monthly code lock, read rows and audit code history
    P->>DB: INSERT Identity header and lines, state nhap, version1
    S->>AU: append tao, state/snapshot after
    AU->>AR: append
    AR->>AR: session.add LichSuThaoTac
    S->>T: Commit once
    T->>DB: Flush audit and COMMIT
    alt Success
        R-->>C: 201 resource + Location + ETag
    else Exhausted code / constraint / unexpected write or commit failure
        T->>DB: ROLLBACK all writes
        R-->>C: 409 / safe 500
    end
    Note over S,DB: No stock, holds, ledger or production writes in a draft
```

## PATCH /api/v1/phieu_nhap/{id}

Field bỏ qua giữ nguyên; ghi_chu=null xóa ghi chú. ncc_id/ngay_nhap/chi_tiet null
bị 422; gửi chi_tiet là thay cả danh sách không rỗng, không endpoint sửa dòng riêng.
So sánh dòng theo `mat_hang_id`, gồm số lượng, đơn giá và `tong_gia`, cùng tổng tiền
phiếu; thứ tự gửi không làm thay đổi phiếu. No-op giữ nguyên dòng/ID, metadata,
phien_ban, ETag và audit, không gọi `patch_draft`. Chỉ gọi `_validate_parts` khi
nội dung dòng thực sự thay đổi; nếu chỉ tổng tiền phiếu sai, cập nhật tổng tiền
không thay dòng hoặc kiểm lại linh kiện. Vì vậy sửa ghi chú kèm dòng cũ vẫn
được phép nếu linh kiện đã ngừng hoạt động. Thay đổi thực tế tăng version/updated_at,
audit before/after. Hoàn tất không được sửa.

```mermaid
%%{init: {"sequence": {"width": 220, "wrap": true, "actorMargin": 40}}}%%
sequenceDiagram
    autonumber
    actor C as QLK
    participant R as phieu_nhap.router<br/>dependencies
    participant A as AuthService
    participant S as PhieuNhapService
    participant P as SqlAlchemy<br/>PhieuNhapRepository
    participant AU as AuditService
    participant AR as SqlAlchemy<br/>AuditRepository
    participant T as SqlAlchemy<br/>Transaction
    participant DB as PostgreSQL
    C->>R: PATCH /api/v1/phieu_nhap/{id} + JWT + If-Match + JSON
    R->>A: current_payload(token) via get_current_user_payload
    A-->>R: Authenticated actor with current roles
    R->>R: receipt_actor requires quan_ly
    break Invalid credentials / not active QLK
        R-->>C: 401 / 403
    end
    R->>R: Validate schema/query, retain every physical If-Match
    break Invalid structure / field semantics
        R-->>C: 422
    end
    R->>S: patch_receipt
    S->>S: Require quan_ly
    S->>T: Enter transaction
    S->>P: lock_receipt(id)
    P->>DB: PhieuNhap then ordered lines FOR UPDATE
    break Missing resource
        S-->>C: 404, rollback
    end
    S->>S: Require one canonical tag and compare under lock
    break Missing / invalid / stale validator
        S-->>C: 428 / 412, rollback
    end
    S->>S: Require nhap
    break Already completed
        S-->>C: 409, rollback
    end
    S->>P: receipt_postings
    P->>DB: Read ledger references
    break Referenced by ledger
        S-->>C: 409, rollback
    end
    opt Supplier changed
        S->>P: lock_supplier
        P->>DB: NCC FOR KEY SHARE
    end
    break Missing supplier
        S-->>C: 404, rollback
    end
    S->>S: Calculate lines and total, compare by mat_hang_id including tong_gia
    opt Actual line content changed
        S->>P: lock_parts
        P->>DB: MatHang FOR UPDATE ordered by ID
        S->>S: Shared validation of existing active components
        break Missing, inactive or non-component item
            S-->>C: 409 phu_thuoc_khong_hop_le, rollback
        end
    end
    alt Actual change
        S->>P: patch_draft(changes, replacement lines)
        P->>DB: Replace lines only if changed, update header/time/version +1
        S->>AU: append sua, before/after state and snapshots
        AU->>AR: append
        AR->>AR: session.add
    else No-op
        S->>S: Keep resource, version and audit unchanged
    end
    S->>T: Commit
    T->>DB: Flush audit if any and COMMIT
    R-->>C: 200 resource + ETag
    Note over T,DB: Any write/audit/commit failure rolls back all changes, 409 or safe 500
```

## DELETE /api/v1/phieu_nhap/{id}

Chỉ nháp chưa có ledger. Audit giữ full snapshot trước/mã; snapshot và state sau null.
Xóa/audit cùng transaction, không cascade xóa ledger/audit. Thành công 204 không body.

```mermaid
%%{init: {"sequence": {"width": 220, "wrap": true, "actorMargin": 40}}}%%
sequenceDiagram
    autonumber
    actor C as QLK
    participant R as phieu_nhap.router<br/>dependencies
    participant A as AuthService
    participant S as PhieuNhapService
    participant P as SqlAlchemy<br/>PhieuNhapRepository
    participant AU as AuditService
    participant AR as SqlAlchemy<br/>AuditRepository
    participant T as SqlAlchemy<br/>Transaction
    participant DB as PostgreSQL
    C->>R: DELETE /api/v1/phieu_nhap/{id} + JWT + If-Match
    R->>A: current_payload(token) via get_current_user_payload
    A-->>R: Authenticated actor with current roles
    R->>R: receipt_actor requires quan_ly
    break Invalid credentials / not active QLK
        R-->>C: 401 / 403
    end
    R->>R: Positive ID, no body/query, retain physical headers
    break Invalid structure
        R-->>C: 422
    end
    R->>S: delete_receipt
    S->>S: Require quan_ly
    S->>T: Enter transaction
    S->>P: lock_receipt(id)
    P->>DB: Header and ordered lines FOR UPDATE
    break Missing resource
        S-->>C: 404, rollback
    end
    S->>S: Validate one strong If-Match and current version
    break Missing / invalid / stale tag
        S-->>C: 428 / 412, rollback
    end
    S->>S: Require nhap
    break Already completed
        S-->>C: 409, rollback
    end
    S->>P: receipt_postings
    P->>DB: Read references
    break Referenced by ledger
        S-->>C: 409, rollback
    end
    S->>P: delete_draft
    P->>DB: DELETE lines then header
    S->>AU: append xoa_nhap, full before, null after/state
    AU->>AR: append
    AR->>AR: session.add
    S->>T: Commit
    T->>DB: Flush audit and COMMIT
    alt Success
        R-->>C: 204, no body
    else Write / audit / commit failure
        T->>DB: ROLLBACK deletion and audit
        R-->>C: 409 / safe 500
    end
```

## POST /api/v1/phieu_nhap/{id}/hoan_tat

Body `{}` bắt buộc. Thứ tự khóa: phiếu → chi tiết tăng ID → MatHang tăng ID.
Service kiểm nội dung persisted, số dư khớp SUM ledger và không tràn INTEGER.
mark_completed UPDATE có điều kiện id/nhap/phien_ban, ghi metadata cùng state trước
INSERT ledger để đáp ứng trigger. Tiền nhập giữ nguyên; không sửa giá danh mục,
so_luong_dang_giu hoặc GiuHang, không tự kiểm tra/đổi yêu cầu sản xuất.

```mermaid
%%{init: {"sequence": {"width": 220, "wrap": true, "actorMargin": 40}}}%%
sequenceDiagram
    autonumber
    actor C as QLK
    participant R as phieu_nhap.router<br/>dependencies
    participant A as AuthService
    participant S as PhieuNhapService
    participant P as SqlAlchemy<br/>PhieuNhapRepository
    participant I as SqlAlchemy<br/>InventoryRepository
    participant AU as AuditService
    participant AR as SqlAlchemy<br/>AuditRepository
    participant T as SqlAlchemy<br/>Transaction
    participant DB as PostgreSQL
    C->>R: POST /api/v1/phieu_nhap/{id}/hoan_tat + JWT + If-Match + empty object
    R->>A: current_payload(token) via get_current_user_payload
    A-->>R: Authenticated actor with current roles
    R->>R: receipt_actor requires quan_ly
    break Invalid credentials / not active QLK
        R-->>C: 401 / 403
    end
    R->>R: Required empty object, positive ID, no query, retain headers
    break Invalid structure
        R-->>C: 422
    end
    R->>S: complete_receipt
    S->>S: Require quan_ly
    S->>T: Enter shared transaction
    S->>P: lock_receipt
    P->>DB: Header then ordered lines FOR UPDATE
    break Missing / out-of-range ID
        S-->>C: 404, rollback
    end
    S->>S: Require one quoted SHA-256 validator including replay
    break Missing / blank / malformed, weak, wildcard or multiple tags
        S-->>C: 428 / 412, rollback
    end
    S->>P: receipt_postings(id)
    P->>DB: Read existing ledger rows
    alt Already hoan_thanh
        S->>S: Require one matching item/type/quantity posting per line
        alt Complete consistent posting
            R-->>C: 200 current resource, old ledger IDs, replay=true, ETag
        else Incomplete or inconsistent ledger
            S-->>C: 409, no repair
        end
        Note over S,DB: Retry carries the old draft ETag (AC-3), check format only, no writes or second audit
    else First completion
        S->>S: Compare current ETag, validate no ledger and persisted content/totals
        break Stale tag / referenced or invalid draft
            S-->>C: 412 / 409, rollback
        end
        S->>I: lock_receipt_stock(item IDs)
        I->>DB: MatHang FOR UPDATE ordered by ID, read SUM ledger
        I-->>S: Detached ReceiptStock snapshots
        S->>S: Validate LK, balance equals ledger, stock plus quantity in INTEGER range
        break Missing/wrong item, inconsistent or overflowing balance
            S-->>C: 409, rollback
        end
        S->>P: mark_completed(expected_version, actor_id, timestamp)
        P->>DB: Conditional UPDATE state, completion actor/time, updated_at, version +1
        break Zero rows updated
            S-->>C: 412, rollback
        end
        S->>I: receive_receipt(lines, actor_id, timestamp)
        I->>DB: Increase stock, RETURNING balance, preserve held/price
        break UPDATE returns no row
            I-->>S: ConflictException (409)
            T->>DB: ROLLBACK state and all writes
        end
        I->>DB: INSERT nhap_linh_kien per line with so_luong_ton_sau
        S->>AU: append hoan_tat, before/after state and snapshots
        AU->>AR: append
        AR->>AR: session.add LichSuThaoTac
        S->>T: Commit once
        T->>DB: Flush audit and COMMIT
        alt Success
            R-->>C: 200 resource, ledger IDs, replay=false, new ETag
        else Error in state/stock/ledger/audit/commit
            T->>DB: ROLLBACK every write
            R-->>C: 409 / safe 500
        end
    end
```

Replay giữ quyền/header đúng policy; không quyết định lại theo giá hoặc tồn hiện tại.
Nhập không có ticket/phiếu điều chỉnh hoặc bước duyệt. Trigger MatHang thông báo sau
commit, cache khác cập nhật theo listener/reconciliation, không bảo đảm tức thì.
Test ASGI với repository/session giả kiểm tra các AC backend, SQL ghi sổ thật và
rollback khi UPDATE không có dòng. Test FE `uc21-hoan-tat-phieu-nhap.test.js` dùng
ReceiptEditor và Confirmation hiện tại, xác nhận Hủy/X/Escape không gọi API.
Chưa kiểm chứng DB PostgreSQL thật, tranh chấp đồng thời hoặc E2E trình duyệt.
