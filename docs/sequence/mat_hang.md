# Sequence — mat_hang

Endpoint thực tế; phần phụ thuộc BOM theo [plan đã duyệt](../../specs/use_cases/bom/PLAN.md). Không mô tả toàn bộ catalog như đã đạt UC v4. Role đọc hiện có QLK/NV, ghi QLK; không thay quyền QTV trong tác vụ BOM.

Tạo chỉ nhận hai loại thanh_pham/linh_kien; mã do Identity/trigger cấp. Thành phẩm bắt buộc có `bom.chi_tiet`, không nhận mã/trạng thái/số tồn từ client. Linh kiện không có công thức. MatHangRead giữ các field đang công khai.

GET danh mục/list dùng cache hiện tại; filter/page/sort giữ nguyên (list page 1/20, max 100). GET detail đọc DB qua BomService.item_detail để body và ETag dùng cùng snapshot; tag thành phẩm có ngữ cảnh BOM. PATCH/DELETE so sánh tag của GET mặt hàng, không dùng tag BOM. Cache của instance xử lý được publish sau commit; instance khác theo LISTEN/NOTIFY và reconciliation hiện có.

## GET /api/v1/danh_muc_mat_hang/

[PNG](assets/mat_hang/mat-hang-1.png). Quyền QLK/NV.

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router + schema
    participant A as AuthService + role dependency
    participant N as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as MatHangReader
    participant K as MatHangCache
    participant DB as PostgreSQL
    C->>R: GET /api/v1/danh_muc_mat_hang/
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
    R->>R: Schema/query validation
    alt input không hợp lệ
        R-->>C: 422
    else hợp lệ
        R->>S: danh_muc
        S->>K: snapshot, lọc/page/sort nếu là list
        alt cache unavailable
            K-->>C: 503
        else dữ liệu sẵn sàng
            K-->>S: immutable records
            S-->>R: data + meta
            R-->>C: 200
        end
    end
```

## GET /api/v1/mat_hang

[PNG](assets/mat_hang/mat-hang-2.png). Quyền QLK/NV.

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router + schema
    participant A as AuthService + role dependency
    participant N as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as MatHangReader
    participant K as MatHangCache
    participant DB as PostgreSQL
    C->>R: GET /api/v1/mat_hang
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
    R->>R: Schema/query validation
    alt input không hợp lệ
        R-->>C: 422
    else hợp lệ
        R->>S: list_mat_hang
        S->>K: snapshot, lọc/page/sort nếu là list
        alt cache unavailable
            K-->>C: 503
        else dữ liệu sẵn sàng
            K-->>S: immutable records
            S-->>R: data + meta
            R-->>C: 200
        end
    end
```

## GET /api/v1/mat_hang/{id}

[PNG](assets/mat_hang/mat-hang-3.png). Quyền QLK/NV.

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router + schema
    participant A as AuthService + role dependency
    participant N as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as MatHangReader
    participant B as SqlAlchemyBomRepository
    participant DB as PostgreSQL
    participant BS as BomService
    C->>R: GET /api/v1/mat_hang/{id}
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
    R->>R: Schema/query validation
    alt input không hợp lệ
        R-->>C: 422
    else hợp lệ
        R->>S: get_mat_hang
        S->>BS: item_detail(id)
        BS->>B: context(id)
        B->>DB: một SELECT item + version state
        DB-->>B: snapshot
        B-->>BS: detached context
        alt không tồn tại
            BS-->>C: 404
        else tồn tại
            BS-->>S: item và strong ETag
            S-->>R: data, ETag
            R-->>C: 200 + ETag
        end
    end
```

## POST /api/v1/mat_hang

[PNG](assets/mat_hang/mat-hang-4.png). Quyền QLK. UC-10/16: tạo thành phẩm và công thức cùng lúc.

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router + schema
    participant A as AuthService + role dependency
    participant N as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as MatHangService
    participant B as SqlAlchemyBomRepository
    participant I as SqlAlchemyMatHangRepository
    participant M as MatHangMutation
    participant T as SqlAlchemyTransaction
    participant K as MatHangCache
    participant AU as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    participant BS as BomService
    C->>R: POST /api/v1/mat_hang
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
    R->>R: Schema/query validation
    alt input không hợp lệ
        R-->>C: 422
    else hợp lệ
        R->>S: create_mat_hang
        S->>S: require_manager
        S->>M: scope()
        M->>K: lock + snapshot
        M->>T: transaction chung
        S->>BS: lock_catalog
        BS->>B: advisory lock
        B->>DB: pg_advisory_xact_lock
        alt không thỏa quyền / dữ liệu / trạng thái
            S-->>R: 403 / 404 / 409 / 422
        else điều kiện hợp lệ
            S->>I: add (exclude bom, không mã client)
            I->>DB: INSERT MatHang, trigger cấp mã, refresh
            opt loại thanh_pham
                S->>BS: create_initial_formula (UC-16)
                BS->>I: khóa và kiểm tra linh kiện
                BS->>B: INSERT Bom v1 + ChiTietBom
                B->>DB: flush (không commit)
                BS->>AU: audit tạo công thức
            end
            S->>AU: audit tạo mặt hàng
            AU->>AR: append
            AR->>DB: session.add, không commit
        end
        alt ghi/audit/commit lỗi
            T->>DB: ROLLBACK
            M->>K: không publish / unavailable nếu commit chưa rõ
            R-->>C: lỗi nghiệp vụ hoặc 500 an toàn
        else thành công
            M->>K: prepare snapshot
            T->>DB: COMMIT một lần
            M->>K: publish
            S-->>R: kết quả
            R-->>C: 201 + Location + ETag
        end
    end
```

