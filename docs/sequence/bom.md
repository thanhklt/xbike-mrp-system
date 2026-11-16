# Sequence — bom

Backend UC-15–19 theo [spec](../../specs/use_cases/bom/README.md). Chỉ mô tả endpoint đã triển khai. `POST /api/v1/bom` cũ đã gỡ (405); v1 chỉ tạo cùng thành phẩm tại UC-10/16, xem [mat_hang](mat_hang.md).

QLK=`quan_ly`, NV=`nhan_vien`; QTV không truy cập BOM. Auth kiểm tra account/role từ DB mỗi request theo cơ chế hiện tại. Không refactor auth hoặc sản xuất v4 trong tác vụ này.

GET list mặc định page=1/page_size=20 (max 100), lọc AND theo mat_hang_id/version/is_active; sort whitelist v4, ID là khóa phụ. GET detail trả strong ETag bao gồm version được đọc và trạng thái hiện tại của công thức; dùng tag cùng ID cho ba mutation. Cây cấu trúc chỉ một cấp, không ETag dùng cho mutation.

Tất cả mutation dùng một session/transaction chung cho MatHang, Bom, ChiTietBom và audit; thứ tự cache lock → advisory lock → item → version. Cache publish sau commit, lỗi commit không chắc chắn làm cache unavailable. Không đổi tồn/giữ hàng/ledger/yêu cầu đã chốt.

Rà soát 14/11/2026 theo T04/T06/T07/T09: `MatHangMutation.scope()` dùng
`@asynccontextmanager` để các service vào/ra transaction đúng bằng `async with`.
Dependency `get_bom_if_match` chỉ gom mọi giá trị header, kể cả các header vật lý
lặp tên, rồi chuyển xuống service. `verify_if_match` vẫn so sánh sau khi khóa và đọc
lại resource: thiếu/rỗng 428, stale/weak/wildcard/nhiều giá trị 412. Không lấy riêng
header đầu tiên; không đổi cách xử lý header của các module khác.

## GET /api/v1/bom

UC-15; quyền QLK / NV. Đầu vào: BomListQuery; reject duplicate query / body. [PNG](assets/bom/bom-1.png).

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router + schema
    participant A as AuthService + role dependency
    participant N as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as BomService
    participant B as SqlAlchemyBomRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/bom
    R->>A: get_current_user_payload / require_roles
    A->>N: get_auth_identity (trạng thái, role từ DB, pwdv)
    N->>NR: get_credentials_by_id
    NR->>DB: SELECT NhanVien + VaiTro
    DB-->>NR: credentials
    NR-->>N: identity
    N-->>A: identity
    alt token thiếu / sai / hết hạn / credential cũ
        A-->>C: 401 + WWW-Authenticate
    else tài khoản khóa / role không được phép
        A-->>C: 403
    else hợp lệ
        A-->>R: actor
    end
    R->>R: Validate path/query/body
    alt input không hợp lệ
        R-->>C: 422, error + meta.request_id
    else input hợp lệ
        R->>S: list_bom(actor, dữ liệu, request_id nếu có)
        S->>S: Guard quyền nghiệp vụ
        S->>B: COUNT + SELECT Bom/ChiTietBom, EXISTS YeuCauSanXuat
        B->>DB: SELECT, không ghi
        DB-->>B: snapshot / page
        B-->>S: detached DTO
        alt không tìm thấy detail
            S-->>C: 404
        else thành công
            S-->>R: data + meta
            R-->>C: 200
        end
    end
