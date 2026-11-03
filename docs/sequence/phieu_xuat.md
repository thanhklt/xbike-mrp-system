# Luồng API phiếu xuất — contract v3

## Ảnh PNG cho từng endpoint

| Endpoint | Ảnh sequence |
|---|---|
| GET `/api/v1/phieu_xuat` | [01 — Danh sách](assets/phieu_xuat/01-danh-sach.png) |
| GET `/api/v1/phieu_xuat/{id}` | [02 — Chi tiết](assets/phieu_xuat/02-chi-tiet.png) |
| POST `/api/v1/phieu_xuat` | [03 — Tạo nháp](assets/phieu_xuat/03-tao-nhap.png) |
| PATCH `/api/v1/phieu_xuat/{id}` | [04 — Sửa nháp](assets/phieu_xuat/04-sua-nhap.png) |
| DELETE `/api/v1/phieu_xuat/{id}` | [05 — Xóa nháp](assets/phieu_xuat/05-xoa-nhap.png) |
| POST `/api/v1/phieu_xuat/{id}/gui` | [06 — Gửi](assets/phieu_xuat/06-gui.png) |
| POST `/api/v1/phieu_xuat/{id}/duyet` | [07 — Duyệt](assets/phieu_xuat/07-duyet.png) |
| POST `/api/v1/phieu_xuat/{id}/tu_choi` | [08 — Từ chối](assets/phieu_xuat/08-tu-choi.png) |
| POST `/api/v1/phieu_xuat/{id}/ve_nhap` | [09 — Về nháp](assets/phieu_xuat/09-ve-nhap.png) |

Đối chiếu `docs/api_contract_v3.md` §2, §3, §10, §14 và code hiện tại. Nguồn schema là `infra/postgres/init.sql`, bảng PascalCase. Đơn giá mặt hàng và ba cột tiền phiếu xuất dùng BIGINT theo quyết định của dev; API trả JSON integer VND, không trả chuỗi Decimal. Không chạy migration hoặc cập nhật database đang có dữ liệu.

Q được đọc và ghi mọi phiếu, kể cả tự duyệt phiếu mình lập. N chỉ đọc phiếu thuộc lệnh/yêu cầu hiện được giao, không kiểm tra N là người lập. A bị từ chối. Vai trò, tài khoản và phiên bản mật khẩu được kiểm tra từ DB mỗi request. Người lập và người ghi audit/ledger lấy từ JWT đã xác minh.

Chỉ đăng ký chín endpoint dưới đây. `/material-issuing` và `/finished-goods-issuing` đã được gỡ khỏi app.main, không còn đường ghi cũ để vượt quyền/giá v3. Phần tương tác nội bộ với module sản xuất vẫn dùng `PhieuXuatService` và `SqlAlchemyPhieuXuatRepository`.

Response thành công `{data,meta}`, lỗi `{error:{code,message,details},meta:{request_id}}`. GET chi tiết và các response ghi trả strong ETag trên resource gồm trạng thái và chi tiết sắp theo ID. POST trả 201 + Location, DELETE 204 không body, còn lại 200. Validation 422 không echo input nhạy cảm. 405 theo FastAPI mặc định.

POST chỉ nhận loại, đúng một FK nguồn và chi_tiet gồm mặt hàng/số lượng. Không nhận đơn giá, tổng, người lập, mã phiếu hoặc trạng thái. Nháp/chờ duyệt/từ chối giữ giá và tổng null. PATCH chỉ nhận chi_tiet, bỏ qua giữ nguyên, null/array rỗng bị từ chối, gửi array thì thay toàn bộ dòng. PATCH không đổi dữ liệu không ghi thêm audit.

Giao dịch ghi dùng chung AsyncSession với auth, audit và inventory. Để đồng bộ với hủy yêu cầu sản xuất, thứ tự khóa là yêu cầu → lệnh (nếu có) → phiếu → chi tiết → mặt hàng tăng dần ID. lock_context đọc FK bất biến trước, khóa nguồn, rồi đọc lại phiếu FOR UPDATE và kiểm tra ETag dưới khóa. GET giữ FOR SHARE trên phiếu/chi tiết đến khi đọc xong, không ghi dữ liệu. COUNT và trang là hai truy vấn nên tổng có thể đổi giữa hai truy vấn khi có tạo/xóa đồng thời.

