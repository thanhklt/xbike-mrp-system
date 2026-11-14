# Sequence — mat_hang

Đối chiếu code ngày 14/11/2026 theo [spec Catalog](../../specs/use_cases/catalog/README.md), [plan Catalog](../../specs/use_cases/catalog/PLAN.md) và phần BOM đã có. Đọc QTV/QLK/NV, ghi chỉ QLK; service kiểm tra lại quyền trước I/O. Frontend và E2E sản xuất/duyệt giá xuất chưa thuộc lần kiểm chứng này.

Tạo chỉ nhận hai loại thanh_pham/linh_kien; mã do Identity/trigger cấp. Thành phẩm bắt buộc có `bom.chi_tiet`, không nhận mã/trạng thái/số tồn từ client. Linh kiện không có công thức. MatHangRead trả ba số chỉ đọc: so_luong_ton, so_luong_dang_giu, so_luong_con_dung = tồn - giữ.

GET danh mục/list dùng cache hiện tại; list page 1/20, max 100, sort id/ma_mat_hang/ten_mat_hang/don_gia và tiền tố `-`, ID ASC khi giá trị bằng nhau. Query DTO cấm tham số lạ/lặp; mọi GET/DELETE cấm body, detail/write cấm query. q là literal substring mã/tên không phân biệt hoa/thường, không tìm SKU; AND các filter. is_active chỉ áp dụng TP, kết hợp loại LK trả 422. GET detail đọc DB qua BomService.item_detail để body và ETag dùng cùng snapshot; tag TP có ngữ cảnh BOM. PATCH/DELETE dùng tag GET mặt hàng, không dùng tag BOM. Thiếu/blank 428, cũ/weak/wildcard/nhiều tag 412. Cache publish sau commit, no-op không prepare/publish; instance khác theo LISTEN/NOTIFY và reconciliation hiện có.

SKU chỉ đổi khi không có tham chiếu hoặc tồn; ĐVT không đổi khi đã có công thức/chứng từ. Mã/loại/số dư bất biến. PATCH không đổi giá trị trả 200 cùng tag, không UPDATE/audit/publish. Ngừng TP đã ngừng với tag hiện tại cũng không ghi lại. Source audit: MatHangService/BomService → AuditService → SqlAlchemyAuditRepository, cùng transaction. UPDATE refresh cột tồn tính toán trước khi dựng DTO để tránh async lazy I/O.

## GET /api/v1/danh_muc_mat_hang/

[PNG](assets/mat_hang/mat-hang-1.png). UC-09, quyền QTV/QLK/NV.

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
        R->>S: danh_muc(actor)
        S->>S: Guard QTV/QLK/NV
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

[PNG](assets/mat_hang/mat-hang-2.png). UC-09, quyền QTV/QLK/NV.

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
        R->>S: list_mat_hang(params, actor)
        S->>S: Guard, is_active chi TP (LK + active tra 422)
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
            opt Co thay doi thuc te
                M->>K: prepare snapshot
            end
            T->>DB: COMMIT một lần
            opt Co snapshot moi
                M->>K: publish
            end
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
        S->>I: get_references neu doi SKU / don_vi_tinh
        I->>DB: SELECT BOM/docs/stock references
        S->>S: Guard SKU refs/tTon, unit refs (409), diff fields
        alt không thỏa quyền / dữ liệu / trạng thái
            S-->>R: 403 / 404 / 409 / 422
        else điều kiện hợp lệ
            Note over S,DB: No-op khong UPDATE/audit/publish, van verify tag
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
            opt Co thay doi thuc te
                M->>K: prepare snapshot
            end
            T->>DB: COMMIT một lần
            opt Co snapshot moi
                M->>K: publish
            end
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
            Note over S,DB: No-op khong UPDATE/audit/publish, van verify tag
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
            opt Co thay doi thuc te
                M->>K: prepare snapshot
            end
            T->>DB: COMMIT một lần
            opt Co snapshot moi
                M->>K: publish
            end
            S-->>R: kết quả
            R-->>C: 204 rỗng
        end
    end
```