```

## GET /api/v1/bom/{id}

UC-15; quyền QLK / NV. Đầu vào: ID positif; không query/body. [PNG](assets/bom/bom-2.png).

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router + schema
    participant A as AuthService + role dependency
    participant N as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as BomService
    participant B as SqlAlchemyBomRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/bom/{id}
    R->>A: get_current_user_payload / require_roles
    A->>N: get_auth_identity (trạng thái, role từ DB, pwdv)
    N->>NR: get_credentials_by_id
    NR->>DB: SELECT NhanVien + VaiTro
    DB-->>NR: credentials
    NR-->>N: identity
    N-->>A: identity
    alt token thiếu / sai / hết hạn / credential cũ
        A-->>C: 401 + WWW-Authenticate
    else tài khoản khóa / role không được phép
        A-->>C: 403
    else hợp lệ
        A-->>R: actor
    end
    R->>R: Validate path/query/body
    alt input không hợp lệ
        R-->>C: 422, error + meta.request_id
    else input hợp lệ
        R->>S: get_bom(actor, dữ liệu, request_id nếu có)
        S->>S: Guard quyền nghiệp vụ
        S->>B: Snapshot version + trạng thái MatHang/Bom + định mức
        B->>DB: SELECT, không ghi
        DB-->>B: snapshot / page
        B-->>S: detached DTO
        alt không tìm thấy detail
            S-->>C: 404
        else thành công
            S-->>R: data + meta và strong ETag
            R-->>C: 200
        end
    end
```

## GET /api/v1/bom/{id}/cau_truc

UC-15; quyền QLK / NV. Đầu vào: ID positif; không query/body. [PNG](assets/bom/bom-3.png).

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router + schema
    participant A as AuthService + role dependency
    participant N as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as BomService
    participant B as SqlAlchemyBomRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/bom/{id}/cau_truc
    R->>A: get_current_user_payload / require_roles
    A->>N: get_auth_identity (trạng thái, role từ DB, pwdv)
    N->>NR: get_credentials_by_id
    NR->>DB: SELECT NhanVien + VaiTro
    DB-->>NR: credentials
    NR-->>N: identity
    N-->>A: identity
    alt token thiếu / sai / hết hạn / credential cũ
        A-->>C: 401 + WWW-Authenticate
    else tài khoản khóa / role không được phép
        A-->>C: 403
    else hợp lệ
        A-->>R: actor
    end
    R->>R: Validate path/query/body
    alt input không hợp lệ
        R-->>C: 422, error + meta.request_id
    else input hợp lệ
        R->>S: get_cau_truc(actor, dữ liệu, request_id nếu có)
        S->>S: Guard quyền nghiệp vụ
        S->>B: Snapshot của đúng version, chỉ linh kiện lá
        B->>DB: SELECT, không ghi
        DB-->>B: snapshot / page
        B-->>S: detached DTO
        alt không tìm thấy detail
            S-->>C: 404
        else thành công
            S-->>R: data + meta
            R-->>C: 200
        end
    end
