# Sequence — nha_cung_cap

Đối chiếu code ngày 17/11/2026 theo [spec Catalog](../../specs/use_cases/catalog/README.md)
và [plan đã duyệt](../../specs/use_cases/catalog/PLAN.md). QTV = quan_tri_vien,
QLK = quan_ly, NV = nhan_vien. Chỉ bốn endpoint dưới đây, không có DELETE.

GET cho QTV/QLK, ghi chỉ QLK; service kiểm tra quyền lại trước truy cập dữ liệu.
Auth đọc vai trò/trạng thái hiện tại từ DB, không tin role JWT. Token thiếu/sai/hết
hạn/thu hồi trả 401 + WWW-Authenticate; tài khoản khóa hoặc sai quyền trả 403.
Các mũi tên HTTP lỗi là response qua exception handler, repository không xử lý HTTP.

## GET /api/v1/nha_cung_cap

[PNG](assets/nha_cung_cap/nha-cung-cap-1.png). UC-13.
Query mặc định page=1/page_size=20, tối đa 100; sort id/ma_ncc/ten_ncc và tiền tố `-`.
ID ASC là khóa phụ. q chỉ tìm literal mã/tên, không phân biệt hoa/thường;
tinh/phuong tìm một phần, không phân biệt hoa/thường và dấu tiếng Việt theo UC-13
R6/AC-6 đã duyệt 17/11/2026, hỗ trợ Unicode dựng sẵn/tổ hợp. Query bỏ whitespace
ngoài; `%`, `_`, `/` được escape để tìm literal. Chỉ chuẩn hóa predicate, giữ nguyên
địa chỉ trong DB/response. Không cần extension hoặc thay đổi schema.
Các bộ lọc kết hợp AND; blank filter không áp dụng; phuong được dùng riêng.
Không ghi dữ liệu/audit, không yêu cầu If-Match. COUNT và trang là hai truy vấn.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router + Query schema
    participant A as AuthService / NhanVienService
    participant N as SqlAlchemyNhanVienRepository
    participant S as SupplierService
    participant P as SqlAlchemySupplierRepository
    participant DB as PostgreSQL
    C->>R: GET + JWT + query
    R->>A: Xác thực và require_roles QTV/QLK
    A->>N: get_credentials_by_id
    N->>DB: SELECT NhanVien + VaiTro
    alt Token/tài khoản/quyền không hợp lệ
        A-->>C: 401 hoặc 403
    else Được phép
        R->>R: Cấm body, query lạ/lặp, validate page/sort
        alt Input sai
            R-->>C: 422
        else Hợp lệ
            R->>S: list_suppliers(params, actor, request_id)
            S->>S: require_supplier_role
            S->>P: list_suppliers(params)
            P->>P: Tỉnh/phường contains literal, bỏ dấu và hoa/thường
            P->>DB: COUNT, AND q/tỉnh/phường
            opt Trang còn dữ liệu
                P->>DB: SELECT, AND filters, ORDER BY, LIMIT/OFFSET
            end
            P-->>S: RecordPage
            S-->>R: data + meta phân trang/request_id
            R-->>C: 200, có thể danh sách rỗng
        end
    end
    Note over R,DB: Lỗi nội bộ trả 500 an toàn, không lộ SQL/secret
```

## GET /api/v1/nha_cung_cap/{id}

[PNG](assets/nha_cung_cap/nha-cung-cap-2.png). UC-13. ID dương, không body/query.
Trả strong ETag từ canonical JSON của NhaCungCapRead, không gồm request_id.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router + Path schema
    participant A as AuthService / NhanVienService
    participant N as SqlAlchemyNhanVienRepository
    participant S as SupplierService
    participant P as SqlAlchemySupplierRepository
    participant DB as PostgreSQL
    C->>R: GET detail + JWT
    R->>A: Xác thực và require_roles QTV/QLK
    A->>N: get_credentials_by_id
    N->>DB: SELECT NhanVien + VaiTro
    alt Token/tài khoản/quyền không hợp lệ
        A-->>C: 401 hoặc 403
    else Được phép
        R->>R: Validate ID, cấm body/query
        alt Input sai
            R-->>C: 422
        else Hợp lệ
            R->>S: get_supplier(id, actor, request_id)
            S->>S: Guard và kiểm tra dải ID
            opt ID trong dải INTEGER
                S->>P: get_by_id
                P->>DB: SELECT NhaCungCap
                P-->>S: SupplierResponse hoặc None
            end
            alt Không tồn tại/vượt dải
                S-->>C: 404
            else Có NCC
                S->>S: NhaCungCapRead và supplier_etag
                S-->>R: detail + strong ETag
                R-->>C: 200 + ETag
            end
        end
    end
```

## POST /api/v1/nha_cung_cap