Thay đổi phiếu cần If-Match: thiếu/rỗng 428, weak/wildcard/sai định dạng/cũ 412. Riêng duyệt đã thành công nhận strong ETag cũ, trả resource hiện tại với da_ghi_so_truoc_do=true và các ID ledger đã có; vẫn phải còn quyền, có header hợp lệ. Không ghi kho/audit lần hai. Phiếu da_duyet bất biến.

Mã PX-YYYYMM-NNNNNN do PostgreSQL xác định tháng Asia/Ho_Chi_Minh; advisory transaction lock (20261022,3) bảo vệ cấp mã. Xét cả mã hiện có và snapshot audit để không tái sử dụng mã đã xóa. ID do IDENTITY cấp, có thể khuyết khi rollback.

AuditService.append → SqlAlchemyAuditRepository.append chỉ session.add, chưa INSERT. SqlAlchemyTransaction.commit flush cả audit rồi COMMIT. Lỗi bất kỳ ở giá/trạng thái/ledger/tồn/tiến độ/audit hoặc commit đều rollback toàn bộ. Không có ticket khi duyệt xuất thất bại.

## GET /api/v1/phieu_xuat

Q/N. Query: page/page_size, q, sort, loai_phieu, trang_thai, nhan_vien_id, lenh_san_xuat_id, yeu_cau_san_xuat_id, tu_ngay/den_ngay. Ngày lọc theo Asia/Ho_Chi_Minh, sort whitelist thêm ID. Không ETag danh sách.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as Router / dependencies
    participant AU as AuthService
    participant NV as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/phieu_xuat + JWT
    R->>AU: current_payload(token)
    AU->>NV: get_auth_identity(subject, pwdv)
    NV->>NR: get_credentials_by_id
    NR->>DB: Read current employee and role
    break Missing/invalid/revoked JWT or missing account
        AU-->>C: 401 chua_xac_thuc + WWW-Authenticate Bearer
    end
    break Account locked or role not allowed
        R-->>C: 403
    end
    R->>R: Validate body, path and query
    break Invalid input, extra or repeated query/header
        R-->>C: 422 du_lieu_khong_hop_le
    end
    R->>S: list_issues(query, actor, request_id)
    S->>P: list_issues with assignment scope for N, all for Q
    P->>DB: Apply EXISTS current assignment, filters, COUNT, sort and pagination
    P->>DB: Read headers and sorted lines under FOR SHARE
    DB-->>P: Records and total, empty results allowed
    P-->>S: RecordPage PhieuXuatRead
    S-->>R: data + pagination meta + request_id
    R-->>C: 200, no stock/state/audit writes
```

## GET /api/v1/phieu_xuat/{id}

Q/N. N ngoài công việc hiện được giao nhận 403; phiếu không tồn tại 404. Không cần N là người lập.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as Router / dependencies
    participant AU as AuthService
    participant NV as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/phieu_xuat/{id} + JWT
    R->>AU: current_payload(token)
    AU->>NV: get_auth_identity(subject, pwdv)
    NV->>NR: get_credentials_by_id
    NR->>DB: Read current employee and role
    break Missing/invalid/revoked JWT or missing account
        AU-->>C: 401 chua_xac_thuc + WWW-Authenticate Bearer
    end
    break Account locked or role not allowed
        R-->>C: 403
    end
    R->>R: Validate body, path and query
    break Invalid input, extra or repeated query/header
        R-->>C: 422 du_lieu_khong_hop_le
    end
    R->>S: get_issue(id, actor, request_id)
    S->>P: get_issue
    P->>DB: FOR SHARE issue then sorted lines
    break Issue missing or ID outside INTEGER
        S-->>C: 404 khong_tim_thay
    end
    opt Actor N
        S->>P: assigned_to(record, employee_id)
        P->>DB: EXISTS order/request current assignee
        break Assignment belongs to another employee
            S-->>C: 403 khong_co_quyen
        end
    end
    S->>S: Hash resource for strong ETag
    S-->>R: data, meta, ETag
    R-->>C: 200 + ETag
```

## POST /api/v1/phieu_xuat