```

## POST /api/v1/bom/{id}/phien_ban

UC-17; quyền QLK. Đầu vào: BomFormula; If-Match của GET cùng ID. [PNG](assets/bom/bom-4.png).

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router + schema
    participant A as AuthService + role dependency
    participant N as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as BomService
    participant B as SqlAlchemyBomRepository
    participant I as SqlAlchemyMatHangRepository
    participant M as MatHangMutation
    participant T as SqlAlchemyTransaction
    participant K as MatHangCache
    participant AU as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    C->>R: POST /api/v1/bom/{id}/phien_ban
    R->>A: get_current_user_payload / require_roles
    A->>N: get_auth_identity (trạng thái, role từ DB, pwdv)
    N->>NR: get_credentials_by_id
    NR->>DB: SELECT NhanVien + VaiTro
    DB-->>NR: credentials
    NR-->>N: identity
    N-->>A: identity
    alt token thiếu / sai / hết hạn / credential cũ
        A-->>C: 401 + WWW-Authenticate
    else tài khoản khóa / role không được phép
        A-->>C: 403
    else hợp lệ
        A-->>R: actor
    end
    R->>R: get_bom_if_match, preserve all header values
    R->>R: Validate path/query/body
    alt input không hợp lệ
        R-->>C: 422, error + meta.request_id
    else input hợp lệ
        R->>S: create_version(id, formula, actor, if_match, request_id)
        S->>S: Guard quyền nghiệp vụ
        S->>M: scope() via asynccontextmanager
        M->>K: acquire lock, snapshot
        M->>T: transaction caller
        S->>B: advisory lock, bom_ref(id)
        B->>DB: pg_advisory_xact_lock, SELECT mat_hang_id + linh kiện
        S->>I: lock_items(thành phẩm + linh kiện, id tăng dần)
        I->>DB: SELECT MatHang ORDER BY id FOR UPDATE
        S->>B: lock_versions, đọc lại snapshot
        B->>DB: SELECT FOR UPDATE / context
        alt resource không tồn tại
            S-->>R: 404
        else thiếu / stale / weak / wildcard / multiple If-Match
            S-->>R: 428 / 412
        else không hợp lệ về trạng thái / linh kiện
            S-->>R: 409 / 404 / 422
        else điều kiện hợp lệ
            S->>B: Đóng active cũ, INSERT version và định mức
            B->>DB: UPDATE Bom active, INSERT Bom + ChiTietBom
            S->>I: cập nhật trạng thái thành phẩm
            I->>DB: UPDATE MatHang
            S->>AU: append snapshot trước/sau
            AU->>AR: append
            AR->>DB: session.add LichSuThaoTac (chưa commit)
        end
        alt có lỗi validate / ghi / audit / commit
            T->>DB: ROLLBACK
            M->>K: không publish, unavailable nếu commit không rõ
            R-->>C: lỗi nghiệp vụ hoặc 500 an toàn
        else thành công
            M->>K: prepare snapshot
            T->>DB: COMMIT một lần (flush audit)
            M->>K: publish sau commit
            S-->>R: data + meta, ETag sau thay đổi
            R-->>C: 201 + Location + ETag
        end
    end
```

## POST /api/v1/bom/{id}/kich_hoat

UC-18; quyền QLK. Đầu vào: Body {} bắt buộc; If-Match của GET cùng ID. [PNG](assets/bom/bom-5.png).

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router + schema
    participant A as AuthService + role dependency
    participant N as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as BomService
    participant B as SqlAlchemyBomRepository
    participant I as SqlAlchemyMatHangRepository
    participant M as MatHangMutation
    participant T as SqlAlchemyTransaction
    participant K as MatHangCache
    participant AU as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    C->>R: POST /api/v1/bom/{id}/kich_hoat
    R->>A: get_current_user_payload / require_roles
    A->>N: get_auth_identity (trạng thái, role từ DB, pwdv)
    N->>NR: get_credentials_by_id
    NR->>DB: SELECT NhanVien + VaiTro
    DB-->>NR: credentials
    NR-->>N: identity
    N-->>A: identity
    alt token thiếu / sai / hết hạn / credential cũ
        A-->>C: 401 + WWW-Authenticate
    else tài khoản khóa / role không được phép
        A-->>C: 403
    else hợp lệ
        A-->>R: actor
    end
    R->>R: get_bom_if_match, preserve all header values
    R->>R: Validate path/query/body
    alt input không hợp lệ
        R-->>C: 422, error + meta.request_id
    else input hợp lệ
        R->>S: activate_bom(id, actor, if_match, request_id)
        S->>S: Guard quyền nghiệp vụ
        S->>M: scope() via asynccontextmanager
        M->>K: acquire lock, snapshot
        M->>T: transaction caller
        S->>B: advisory lock, bom_ref(id)
        B->>DB: pg_advisory_xact_lock, SELECT mat_hang_id + linh kiện
        S->>I: lock_items(thành phẩm + linh kiện, id tăng dần)
        I->>DB: SELECT MatHang ORDER BY id FOR UPDATE
        S->>B: lock_versions, đọc lại snapshot
        B->>DB: SELECT FOR UPDATE / context
        alt resource không tồn tại
            S-->>R: 404
        else thiếu / stale / weak / wildcard / multiple If-Match
            S-->>R: 428 / 412
        else không hợp lệ về trạng thái / linh kiện
            S-->>R: 409 / 404 / 422
        else điều kiện hợp lệ
            S->>B: Đóng active cũ, kích hoạt version đích, clock_timestamp, MatHang active
            B->>DB: ghi version / định mức trong transaction
            S->>I: cập nhật trạng thái thành phẩm
            I->>DB: UPDATE MatHang
            S->>AU: append snapshot trước/sau
            AU->>AR: append
            AR->>DB: session.add LichSuThaoTac (chưa commit)
        end
        alt có lỗi validate / ghi / audit / commit
            T->>DB: ROLLBACK
            M->>K: không publish, unavailable nếu commit không rõ
            R-->>C: lỗi nghiệp vụ hoặc 500 an toàn
        else thành công
            M->>K: prepare snapshot
            T->>DB: COMMIT một lần (flush audit)
            M->>K: publish sau commit
            S-->>R: data + meta, ETag sau thay đổi
            R-->>C: 200 + ETag
        end
    end
