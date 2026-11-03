# Luồng API ticket lỗi điều chỉnh — contract v3

## Ảnh PNG cho từng endpoint

| Endpoint | Ảnh sequence |
|---|---|
| GET `/api/v1/ticket_loi_dieu_chinh` | [01 — Danh sách](assets/ticket_dieu_chinh/01-danh-sach.png) |
| GET `/api/v1/ticket_loi_dieu_chinh/{id}` | [02 — Chi tiết](assets/ticket_dieu_chinh/02-chi-tiet.png) |
| POST `/api/v1/ticket_loi_dieu_chinh/{id}/nhan_xu_ly` | [03 — Nhận xử lý](assets/ticket_dieu_chinh/03-nhan-xu-ly.png) |
| POST `/api/v1/ticket_loi_dieu_chinh/{id}/giai_quyet` | [04 — Giải quyết](assets/ticket_dieu_chinh/04-giai-quyet.png) |

Module `backend/app/modules/ticket_dieu_chinh/` triển khai bốn endpoint dưới tiền tố `/api/v1/ticket_loi_dieu_chinh`, theo `docs/api_contract_v3.md` §2, §3, §12.2, §14 và bảng `"TicketLoiDieuChinh"`, `"ChiTietTicketLoiDieuChinh"` trong `infra/postgres/init.sql`.

## Quy ước đang triển khai

- Chỉ Q (`quan_ly`) được gọi cả bốn endpoint. A và N nhận 403. Mỗi request xác minh JWT, phiên bản mật khẩu, trạng thái tài khoản và vai trò hiện tại trong DB thông qua AuthService → NhanVienService → SqlAlchemyNhanVienRepository.
- Response thành công `{data, meta: {request_id}}`; danh sách thêm page, page_size, total, total_pages vào meta. Lỗi `{error: {code, message, details}, meta: {request_id}}`; 401 có `WWW-Authenticate: Bearer`. Validation 422 không echo input nhạy cảm.
- TicketRead gồm header, người tạo/người xử lý, thời gian và các dòng snapshot. Dòng chi tiết sắp theo ID; trường số lượng là integer, `so_luong_bien_dong` có thể âm. Các timestamp trả UTC có `Z`. Không có trường tiền, giao dịch kho hoặc cờ ghi sổ trong response ticket.
- GET chi tiết và hai action trả strong ETag trên toàn bộ TicketRead, gồm trạng thái, người xử lý, kết quả, thời gian đóng và snapshot chi tiết. `request_id` không tham gia ETag.
- Hai action yêu cầu If-Match. Sau khi khóa và đọc resource, kiểm tra header và ETag trước điều kiện trạng thái/người xử lý. Thiếu/rỗng trả 428; stale, weak, wildcard hoặc không khớp trả 412. Header lặp trả 422. Ticket không thuộc nhóm action ghi sổ cho retry bỏ qua ETag: không có nhánh idempotent trả kết quả cũ khi header stale.
- `nhan_xu_ly` chỉ từ `cho_xu_ly` sang `dang_xu_ly`, người xử lý lấy từ JWT. `giai_quyet` đóng trực tiếp từ `cho_xu_ly`, hoặc từ `dang_xu_ly` nếu người gọi chính là người đã nhận. Khi đóng từ `cho_xu_ly`, người đóng trở thành người xử lý. Ticket đã `da_xu_ly` không sửa, đóng lại hoặc mở lại.
- Bối cảnh gốc và chi tiết snapshot bất biến. Không có endpoint tạo, PATCH, DELETE hoặc mở lại ticket. Việc hệ thống tạo ticket khi xác nhận điều chỉnh thất bại thuộc luồng phiếu điều chỉnh, ngoài phạm vi bốn endpoint này.
- Nhận xử lý/đóng ticket chỉ cập nhật header cho phép và audit. Không đọc điều kiện thành công của phiếu điều chỉnh mới, không cập nhật phiếu nhập, tồn kho, ledger hoặc tiến độ.
- GET giữ khóa FOR SHARE trên header; SQLAlchemy select-in load các dòng snapshot bất biến theo ID. Danh sách COUNT trước, sau đó truy vấn trang header và nạp chi tiết; tổng có thể thay đổi giữa các truy vấn nếu hệ thống tạo ticket đồng thời. GET không ghi trạng thái hoặc audit.
- Action giữ khóa FOR UPDATE trên header đến hết transaction, rồi đọc snapshot chi tiết. So sánh ETag và ghi dưới cùng khóa. Hai quản lý cùng nhận/đóng với một ETag: một request thành công, request còn lại đọc phiên bản mới và nhận 412.
- Luồng audit là TicketDieuChinhService → AuditService.append → SqlAlchemyAuditRepository.append. Repository audit chỉ session.add; SqlAlchemyTransaction.__aexit__ gọi session.commit, flush pending audit rồi COMMIT. Ticket và audit dùng chung session/transaction, bất kỳ lỗi ghi/flush/commit nào đều rollback cả hai. Các dependency của FastAPI có thể được giải quyết xen kẽ với validation trước handler.