[PNG](assets/nha_cung_cap/nha-cung-cap-3.png). UC-14. Bắt buộc đủ năm chuỗi
ten_ncc/so_dien_thoai/dia_chi/phuong/tinh không null/trắng, lưu nguyên văn.
Không nhận id/ma_ncc/created_at/field lạ; không tự kiểm tra địa giới hoặc định dạng
điện thoại. IDENTITY và trigger cấp mã NCC-NNNNNN, không dùng MAX ID/advisory lock.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router + NhaCungCapCreate
    participant A as AuthService / NhanVienService
    participant N as SqlAlchemyNhanVienRepository
    participant S as SupplierService
    participant P as SqlAlchemySupplierRepository
    participant AU as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: POST + JWT + năm field
    R->>A: Xác thực và require_roles QLK
    A->>N: get_credentials_by_id
    N->>DB: SELECT NhanVien + VaiTro
    alt Token/tài khoản/quyền không hợp lệ
        A-->>C: 401 hoặc 403
    else Được phép
        R->>R: Validate body, cấm query
        alt Input sai
            R-->>C: 422
        else Hợp lệ
            R->>S: create_supplier(payload, actor, request_id)
            S->>S: Guard QLK
            S->>T: Vào transaction dùng chung session
            S->>P: add(payload)
            P->>DB: INSERT, Identity + trigger cấp mã, flush/refresh
            P-->>S: CreatedRecord và snapshot thật
            S->>AU: append(tao, actor, snapshot)
            AU->>AR: append
            AR->>DB: session.add LichSuThaoTac, chưa commit
            alt Hết dải mã hoặc vi phạm ràng buộc
                T->>DB: ROLLBACK
                S-->>C: 409
            else Lỗi ghi/audit/commit
                T->>DB: ROLLBACK
                R-->>C: 500 an toàn
            else Thành công
                T->>DB: Flush audit + COMMIT một lần
                S-->>R: detail + supplier_etag
                R-->>C: 201 + Location + ETag
            end
        end
    end
```

## PATCH /api/v1/nha_cung_cap/{id}

[PNG](assets/nha_cung_cap/nha-cung-cap-4.png). UC-44. Chỉ sửa từng phần năm field
thông tin, field vắng giữ nguyên. Explicit null/trắng hoặc mã/field lạ trả 422.
`{}` và giá trị không đổi là no-op sau kiểm tra If-Match: không UPDATE/audit.
Thiếu/blank tag trả 428; tag cũ/weak/wildcard/nhiều validator trả 412, kể cả no-op.
So sánh dưới FOR UPDATE; hai session cùng tag chỉ một thay đổi thắng.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router + NhaCungCapPatch
    participant A as AuthService / NhanVienService
    participant N as SqlAlchemyNhanVienRepository
    participant S as SupplierService
    participant P as SqlAlchemySupplierRepository
    participant AU as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: PATCH + JWT + If-Match + body
    R->>A: Xác thực và require_roles QLK
    A->>N: get_credentials_by_id
    N->>DB: SELECT NhanVien + VaiTro
    alt Token/tài khoản/quyền không hợp lệ
        A-->>C: 401 hoặc 403
    else Được phép
        R->>R: Validate ID/body, cấm query
        alt Input sai
            R-->>C: 422
        else Hợp lệ
            R->>S: patch_supplier(id, payload, actor, tag, request_id)
            S->>S: Guard QLK và dải ID
            S->>T: Transaction chung
            S->>P: get_for_update(id)
            P->>DB: SELECT NhaCungCap FOR UPDATE
            alt Không tồn tại/vượt dải
                S-->>C: 404
            else Thiếu/blank If-Match
                S-->>C: 428
            else Validator không khớp strong tag hiện tại
                S-->>C: 412
            else Hợp lệ
                S->>S: So giá trị gửi với bản ghi đã khóa
                opt Có thay đổi thực tế
                    S->>P: update(values)
                    P->>DB: UPDATE, flush/refresh
                    S->>AU: append sua, snapshot trước/sau
                    AU->>AR: append
                    AR->>DB: session.add LichSuThaoTac
                end
                alt Ghi/audit/commit lỗi
                    T->>DB: ROLLBACK
                    R-->>C: 409 ràng buộc hoặc 500 an toàn
                else Thành công hoặc no-op
                    T->>DB: COMMIT một lần
                    S-->>R: detail + ETag hiện tại
                    R-->>C: 200 + ETag
                end
            end
        end
    end
    Note over S,DB: Không sửa phiếu nhập, tồn hay ledger
```

Phiếu nhập đọc thông tin NCC hiện tại qua quan hệ chỉ đọc, không lưu snapshot NCC.
Sửa NCC làm representation/ETag phiếu nhập đổi; client cần GET lại trước khi ghi.
Luồng audit: SupplierService → AuditService → SqlAlchemyAuditRepository → PostgreSQL,
trong cùng transaction với tạo/sửa NCC. Không có commit riêng trong audit/repository.