Chỉ Q, không If-Match. Kiểm tra đúng nguồn, trạng thái và mặt hàng active thuộc nhu cầu trực tiếp. Không kiểm tồn hoặc ghi kho ở bước tạo nháp.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as Router / dependencies
    participant AU as AuthService
    participant NV as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant DB as PostgreSQL
    participant T as SqlAlchemyTransaction
    participant A as AuditService
    participant AR as SqlAlchemyAuditRepository
    C->>R: POST /api/v1/phieu_xuat + JWT
    R->>AU: current_payload(token)
    AU->>NV: get_auth_identity(subject, pwdv)
    NV->>NR: get_credentials_by_id
    NR->>DB: Read current employee and role
    break Missing/invalid/revoked JWT or missing account
        AU-->>C: 401 chua_xac_thuc + WWW-Authenticate Bearer
    end
    break Account locked or role not allowed
        R-->>C: 403
    end
    R->>R: Validate body, path and query
    break Invalid input, extra or repeated query/header
        R-->>C: 422 du_lieu_khong_hop_le
    end
    R->>S: create_issue(payload, actor, request_id)
    S->>T: __aenter__
    S->>P: lock_source then lock_parts in ascending ID, FOR SHARE
    P->>DB: Lock request/order, read demand and active items
    break Source/item missing or source state invalid
        S-->>C: 404 / 409 trang_thai_khong_hop_le
    end
    break Inactive/wrong item, wrong source demand or excessive quantity
        S-->>C: 409 mat_hang_ngung_hoat_dong / phu_thuoc_khong_hop_le / vuot_nhu_cau
    end
    S->>P: add draft with actor_id and null prices
    P->>DB: Advisory code lock, monthly code from rows/audit, INSERT header/lines with IDENTITY
    S->>A: append(CreationAudit with before/after and reason)
    A->>AR: append(entry)
    AR->>AR: session.add audit, no independent commit
    S->>T: __aexit__ success
    T->>DB: session.commit, flush pending audit then COMMIT
    break Write, audit, flush or commit failure
        T->>DB: ROLLBACK all document, stock, ledger and progress changes
        T-->>C: 409 database constraint or 500 safe error
    end
    S-->>R: Draft resource, meta, strong ETag
    R-->>C: 201 + Location + ETag
```

## PATCH /api/v1/phieu_xuat/{id}

Chỉ Q, chỉ nháp. Chi tiết được thay nguyên danh sách khi gửi, ID dòng do server cấp. Không ghi kho.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as Router / dependencies
    participant AU as AuthService
    participant NV as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant DB as PostgreSQL
    participant T as SqlAlchemyTransaction
    participant A as AuditService
    participant AR as SqlAlchemyAuditRepository
    C->>R: PATCH /api/v1/phieu_xuat/{id} + JWT
    R->>AU: current_payload(token)
    AU->>NV: get_auth_identity(subject, pwdv)
    NV->>NR: get_credentials_by_id
    NR->>DB: Read current employee and role
    break Missing/invalid/revoked JWT or missing account
        AU-->>C: 401 chua_xac_thuc + WWW-Authenticate Bearer
    end
    break Account locked or role not allowed
        R-->>C: 403
    end
    R->>R: Validate body, path and query
    break Invalid input, extra or repeated query/header
        R-->>C: 422 du_lieu_khong_hop_le
    end
    R->>S: patch_issue(id, payload, actor, If-Match, request_id)
    S->>T: __aenter__, use existing request session
    S->>P: lock_context(id)
    P->>DB: Peek immutable FK, lock request then order then issue and lines
    break Source or issue missing
        S-->>C: 404 khong_tim_thay
    end
    S->>S: Require strong If-Match, compare current resource under lock
    break Header missing / stale, weak or wildcard
        S-->>C: 428 thieu_if_match / 412 du_lieu_da_thay_doi
    end
    break Not draft or already referenced by ledger
        S-->>C: 409 trang_thai_khong_hop_le / dang_duoc_tham_chieu
    end
    opt chi_tiet supplied
        S->>P: lock_parts FOR SHARE
        P->>DB: Read active items in ascending ID
        S->>S: Validate source, types and demand, errors 404/409
        opt Lines actually changed
            S->>P: replace_lines, keep prices null
            P->>DB: DELETE old lines, INSERT replacement lines
            S->>A: append sua with snapshots
            A->>AR: append
            AR->>AR: session.add
        end
    end
    S->>T: __aexit__, session.commit flushes pending writes
    T->>DB: COMMIT, rollback on write/flush/audit failure
    S-->>R: Current resource and ETag
    R-->>C: 200 + ETag, unchanged on no-op
```