## GET /api/v1/ticket_loi_dieu_chinh

Q đọc toàn bộ ticket. Query: `page` mặc định 1, `page_size` mặc định 20 (tối đa 100), `trang_thai`, `phieu_nhap_id`, `nguoi_tao_id`, `nguoi_xu_ly_id`, `tu_ngay`, `den_ngay`, `sort`. Sort cho phép `id`, `created_at`, `ma_ticket` và dạng giảm dần với tiền tố `-`; ID là tiêu chí phụ. Không có `q`, `search`, `sort_by` hoặc `sort_order`. Ngày lọc theo `created_at`, lấy cả hai đầu ngày Asia/Ho_Chi_Minh bằng khoảng UTC nửa mở. Query lặp, trường lạ, sort/enum/ngày không hợp lệ trả 422. Danh sách rỗng trả 200, không trả ETag.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as Router / dependencies
    participant AU as AuthService
    participant NV as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as TicketDieuChinhService
    participant P as SqlAlchemyTicketDieuChinhRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/ticket_loi_dieu_chinh + query + JWT
    R->>AU: current_payload(token)
    AU->>NV: get_auth_identity(subject, pwdv)
    NV->>NR: get_credentials_by_id
    NR->>DB: Read current employee and role
    break JWT missing, invalid, expired or revoked
        AU-->>C: 401 chua_xac_thuc + WWW-Authenticate Bearer
    end
    break Account locked or role is not Q
        R-->>C: 403 tai_khoan_bi_vo_hieu_hoa / khong_co_quyen
    end
    R->>R: Validate query, whitelist, dates and repeated parameters
    break Query invalid or unsupported
        R-->>C: 422 du_lieu_khong_hop_le
    end
    R->>S: list_tickets(params, actor, request_id)
    S->>P: list_tickets(params)
    P->>DB: COUNT with combined filters
    P->>DB: Page headers FOR SHARE, stable sort and pagination
    P->>DB: Select-in load immutable snapshot lines ordered by ID
    DB-->>P: Headers, snapshots and total
    P-->>S: RecordPage TicketRead
    S-->>R: data + pagination meta + request_id
    R-->>C: 200, empty data allowed, no ETag
    Note over S,DB: No ticket, receipt, stock, ledger or audit writes
```

## GET /api/v1/ticket_loi_dieu_chinh/{id}

Q đọc được ticket ở cả ba trạng thái. Không nhận query. ID path phải là integer dương; không tồn tại trả 404. Response chứa snapshot của sự việc thất bại, không tính lại số lượng hoặc tồn hiện tại.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as Router / dependencies
    participant AU as AuthService
    participant NV as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as TicketDieuChinhService
    participant P as SqlAlchemyTicketDieuChinhRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/ticket_loi_dieu_chinh/id + JWT
    R->>AU: current_payload(token)
    AU->>NV: get_auth_identity(subject, pwdv)
    NV->>NR: get_credentials_by_id
    NR->>DB: Read current employee and role
    break JWT invalid or account missing
        AU-->>C: 401 chua_xac_thuc
    end
    break Account locked or role is not Q
        R-->>C: 403
    end
    R->>R: Validate positive path ID and reject query
    break Input invalid
        R-->>C: 422 du_lieu_khong_hop_le
    end
    R->>S: get_ticket(id, actor, request_id)
    S->>P: get_ticket(id)
    P->>DB: Header FOR SHARE and immutable lines ordered by ID
    break Ticket does not exist
        S-->>C: 404 khong_tim_thay
    end
    P-->>S: Detached TicketRead
    S->>S: Hash TicketRead for strong ETag
    S-->>R: data, meta and ETag
    R-->>C: 200 + ETag
    Note over S,DB: Original error and snapshot quantities are unchanged
```

## POST /api/v1/ticket_loi_dieu_chinh/{id}/nhan_xu_ly