## PATCH /api/v1/mat_hang/{id}

[PNG](assets/mat_hang/mat-hang-5.png). Quyền QLK. Phần UC-12/18/19 liên quan trạng thái công thức.

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router + schema
    participant A as AuthService + role dependency
    participant N as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as MatHangService
    participant B as SqlAlchemyBomRepository
    participant I as SqlAlchemyMatHangRepository
    participant M as MatHangMutation
    participant T as SqlAlchemyTransaction
    participant K as MatHangCache
    participant AU as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    participant BS as BomService
    C->>R: PATCH /api/v1/mat_hang/{id}
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
    R->>R: Schema/query validation
    alt input không hợp lệ
        R-->>C: 422
    else hợp lệ
        R->>S: patch_mat_hang
        S->>S: require_manager
        S->>M: scope()
        M->>K: lock + snapshot
        M->>T: transaction chung
        S->>BS: lock_catalog
        BS->>B: advisory lock
        B->>DB: pg_advisory_xact_lock
        S->>I: get_for_update(id)
        I->>DB: SELECT FOR UPDATE
        S->>BS: lock_item_versions + item_detail
        BS->>B: khóa versions / context
        B->>DB: đọc snapshot
        S->>S: so If-Match (428/412)
        alt không thỏa quyền / dữ liệu / trạng thái
            S-->>R: 403 / 404 / 409 / 422
        else điều kiện hợp lệ
            S->>BS: stop_for_item_in_transaction / reuse_last nếu đổi trạng thái
            BS->>B: ngừng / dùng version gần kích hoạt nhất
            B->>DB: UPDATE Bom, không sửa định mức
            BS->>I: trạng thái thành phẩm đi cùng
            I->>DB: UPDATE MatHang
            BS->>AU: audit công thức + mặt hàng nếu đổi trạng thái
            S->>I: update thuộc tính mô tả nếu có, kiểm tra tham chiếu ĐVT
            I->>DB: SELECT references / UPDATE fields
            S->>AU: audit sửa nếu có thuộc tính gửi sửa
            AU->>AR: append
            AR->>DB: session.add, không commit
        end
        alt ghi/audit/commit lỗi
            T->>DB: ROLLBACK
            M->>K: không publish / unavailable nếu commit chưa rõ
            R-->>C: lỗi nghiệp vụ hoặc 500 an toàn
        else thành công
            M->>K: prepare snapshot
            T->>DB: COMMIT một lần
            M->>K: publish
            S-->>R: kết quả
            R-->>C: 200 + ETag
        end
    end
```

## DELETE /api/v1/mat_hang/{id}

[PNG](assets/mat_hang/mat-hang-6.png). Quyền QLK. Phần UC-12/18/19 liên quan trạng thái công thức.

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router + schema
    participant A as AuthService + role dependency
    participant N as NhanVienService
    participant NR as SqlAlchemyNhanVienRepository
    participant S as MatHangService
    participant B as SqlAlchemyBomRepository
    participant I as SqlAlchemyMatHangRepository
    participant M as MatHangMutation
    participant T as SqlAlchemyTransaction
    participant K as MatHangCache
    participant AU as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    participant BS as BomService
    C->>R: DELETE /api/v1/mat_hang/{id}
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
    R->>R: Schema/query validation
    alt input không hợp lệ
        R-->>C: 422
    else hợp lệ
        R->>S: delete_mat_hang
        S->>S: require_manager
        S->>M: scope()
        M->>K: lock + snapshot
        M->>T: transaction chung
        S->>BS: lock_catalog
        BS->>B: advisory lock
        B->>DB: pg_advisory_xact_lock
        S->>I: get_for_update(id)
        I->>DB: SELECT FOR UPDATE
        S->>BS: lock_item_versions + item_detail
        BS->>B: khóa versions / context
        B->>DB: đọc snapshot
        S->>S: so If-Match (428/412)
        alt không thỏa quyền / dữ liệu / trạng thái
            S-->>R: 403 / 404 / 409 / 422
        else điều kiện hợp lệ
            S->>BS: stop_for_item_in_transaction / reuse_last nếu đổi trạng thái
            BS->>B: ngừng / dùng version gần kích hoạt nhất
            B->>DB: UPDATE Bom, không sửa định mức
            BS->>I: trạng thái thành phẩm đi cùng
            I->>DB: UPDATE MatHang
            BS->>AU: audit công thức + mặt hàng nếu đổi trạng thái
            AU->>AR: append
            AR->>DB: session.add, không commit
        end
        alt ghi/audit/commit lỗi
            T->>DB: ROLLBACK
            M->>K: không publish / unavailable nếu commit chưa rõ
            R-->>C: lỗi nghiệp vụ hoặc 500 an toàn
        else thành công
            M->>K: prepare snapshot
            T->>DB: COMMIT một lần
            M->>K: publish
            S-->>R: kết quả
            R-->>C: 204 rỗng
        end
    end
```