## DELETE /api/v1/phieu_xuat/{id}

Chỉ Q, chỉ nháp chưa có ledger. Audit giữ snapshot trước khi xóa.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as Router / dependencies
    participant AU as AuthService
    participant NV as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant DB as PostgreSQL
    participant T as SqlAlchemyTransaction
    participant A as AuditService
    participant AR as SqlAlchemyAuditRepository
    C->>R: DELETE /api/v1/phieu_xuat/{id} + JWT
    R->>AU: current_payload(token)
    AU->>NV: get_auth_identity(subject, pwdv)
    NV->>NR: get_credentials_by_id
    NR->>DB: Read current employee and role
    break Missing/invalid/revoked JWT or missing account
        AU-->>C: 401 chua_xac_thuc + WWW-Authenticate Bearer
    end
    break Account locked or role not allowed
        R-->>C: 403
    end
    R->>R: Validate body, path and query
    break Invalid input, extra or repeated query/header
        R-->>C: 422 du_lieu_khong_hop_le
    end
    R->>S: delete_issue(id, actor, If-Match)
    S->>T: __aenter__, use existing request session
    S->>P: lock_context(id)
    P->>DB: Peek immutable FK, lock request then order then issue and lines
    break Source or issue missing
        S-->>C: 404 khong_tim_thay
    end
    S->>S: Require strong If-Match, compare current resource under lock
    break Header missing / stale, weak or wildcard
        S-->>C: 428 thieu_if_match / 412 du_lieu_da_thay_doi
    end
    break Not draft or referenced by ledger
        S-->>C: 409 trang_thai_khong_hop_le / dang_duoc_tham_chieu
    end
    S->>P: delete_draft
    P->>DB: DELETE lines then header
    S->>A: append(CreationAudit with before/after and reason)
    A->>AR: append(entry)
    AR->>AR: session.add audit, no independent commit
    S->>T: __aexit__ success
    T->>DB: session.commit, flush pending audit then COMMIT
    break Write, audit, flush or commit failure
        T->>DB: ROLLBACK all document, stock, ledger and progress changes
        T-->>C: 409 database constraint or 500 safe error
    end
    R-->>C: 204, empty body
```

## POST /api/v1/phieu_xuat/{id}/gui

Chỉ Q. nhap → cho_duyet. Body JSON object rỗng bắt buộc. Không thay đổi tồn kho.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as Router / dependencies
    participant AU as AuthService
    participant NV as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant DB as PostgreSQL
    participant T as SqlAlchemyTransaction
    participant A as AuditService
    participant AR as SqlAlchemyAuditRepository
    C->>R: POST /api/v1/phieu_xuat/{id}/gui + JWT
    R->>AU: current_payload(token)
    AU->>NV: get_auth_identity(subject, pwdv)
    NV->>NR: get_credentials_by_id
    NR->>DB: Read current employee and role
    break Missing/invalid/revoked JWT or missing account
        AU-->>C: 401 chua_xac_thuc + WWW-Authenticate Bearer
    end
    break Account locked or role not allowed
        R-->>C: 403
    end
    R->>R: Validate body, path and query
    break Invalid input, extra or repeated query/header
        R-->>C: 422 du_lieu_khong_hop_le
    end
    R->>S: transition(id, gui, actor, If-Match, request_id, reason)
    S->>T: __aenter__, use existing request session
    S->>P: lock_context(id)
    P->>DB: Peek immutable FK, lock request then order then issue and lines
    break Source or issue missing
        S-->>C: 404 khong_tim_thay
    end
    S->>S: Require strong If-Match, compare current resource under lock
    break Header missing / stale, weak or wildcard
        S-->>C: 428 thieu_if_match / 412 du_lieu_da_thay_doi
    end
    break Current state is not nhap
        S-->>C: 409 trang_thai_khong_hop_le
    end
    S->>P: lock_parts FOR SHARE, read current source/demand
    P->>DB: Read active items and source
    S->>S: Validate allowed item types, source state and demand, 404/409 on failure
    S->>P: change_state(cho_duyet)
    P->>DB: UPDATE issue state
    S->>A: append(CreationAudit with before/after and reason)
    A->>AR: append(entry)
    AR->>AR: session.add audit, no independent commit
    S->>T: __aexit__ success
    T->>DB: session.commit, flush pending audit then COMMIT
    break Write, audit, flush or commit failure
        T->>DB: ROLLBACK all document, stock, ledger and progress changes
        T-->>C: 409 database constraint or 500 safe error
    end
    S-->>R: Updated resource, meta and ETag
    R-->>C: 200 + ETag
```