```

## DELETE /api/v1/bom/{id}

UC-19; quyền QLK. Đầu vào: Không query/body; If-Match của GET cùng ID. [PNG](assets/bom/bom-6.png).

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router + schema
    participant A as AuthService + role dependency
    participant N as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as BomService
    participant B as SqlAlchemyBomRepository
    participant I as SqlAlchemyMatHangRepository
    participant M as MatHangMutation
    participant T as SqlAlchemyTransaction
    participant K as MatHangCache
    participant AU as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    C->>R: DELETE /api/v1/bom/{id}
    R->>A: get_current_user_payload / require_roles
    A->>N: get_auth_identity (trạng thái, role từ DB, pwdv)
    N->>NR: get_credentials_by_id
    NR->>DB: SELECT NhanVien + VaiTro
    DB-->>NR: credentials
    NR-->>N: identity
    N-->>A: identity
    alt token thiếu / sai / hết hạn / credential cũ
        A-->>C: 401 + WWW-Authenticate
    else tài khoản khóa / role không được phép
        A-->>C: 403
    else hợp lệ
        A-->>R: actor
    end
    R->>R: get_bom_if_match, preserve all header values
    R->>R: Validate path/query/body
    alt input không hợp lệ
        R-->>C: 422, error + meta.request_id
    else input hợp lệ
        R->>S: delete_bom(id, actor, if_match)
        S->>S: Guard quyền nghiệp vụ
        S->>M: scope() via asynccontextmanager
        M->>K: acquire lock, snapshot
        M->>T: transaction caller
        S->>B: advisory lock, bom_ref(id)
        B->>DB: pg_advisory_xact_lock, SELECT mat_hang_id + linh kiện
        S->>I: lock_items(thành phẩm + linh kiện, id tăng dần)
        I->>DB: SELECT MatHang ORDER BY id FOR UPDATE
        S->>B: lock_versions, đọc lại snapshot
        B->>DB: SELECT FOR UPDATE / context
        alt resource không tồn tại
            S-->>R: 404
        else thiếu / stale / weak / wildcard / multiple If-Match
            S-->>R: 428 / 412
        else không hợp lệ về trạng thái / linh kiện
            S-->>R: 409 / 404 / 422
        else điều kiện hợp lệ
            S->>B: deactivate version, không DELETE
            B->>DB: UPDATE Bom is_active=false, không sửa định mức
            S->>I: cập nhật trạng thái thành phẩm
            I->>DB: UPDATE MatHang
            S->>AU: append snapshot trước/sau
            AU->>AR: append
            AR->>DB: session.add LichSuThaoTac (chưa commit)
        end
        alt có lỗi validate / ghi / audit / commit
            T->>DB: ROLLBACK
            M->>K: không publish, unavailable nếu commit không rõ
            R-->>C: lỗi nghiệp vụ hoặc 500 an toàn
        else thành công
            M->>K: prepare snapshot
            T->>DB: COMMIT một lần (flush audit)
            M->>K: publish sau commit
            S-->>R: không payload
            R-->>C: 204 rỗng
        end
    end
```
