# Module nha_cung_cap

Nguồn: [API contract v2, mục 2, 3, 5 và 14](https://drive.google.com/file/d/16hj1yTLvhQ4peRENCLjbCKhNdGy_L2Xz/view),
`infra/postgres/init.sql` và quyết định trong `.handoff/plan.md` ngày 01/11/2026.
Quyết định mới thay thế phần sửa/xóa nhà cung cấp trong contract v2: nhà cung cấp
không được sửa hoặc xóa vì phiếu nhập tham chiếu trực tiếp và không lưu bản sao thông tin.
Module chỉ cung cấp ba endpoint dưới đây. Không còn `/api/v1/suppliers`; đường dẫn cũ
trả 404. PATCH/DELETE đường dẫn chi tiết trả 405 và không ghi audit.

Lỗi nghiệp vụ, xác thực, validation và lỗi nội bộ dùng
`{error: {code, message, details}, meta: {request_id}}`. Lỗi 401 có
`WWW-Authenticate: Bearer`. Q là `quan_ly`. Admin (`quan_tri_vien`) và nhân viên nhận 403 ở cả ba endpoint.

## GET /api/v1/nha_cung_cap

```mermaid
sequenceDiagram
    actor Client
    participant Router
    participant Auth as Auth dependency / AuthService
    participant Employees as NhanVienService
    participant EmployeeRepo as SqlAlchemyNhanVienRepository
    participant Service as SupplierService
    participant Repo as SqlAlchemySupplierRepository
    participant DB as PostgreSQL
    Client->>Router: GET /api/v1/nha_cung_cap + Bearer JWT
    Router->>Auth: get_current_user_payload / require_roles
    Auth->>Auth: current_payload(token): kiểm tra chữ ký, exp, sub
    alt Thiếu JWT, JWT sai hoặc hết hạn, sub không hợp lệ
        Auth-->>Client: 401 chua_xac_thuc
    else JWT hợp lệ
        Auth->>Employees: get_auth_identity(sub, credential_version=pwdv)
        Employees->>EmployeeRepo: get_credentials_by_id(sub)
        EmployeeRepo->>DB: SELECT NhanVien JOIN VaiTro
        DB-->>Employees: Credentials và vai trò hiện tại
        alt Không có nhân viên hoặc pwdv không khớp
            Employees-->>Client: 401 chua_xac_thuc
        else Tài khoản bị khóa
            Employees-->>Client: 403 tai_khoan_bi_vo_hieu_hoa
        else Tài khoản hoạt động, token còn hiệu lực
            Employees-->>Auth: AuthIdentity
            Auth->>Auth: Lấy roles hiện tại, kiểm tra quyền Q
            alt Không có quyền Q
                Auth-->>Client: 403 khong_co_quyen
            else Có quyền Q
                Router->>Router: Validate query, từ chối trường lạ hoặc tham số lặp
                alt Query không hợp lệ
                    Router-->>Client: 422 du_lieu_khong_hop_le
                else Query hợp lệ
                    Router->>Service: list_suppliers(params, request_id)
                    Service->>Repo: list_suppliers(params)
                    Repo->>DB: SELECT COUNT với bộ lọc
                    DB-->>Repo: total
                    opt Offset nhỏ hơn total
                        Repo->>DB: SELECT với bộ lọc, ORDER BY, LIMIT/OFFSET
                        DB-->>Repo: Các nhà cung cấp
                    end
                    Repo-->>Service: RecordPage(items, total)
                    Service-->>Router: NhaCungCapListResponse
                    Router-->>Client: 200 data và meta phân trang
                end
            end
        end
    end
    Note over Router,DB: Handler chuyển lỗi chưa phân loại thành 500 loi_noi_bo, không trả SQL hoặc stack trace
```

- `page=1`, `page_size=20`; page_size từ 1 đến 100. Trang vượt phạm vi trả
  `data=[]` và total thực tế; không có kết quả thì total_pages=0.
- `q` tìm chuỗi con không phân biệt hoa thường trong `ma_ncc`, `ten_ncc`;
  `%` và `_` là ký tự thường. `tinh`, `phuong` so khớp chính xác sau trim;
  các bộ lọc kết hợp AND.
- Sort hỗ trợ `id`, `ma_ncc`, `ten_ncc` và tiền tố `-` để giảm dần;
  mặc định `id` tăng dần. ID tăng dần là tiêu chí phụ, NULL theo PostgreSQL.
- Q nhận bảy trường: `id`, `ma_ncc`, `ten_ncc`, `so_dien_thoai`,
  `dia_chi`, `phuong`, `tinh`. Meta gồm `request_id`, `page`, `page_size`,
  `total`, `total_pages`. Dữ liệu cũ được phép có `ten_ncc=null`.
- GET chỉ SELECT, không ghi audit hoặc cập nhật dữ liệu.

## GET /api/v1/nha_cung_cap/{id}

```mermaid
sequenceDiagram
    actor Client
    participant Router
    participant Auth as Auth dependency / AuthService
    participant Employees as NhanVienService
    participant EmployeeRepo as SqlAlchemyNhanVienRepository
    participant Service as SupplierService
    participant Repo as SqlAlchemySupplierRepository
    participant DB as PostgreSQL
    Client->>Router: GET /api/v1/nha_cung_cap/{id} + Bearer JWT
    Router->>Auth: get_current_user_payload / require_roles
    Auth->>Auth: current_payload(token): kiểm tra chữ ký, exp, sub
    alt Thiếu JWT, JWT sai hoặc hết hạn, sub không hợp lệ
        Auth-->>Client: 401 chua_xac_thuc
    else JWT hợp lệ
        Auth->>Employees: get_auth_identity(sub, credential_version=pwdv)
        Employees->>EmployeeRepo: get_credentials_by_id(sub)
        EmployeeRepo->>DB: SELECT NhanVien JOIN VaiTro
        DB-->>Employees: Credentials và vai trò hiện tại
        alt Không có nhân viên hoặc pwdv không khớp
            Employees-->>Client: 401 chua_xac_thuc
        else Tài khoản bị khóa
            Employees-->>Client: 403 tai_khoan_bi_vo_hieu_hoa
        else Tài khoản hoạt động, token còn hiệu lực
            Employees-->>Auth: AuthIdentity
            Auth->>Auth: Lấy roles hiện tại, kiểm tra quyền Q
            alt Không có quyền Q
                Auth-->>Client: 403 khong_co_quyen
            else Có quyền Q
                Router->>Router: Validate ID nguyên dương, không nhận query
                alt ID/query không hợp lệ
                    Router-->>Client: 422 du_lieu_khong_hop_le
                else Input hợp lệ
                    Router->>Service: get_supplier(id, request_id)
                    alt ID lớn hơn 2147483647
                        Service-->>Client: 404 khong_tim_thay
                    else ID thuộc miền INTEGER PostgreSQL
                        Service->>Repo: get_by_id(id)
                        Repo->>DB: SELECT NhaCungCap WHERE id
                        DB-->>Repo: Bản ghi hoặc không có
                        Repo-->>Service: SupplierResponse hoặc None
                        alt Không tìm thấy
                            Service-->>Client: 404 khong_tim_thay
                        else Có bản ghi
                            Service-->>Router: NhaCungCapDetailResponse
                            Router-->>Client: 200 data và meta.request_id
                        end
                    end
                end
            end
        end
    end
    Note over Router,DB: Handler chuyển lỗi chưa phân loại thành 500 loi_noi_bo, không trả SQL hoặc stack trace
```

Q nhận bảy trường như GET list, cho phép `ten_ncc=null` với dữ liệu cũ.
GET chi tiết không trả ETag, không ghi audit hoặc cập nhật dữ liệu.

## POST /api/v1/nha_cung_cap

```mermaid
sequenceDiagram
    actor Client
    participant Router
    participant Auth as Auth dependency / AuthService
    participant Employees as NhanVienService
    participant EmployeeRepo as SqlAlchemyNhanVienRepository
    participant Service as SupplierService
    participant Repo as SqlAlchemySupplierRepository
    participant Tx as SqlAlchemyTransaction
    participant AuditRepo as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    Client->>Router: POST /api/v1/nha_cung_cap + Bearer JWT + JSON
    Router->>Auth: get_current_user_payload / require_roles
    Auth->>Auth: current_payload(token): kiểm tra chữ ký, exp, sub
    alt Thiếu JWT, JWT sai hoặc hết hạn, sub không hợp lệ
        Auth-->>Client: 401 chua_xac_thuc
    else JWT hợp lệ
        Auth->>Employees: get_auth_identity(sub, credential_version=pwdv)
        Employees->>EmployeeRepo: get_credentials_by_id(sub)
        EmployeeRepo->>DB: SELECT NhanVien JOIN VaiTro
        DB-->>Employees: Credentials và vai trò hiện tại
        alt Không có nhân viên hoặc pwdv không khớp
            Employees-->>Client: 401 chua_xac_thuc
        else Tài khoản bị khóa
            Employees-->>Client: 403 tai_khoan_bi_vo_hieu_hoa
        else Tài khoản hoạt động, token còn hiệu lực
            Employees-->>Auth: AuthIdentity
            Auth->>Auth: Lấy roles hiện tại, kiểm tra quyền Q
            alt Không có quyền Q
                Auth-->>Client: 403 khong_co_quyen
            else Có quyền Q
                Router->>Router: Validate NhaCungCapCreate, không nhận query
                alt Body/query không hợp lệ
                    Router-->>Client: 422 du_lieu_khong_hop_le
                else Input hợp lệ
                    Router->>Service: create_supplier(payload, actor, request_id)
                    Service->>Tx: __aenter__ (dùng session chung với auth)
                    Service->>Repo: add(payload)
                    Repo->>DB: pg_advisory_xact_lock(20261020, 1)
                    Repo->>DB: MAX ID của NhaCungCap và audit nha_cung_cap
                    DB-->>Repo: ID lớn nhất hiện tại/lịch sử
                    alt Miền INTEGER đã cạn
                        Repo-->>Service: ConflictException
                        Service->>Tx: __aexit__ với lỗi
                        Tx->>DB: ROLLBACK
                        Service-->>Client: 409 trang_thai_khong_hop_le
                    else Còn ID
                        Repo->>DB: INSERT NhaCungCap với ID lớn nhất + 1, flush
                        alt Trùng mã (NhaCungCap_ma_ncc_key)
                            DB-->>Repo: IntegrityError
                            Repo-->>Service: DuplicateCodeException
                            Service->>Tx: __aexit__ với lỗi
                            Tx->>DB: ROLLBACK
                            Service-->>Client: 409 ma_bi_trung
                        else INSERT thành công
                            Repo-->>Service: CreatedRecord(record, snapshot)
                            Service->>AuditRepo: append(CreationAudit thao_tac=tao)
                            AuditRepo->>AuditRepo: session.add(LichSuThaoTac), chưa flush
                            Service->>Tx: __aexit__: commit cả nhà cung cấp và audit
                            Tx->>DB: Flush audit và COMMIT
                            alt Audit hoặc commit lỗi
                                Tx->>DB: ROLLBACK
                                Note over Tx,DB: IntegrityError chuyển thành ConflictException
                                Service-->>Client: 409 trang_thai_khong_hop_le hoặc 500 loi_noi_bo
                            else Commit thành công
                                Service-->>Router: NhaCungCapDetailResponse
                                Router-->>Client: 201 data, meta.request_id và Location
                            end
                        end
                    end
                end
            end
        end
    end
    Note over Router,DB: Handler chuyển lỗi chưa phân loại thành 500 loi_noi_bo, không trả SQL hoặc stack trace
```

- Chỉ Q được tạo. `ma_ncc`, `ten_ncc` bắt buộc; chuỗi được trim, tên không được
  rỗng. Mã từ `NCC-000001` đến `NCC-999999`. Trường lạ, null ở trường bắt buộc,
  mã sai định dạng và mọi query trả 422. Các trường liên hệ/địa chỉ nullable.
- `Location` là `/api/v1/nha_cung_cap/{id}`. POST không trả ETag.
- ID được cấp dưới advisory lock giữ đến commit/rollback và xét cả audit để không
  tái sử dụng ID lịch sử. Không dùng sequence để cấp ID trong repository.
- Audit `tao` chứa actor, loại `nha_cung_cap`, ID và snapshot sau tạo. Repository
  audit được inject trực tiếp qua dependency, dùng cùng session/transaction;
  không có tầng AuditService trong luồng tạo này.
- Bảng ORM là `"NhaCungCap"`; FK trực tiếp trong receiving đã cập nhật. Bảng
  receiving và các ORM nghiệp vụ còn lại chưa được chuyển đổi trong tác vụ này.
- Đây là cập nhật code cho bootstrap mới/trống; không migration, không áp dụng
  schema hay nạp seed vào database ứng dụng đang chạy.