## POST /api/v1/phieu_xuat/{id}/tu_choi

Chỉ Q. cho_duyet → tu_choi. LyDoInput bắt buộc, trim lý do không rỗng và lưu audit. Không thay đổi tồn kho.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as Router / dependencies
    participant AU as AuthService
    participant NV as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant DB as PostgreSQL
    participant T as SqlAlchemyTransaction
    participant A as AuditService
    participant AR as SqlAlchemyAuditRepository
    C->>R: POST /api/v1/phieu_xuat/{id}/tu_choi + JWT
    R->>AU: current_payload(token)
    AU->>NV: get_auth_identity(subject, pwdv)
    NV->>NR: get_credentials_by_id
    NR->>DB: Read current employee and role
    break Missing/invalid/revoked JWT or missing account
        AU-->>C: 401 chua_xac_thuc + WWW-Authenticate Bearer
    end
    break Account locked or role not allowed
        R-->>C: 403
    end
    R->>R: Validate body, path and query
    break Invalid input, extra or repeated query/header
        R-->>C: 422 du_lieu_khong_hop_le
    end
    R->>S: transition(id, tu_choi, actor, If-Match, request_id, reason)
    S->>T: __aenter__, use existing request session
    S->>P: lock_context(id)
    P->>DB: Peek immutable FK, lock request then order then issue and lines
    break Source or issue missing
        S-->>C: 404 khong_tim_thay
    end
    S->>S: Require strong If-Match, compare current resource under lock
    break Header missing / stale, weak or wildcard
        S-->>C: 428 thieu_if_match / 412 du_lieu_da_thay_doi
    end
    break Current state is not cho_duyet
        S-->>C: 409 trang_thai_khong_hop_le
    end
    S->>P: change_state(tu_choi)
    P->>DB: UPDATE issue state
    S->>A: append(CreationAudit with before/after and reason)
    A->>AR: append(entry)
    AR->>AR: session.add audit, no independent commit
    S->>T: __aexit__ success
    T->>DB: session.commit, flush pending audit then COMMIT
    break Write, audit, flush or commit failure
        T->>DB: ROLLBACK all document, stock, ledger and progress changes
        T-->>C: 409 database constraint or 500 safe error
    end
    S-->>R: Updated resource, meta and ETag
    R-->>C: 200 + ETag
```

## POST /api/v1/phieu_xuat/{id}/ve_nhap

Chỉ Q. tu_choi → nhap. LyDoInput bắt buộc, trim lý do không rỗng và lưu audit. Không thay đổi tồn kho.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as Router / dependencies
    participant AU as AuthService
    participant NV as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant DB as PostgreSQL
    participant T as SqlAlchemyTransaction
    participant A as AuditService
    participant AR as SqlAlchemyAuditRepository
    C->>R: POST /api/v1/phieu_xuat/{id}/ve_nhap + JWT
    R->>AU: current_payload(token)
    AU->>NV: get_auth_identity(subject, pwdv)
    NV->>NR: get_credentials_by_id
    NR->>DB: Read current employee and role
    break Missing/invalid/revoked JWT or missing account
        AU-->>C: 401 chua_xac_thuc + WWW-Authenticate Bearer
    end
    break Account locked or role not allowed
        R-->>C: 403
    end
    R->>R: Validate body, path and query
    break Invalid input, extra or repeated query/header
        R-->>C: 422 du_lieu_khong_hop_le
    end
    R->>S: transition(id, ve_nhap, actor, If-Match, request_id, reason)
    S->>T: __aenter__, use existing request session
    S->>P: lock_context(id)
    P->>DB: Peek immutable FK, lock request then order then issue and lines
    break Source or issue missing
        S-->>C: 404 khong_tim_thay
    end
    S->>S: Require strong If-Match, compare current resource under lock
    break Header missing / stale, weak or wildcard
        S-->>C: 428 thieu_if_match / 412 du_lieu_da_thay_doi
    end
    break Current state is not tu_choi
        S-->>C: 409 trang_thai_khong_hop_le
    end
    S->>P: change_state(nhap)
    P->>DB: UPDATE issue state
    S->>A: append(CreationAudit with before/after and reason)
    A->>AR: append(entry)
    AR->>AR: session.add audit, no independent commit
    S->>T: __aexit__ success
    T->>DB: session.commit, flush pending audit then COMMIT
    break Write, audit, flush or commit failure
        T->>DB: ROLLBACK all document, stock, ledger and progress changes
        T-->>C: 409 database constraint or 500 safe error
    end
    S-->>R: Updated resource, meta and ETag
    R-->>C: 200 + ETag
```