Chỉ Q; body JSON object rỗng `{}` bắt buộc. Chỉ nhận ticket đang `cho_xu_ly`. Người nhận lấy từ JWT đã xác minh, client không được gửi người xử lý hoặc trạng thái. Thành công trả TicketRead ở `dang_xu_ly`, ETag mới và audit `nhan_xu_ly`.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as Router / dependencies
    participant AU as AuthService
    participant NV as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as TicketDieuChinhService
    participant P as SqlAlchemyTicketDieuChinhRepository
    participant A as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: POST /api/v1/ticket_loi_dieu_chinh/id/nhan_xu_ly + {} + If-Match + JWT
    R->>AU: current_payload(token)
    AU->>NV: get_auth_identity(subject, pwdv)
    NV->>NR: get_credentials_by_id
    NR->>DB: Read current employee and role
    break JWT invalid or account missing
        AU-->>C: 401 chua_xac_thuc
    end
    break Account locked or role is not Q
        R-->>C: 403
    end
    R->>R: Validate body {}, path, no query and no repeated If-Match
    break Input invalid
        R-->>C: 422 du_lieu_khong_hop_le
    end
    R->>S: claim_ticket(id, actor, If-Match, request_id)
    S->>T: __aenter__, use shared request session
    S->>P: lock_ticket(id)
    P->>DB: Header FOR UPDATE, immutable lines ordered by ID
    break Ticket missing
        S-->>C: 404 khong_tim_thay
    end
    S->>S: Require and compare strong If-Match under lock
    break If-Match missing or blank
        S-->>C: 428 thieu_if_match
    end
    break If-Match stale, weak, wildcard or mismatched
        S-->>C: 412 du_lieu_da_thay_doi
    end
    break Ticket state is not cho_xu_ly
        S-->>C: 409 trang_thai_khong_hop_le
    end
    S->>P: claim_ticket(id, actor_id)
    P->>DB: UPDATE state dang_xu_ly, assignee from JWT
    P-->>S: TicketRead after claim
    S->>A: append nhan_xu_ly with before/after snapshots
    A->>AR: append(CreationAudit)
    AR->>AR: session.add, no independent commit
    S->>T: __aexit__ success
    T->>DB: session.commit flushes pending audit then COMMIT
    break Ticket write, audit, flush or commit failure
        T->>DB: ROLLBACK ticket and audit
        T-->>C: 409 constraint conflict or 500 safe error
    end
    S->>S: Hash updated TicketRead
    S-->>R: data, meta and new ETag
    R-->>C: 200 + ETag
    Note over S,DB: No stock or ledger writes, no successful-adjustment prerequisite
```

## POST /api/v1/ticket_loi_dieu_chinh/{id}/giai_quyet

Chỉ Q; body bắt buộc `{ket_qua_xu_ly: string}`, trim không rỗng, cấm trường lạ. Đóng trực tiếp ticket `cho_xu_ly` hoặc ticket `dang_xu_ly` đã được chính người gọi nhận. Người xử lý là người đóng lấy từ JWT; ghi kết quả và `closed_at`, audit `giai_quyet`. Không mở lại ticket đã đóng và không yêu cầu điều chỉnh mới thành công.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as Router / dependencies
    participant AU as AuthService
    participant NV as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as TicketDieuChinhService
    participant P as SqlAlchemyTicketDieuChinhRepository
    participant A as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: POST /api/v1/ticket_loi_dieu_chinh/id/giai_quyet + result + If-Match + JWT
    R->>AU: current_payload(token)
    AU->>NV: get_auth_identity(subject, pwdv)
    NV->>NR: get_credentials_by_id
    NR->>DB: Read current employee and role
    break JWT invalid or account missing
        AU-->>C: 401 chua_xac_thuc
    end
    break Account locked or role is not Q
        R-->>C: 403
    end
    R->>R: Validate nonblank result, path, no query and no repeated If-Match
    break Input invalid or extra field
        R-->>C: 422 du_lieu_khong_hop_le
    end
    R->>S: resolve_ticket(id, result, actor, If-Match, request_id)
    S->>T: __aenter__, use shared request session
    S->>P: lock_ticket(id)
    P->>DB: Header FOR UPDATE, immutable lines ordered by ID
    break Ticket missing
        S-->>C: 404 khong_tim_thay
    end
    S->>S: Require and compare strong If-Match under lock
    break If-Match missing or blank
        S-->>C: 428 thieu_if_match
    end
    break If-Match stale, weak, wildcard or mismatched
        S-->>C: 412 du_lieu_da_thay_doi
    end
    break Ticket already da_xu_ly
        S-->>C: 409 trang_thai_khong_hop_le
    end
    break Ticket dang_xu_ly belongs to another manager
        S-->>C: 403 khong_co_quyen
    end
    S->>S: Capture closed_at as current UTC time
    S->>P: resolve_ticket(id, actor_id, result, closed_at)
    P->>DB: UPDATE da_xu_ly, assignee, result and closed_at
    P-->>S: Closed TicketRead
    S->>A: append giai_quyet with before/after snapshots
    A->>AR: append(CreationAudit)
    AR->>AR: session.add, no independent commit
    S->>T: __aexit__ success
    T->>DB: session.commit flushes pending audit then COMMIT
    break Ticket write, audit, flush or commit failure
        T->>DB: ROLLBACK ticket and audit
        T-->>C: 409 constraint conflict or 500 safe error
    end
    S->>S: Hash closed TicketRead
    S-->>R: data, meta and new ETag
    R-->>C: 200 + ETag
    Note over P,DB: Original context and detail snapshots remain immutable
    Note over S,DB: No receipt, adjustment, stock or ledger writes
```