## POST /api/v1/phieu_xuat/{id}/duyet

Chỉ Q, body {}. Được duyệt phiếu mình lập. Duyệt mới chỉ từ cho_duyet. Tồn/giá/ledger/tiến độ/audit cùng transaction. Hai yêu cầu khác nhau dùng chung mặt hàng vẫn được tuần tự hóa bằng khóa dòng MatHang.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as Router / dependencies
    participant AU as AuthService
    participant NV as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant DB as PostgreSQL
    participant T as SqlAlchemyTransaction
    participant A as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant I as SqlAlchemyInventoryRepository
    C->>R: POST /api/v1/phieu_xuat/{id}/duyet + JWT
    R->>AU: current_payload(token)
    AU->>NV: get_auth_identity(subject, pwdv)
    NV->>NR: get_credentials_by_id
    NR->>DB: Read current employee and role
    break Missing/invalid/revoked JWT or missing account
        AU-->>C: 401 chua_xac_thuc + WWW-Authenticate Bearer
    end
    break Account locked or role not allowed
        R-->>C: 403
    end
    R->>R: Validate body, path and query
    break Invalid input, extra or repeated query/header
        R-->>C: 422 du_lieu_khong_hop_le
    end
    R->>S: approve(id, actor, If-Match, request_id)
    S->>T: __aenter__
    S->>P: lock_context, lock request then order then issue/lines
    P->>DB: FOR UPDATE context, missing resource returns 404
    S->>S: Require header, missing 428, malformed/weak/wildcard 412
    alt Issue already da_duyet
        S->>P: postings(id)
        P->>DB: Read existing ledger IDs
        Note over S,DB: Strong stale ETag allowed, no state/stock/ledger/audit writes
    else First approval
        S->>S: Compare ETag 412, require cho_duyet 409
        S->>P: lock_parts(posting=true), approved_quantities
        P->>DB: MatHang FOR UPDATE in ascending ID, sum approved source quantities
        S->>S: Recheck source state, item active/type, remaining demand and BIGINT price bounds
        break Invalid source/item or quantity exceeds remaining demand
            S-->>C: 404 / 409 trang_thai_khong_hop_le, mat_hang_ngung_hoat_dong, phu_thuoc_khong_hop_le, vuot_nhu_cau
        end
        S->>P: freeze_prices(record, locked catalog prices)
        P->>DB: UPDATE line prices/totals then header total and da_duyet
        S->>I: issue_stock(lines, kind, actor_id, posted_at)
        I->>DB: Recheck locked stock equals ledger sum
        break Insufficient stock or inconsistent ledger
            I-->>S: khong_du_ton_kho with safe quantity details or conflict
            S->>T: Propagate error
            T->>DB: ROLLBACK state and prices too
            T-->>C: 409
        end
        I->>DB: INSERT negative source-unique ledger and UPDATE stock balance/time
        opt Finished goods
            S->>P: update_progress(source request, approved total, demand)
            P->>DB: UPDATE request dang_thuc_hien or hoan_thanh and completed_at
        end
        S->>A: append duyet with before/after snapshots
        A->>AR: append
        AR->>AR: session.add, deferred INSERT
    end
    S->>T: __aexit__, session.commit flushes pending audit
    T->>DB: COMMIT
    break Failure in ledger/balance/progress/audit/flush/commit
        T->>DB: ROLLBACK everything
        T-->>C: 409 constraint or 500 safe error, no ticket
    end
    S-->>R: ActionRead resource, ledger IDs and replay flag, strong ETag
    R-->>C: 200 + ETag
```

