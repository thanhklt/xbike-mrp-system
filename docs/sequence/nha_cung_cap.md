# Module nha_cung_cap

Nguồn: [API contract v2, mục 2, 3, 5 và 14](https://drive.google.com/file/d/16hj1yTLvhQ4peRENCLjbCKhNdGy_L2Xz/view).
Hai GET và POST/PATCH/DELETE tiếng Việt được triển khai theo contract v2. Dev xác nhận giữ
module `nha_cung_cap`, cho GET trả `ten_ncc=null` với dữ liệu cũ, giữ SQL hiện tại và cấp ID
tại backend dưới khóa. DELETE dùng audit `xoa_nhap` kèm snapshot trước khi xóa.

## GET /api/v1/nha_cung_cap

```mermaid
sequenceDiagram
    actor Client
    participant Router
    participant Auth as Auth dependency / AuthService
    participant AuthRepo as SqlAlchemyAuthRepository
    participant Service as SupplierService
    participant Repo as SqlAlchemySupplierRepository
    participant DB as PostgreSQL
    Client->>Router: GET /api/v1/nha_cung_cap + Bearer JWT
    Router->>Auth: get_current_user_payload / require_roles
    Auth->>Auth: Kiểm tra chữ ký, exp, sub
    alt Thiếu, sai hoặc hết hạn JWT
        Auth-->>Client: 401 chua_xac_thuc + WWW-Authenticate
    else JWT hợp lệ
        Auth->>AuthRepo: get_by_id(sub)
        AuthRepo->>DB: SELECT nhan_vien và vai_tro
        DB-->>Auth: Tài khoản, trạng thái, vai trò, hash
        alt Tài khoản không tồn tại hoặc pwdv không khớp
            Auth-->>Client: 401 chua_xac_thuc
        else Tài khoản bị khóa hoặc không có quyền A/Q
            Auth-->>Client: 403 tai_khoan_bi_vo_hieu_hoa / khong_co_quyen
        else Tài khoản hoạt động và có quyền A/Q
            Router->>Router: Validate query, từ chối trường lạ hoặc lặp
            alt Query không hợp lệ
                Router-->>Client: 422 du_lieu_khong_hop_le
            else Query hợp lệ
                Router->>Service: list_suppliers(params, request_id)
                Service->>Repo: list_suppliers(params)
                Repo->>DB: SELECT COUNT với bộ lọc
                DB-->>Repo: total
                opt Offset nhỏ hơn total
                    Repo->>DB: SELECT với bộ lọc, ORDER BY trường whitelist và id, LIMIT/OFFSET
                    DB-->>Repo: Các nhà cung cấp
                end
                Repo-->>Service: RecordPage(items, total)
                Service-->>Router: data và meta phân trang
                Router-->>Client: 200 NhaCungCapListResponse
            end
        end
    end
    Note over Router,DB: Lỗi chưa phân loại được handler chuyển thành 500 loi_noi_bo, không trả SQL/stack trace
```

- `page=1`, `page_size=20`, giới hạn page_size từ 1 đến 100.
- `q` tìm chuỗi con không phân biệt hoa thường trong mã/tên. `%`, `_` được tìm như ký tự thường.
- `tinh`, `phuong` so khớp chính xác sau trim, kết hợp AND với `q`.
- Sort: `id`, `ma_ncc`, `ten_ncc`, thêm `-` để giảm dần. Mặc định `id` tăng dần;
  khi trùng giá trị, ID tăng dần làm tiêu chí phụ. NULL sắp theo mặc định PostgreSQL.
- Không hỗ trợ query khác hoặc cùng tham số xuất hiện nhiều lần: 422.
- Trang vượt phạm vi trả `data=[]` nhưng giữ total thực tế. Không có kết quả: total_pages=0.
- A và Q nhận cùng bảy trường: id, ma_ncc, ten_ncc, so_dien_thoai, dia_chi, phuong, tinh.
- GET chỉ SELECT, không ghi audit, không cập nhật nhà cung cấp, chứng từ hay tồn kho.

## GET /api/v1/nha_cung_cap/{id}

```mermaid
sequenceDiagram
    actor Client
    participant Router
    participant Auth as Auth dependency / AuthService
    participant AuthRepo as SqlAlchemyAuthRepository
    participant Service as SupplierService
    participant Repo as SqlAlchemySupplierRepository
    participant DB as PostgreSQL
    Client->>Router: GET /api/v1/nha_cung_cap/{id} + Bearer JWT
    Router->>Auth: Kiểm tra JWT
    alt Thiếu, sai hoặc hết hạn JWT
        Auth-->>Client: 401 chua_xac_thuc
    else JWT hợp lệ
        Auth->>AuthRepo: get_by_id(sub)
        AuthRepo->>DB: SELECT tài khoản và vai trò hiện tại
        DB-->>Auth: Tài khoản, trạng thái, hash, vai trò
        alt Tài khoản bị xóa hoặc token đã bị thu hồi
            Auth-->>Client: 401 chua_xac_thuc
        else Tài khoản khóa hoặc không có quyền A/Q
            Auth-->>Client: 403
        else Có quyền A/Q
            Router->>Router: Validate ID nguyên dương, không nhận query
            alt ID/query sai
                Router-->>Client: 422 du_lieu_khong_hop_le
            else Input hợp lệ
                Router->>Service: get_supplier(id, request_id)
                alt ID vượt miền INTEGER PostgreSQL
                    Service-->>Client: 404 khong_tim_thay
                else ID trong miền INTEGER
                    Service->>Repo: get_by_id(id)
                    Repo->>DB: SELECT nha_cung_cap WHERE id = parameter
                    DB-->>Repo: Bản ghi hoặc không có
                    Repo-->>Service: SupplierResponse hoặc None
                    alt Không tồn tại
                        Service-->>Client: 404 khong_tim_thay
                    else Tồn tại
                        Service->>Service: Tạo NhaCungCapRead và SHA-256 ETag
                        Service-->>Router: data, meta, etag
                        Router-->>Client: 200 NhaCungCapDetailResponse + ETag
                    end
                end
            end
        end
    end
    Note over Router,DB: Lỗi nội bộ qua handler trả 500 loi_noi_bo, không lộ SQL/stack trace
```

ETag có dấu ngoặc kép, không có tiền tố W/, tính trên dữ liệu nhà cung cấp và không gồm request_id.
Cùng dữ liệu có cùng ETag, đổi bất kỳ trường trả về nào làm đổi ETag. GET không yêu cầu If-Match.
Nhân viên N bị từ chối trước truy vấn nhà cung cấp. Các lỗi dùng `{error, meta.request_id}`;
401 có `WWW-Authenticate: Bearer`. Không có lỗi nghiệp vụ 409 cho hai thao tác chỉ đọc này.

## Các endpoint /suppliers có sẵn

Các đường dẫn bên dưới được giữ để tương thích; chúng vẫn dùng response/query cũ,
không phải các API v2 mới. GET cũ cho mọi tài khoản đã xác thực A/Q/N, POST cũ cho A/Q.
POST/PATCH/DELETE mới dưới `/nha_cung_cap` chỉ cho Q, được mô tả riêng bên dưới.

## GET /api/v1/suppliers

```mermaid
sequenceDiagram
    actor Client
    participant Router
    participant Auth as AuthService / SqlAlchemyAuthRepository
    participant Service as SupplierService
    participant Repo as SqlAlchemySupplierRepository
    participant DB as PostgreSQL
    Client->>Router: GET /api/v1/suppliers
    Router->>Auth: Xác thực JWT, tài khoản, pwdv
    Auth->>DB: SELECT tài khoản và vai trò
    alt Xác thực thất bại hoặc tài khoản khóa
        Auth-->>Client: 401 hoặc 403, envelope cũ
    else Xác thực thành công
        Router->>Router: Validate page, page_size, search, sort_by, sort_order
        alt Validation lỗi
            Router-->>Client: 422, envelope cũ
        else Input hợp lệ
            Router->>Service: list_entries(PageParams)
            Service->>Repo: list_entries / select_page
            Repo->>DB: SELECT COUNT và SELECT phân trang
            DB-->>Repo: Bản ghi và total
            Repo-->>Service: RecordPage
            Service-->>Router: PaginatedResponse
            Router-->>Client: 200 với pagination cũ, không ETag
        end
    end
    Note over Router,DB: Lỗi chưa phân loại trả 500, không ghi dữ liệu
```

## GET /api/v1/suppliers/{supplier_id}

```mermaid
sequenceDiagram
    actor Client
    participant Router
    participant Auth as AuthService / SqlAlchemyAuthRepository
    participant Service as SupplierService
    participant Repo as SqlAlchemySupplierRepository
    participant DB as PostgreSQL
    Client->>Router: GET /api/v1/suppliers/{supplier_id}
    Router->>Auth: Xác thực JWT, tài khoản, pwdv
    Auth->>DB: SELECT tài khoản và vai trò
    alt Xác thực thất bại hoặc tài khoản khóa
        Auth-->>Client: 401 hoặc 403, envelope cũ
    else Xác thực thành công
        Router->>Router: Validate supplier_id kiểu integer
        alt Sai kiểu
            Router-->>Client: 422
        else Input hợp lệ
            Router->>Service: get_entry(supplier_id)
            Service->>Repo: get_by_id / select_by_id
            Repo->>DB: SELECT nha_cung_cap theo ID
            DB-->>Repo: Bản ghi hoặc không có
            Repo-->>Service: SupplierResponse hoặc None
            alt Không có bản ghi
                Service-->>Client: 404, envelope cũ
            else Có bản ghi
                Service-->>Router: SupplierResponse
                Router-->>Client: 200 object trực tiếp, không ETag
            end
        end
    end
    Note over Router,DB: Lỗi chưa phân loại trả 500, không ghi dữ liệu
```

## POST /api/v1/suppliers

```mermaid
sequenceDiagram
    actor Client
    participant Router
    participant Auth as AuthService / SqlAlchemyAuthRepository
    participant Service as SupplierService
    participant Tx as SqlAlchemyTransaction
    participant Repo as SqlAlchemySupplierRepository
    participant Audit as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    Client->>Router: POST SupplierCreate + Bearer JWT
    Router->>Auth: Xác thực và require_roles A/Q
    Auth->>DB: SELECT tài khoản, vai trò, trạng thái và hash
    alt Token không hợp lệ hoặc tài khoản không tồn tại
        Auth-->>Client: 401
    else Khóa hoặc không có quyền A/Q
        Auth-->>Client: 403
    else Có quyền
        Router->>Router: Validate SupplierCreate, từ chối trường thừa
        alt Body sai
            Router-->>Client: 422, envelope cũ
        else Body hợp lệ
            Router->>Service: create_entry(payload, actor)
            Service->>Tx: Mở transaction
            Service->>Repo: add(payload)
            Repo->>DB: Advisory transaction lock, MAX ID hiện tại và audit lịch sử
            Repo->>DB: INSERT nha_cung_cap và flush
            DB-->>Repo: Bản ghi mới
            Repo-->>Service: CreatedRecord và snapshot
            Service->>Audit: append(CreationAudit)
            Audit->>DB: INSERT audit
            alt Vi phạm ràng buộc hoặc lỗi ghi dữ liệu/audit
                Service->>Tx: Rollback
                Tx->>DB: ROLLBACK
                Service-->>Client: Lỗi theo handler hiện có
            else Thành công
                Service->>Tx: Commit
                Tx->>DB: COMMIT
                Service-->>Router: SupplierResponse
                Router-->>Client: 201 object trực tiếp
            end
        end
    end
```

POST cũ chưa có envelope/Location/ETag theo contract v2 và vẫn cho phép ten_ncc nullable.
Quy tắc lỗi transaction theo code hiện tại: IntegrityError được chuyển thành ConflictException
(409), lỗi nội bộ khác 500. Đây là mô tả chức năng cũ, không phải mở rộng phạm vi triển khai.

## POST /api/v1/nha_cung_cap

```mermaid
sequenceDiagram
    actor Client
    participant Router
    participant Auth as AuthService / SqlAlchemyAuthRepository
    participant Service as SupplierService
    participant Tx as SqlAlchemyTransaction
    participant Repo as SqlAlchemySupplierRepository
    participant Audit as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    Client->>Router: POST NhaCungCapCreate + Bearer JWT
    Router->>Auth: Xác thực JWT, pwdv, trạng thái, require_roles Q
    Auth->>DB: SELECT tài khoản và vai trò hiện tại
    alt Token thiếu/sai/hết hạn/thu hồi hoặc account không tồn tại
        Auth-->>Client: 401 chua_xac_thuc
    else Account khóa hoặc vai trò A/N
        Auth-->>Client: 403
    else Q đang hoạt động
        Router->>Router: Validate ma_ncc, ten_ncc, trường nullable, không nhận query/trường thừa
        alt Input sai
            Router-->>Client: 422 du_lieu_khong_hop_le
        else Input hợp lệ
            Router->>Service: create_supplier(payload, actor, request_id)
            Service->>Tx: Dùng transaction của session request
            Service->>Repo: add(payload)
            Repo->>DB: pg_advisory_xact_lock cho cấp ID nhà cung cấp
            Repo->>DB: MAX ID hiện tại và ID trong lịch sử audit
            alt Hết miền INTEGER
                Service->>Tx: Rollback
                Tx->>DB: ROLLBACK
                Service-->>Client: 409 trang_thai_khong_hop_le
            else Có ID kế tiếp
                Repo->>DB: INSERT nha_cung_cap với ID cấp tại backend
                alt Mã trùng
                    Repo-->>Service: SupplierCodeConflict
                    Service->>Tx: Rollback
                    Tx->>DB: ROLLBACK
                    Service-->>Client: 409 ma_bi_trung
                else Insert thành công
                    Repo-->>Service: Bản ghi và snapshot
                    Service->>Audit: append tao, du_lieu_sau
                    Audit->>DB: INSERT audit trong cùng transaction khi flush/commit
                    alt Lỗi ghi audit hoặc commit
                        Service->>Tx: Rollback
                        Tx->>DB: ROLLBACK
                        Service-->>Client: 409 nếu vi phạm ràng buộc, lỗi khác 500
                    else Thành công
                        Service->>Tx: Commit
                        Tx->>DB: COMMIT, nhả advisory lock
                        Service-->>Router: data, meta, ETag
                        Router-->>Client: 201 + Location + ETag
                    end
                end
            end
        end
    end
```

`ma_ncc` do client cung cấp theo contract v2: NCC-000001..NCC-999999, duy nhất.
`ten_ncc` bắt buộc, trim, không rỗng/null. `so_dien_thoai`, `dia_chi`, `phuong`, `tinh`
tùy chọn nullable. Không nhận ID/audit/chi tiết từ client. Không yêu cầu If-Match khi tạo.
SQL không tự tăng `nha_cung_cap.id`: advisory lock giữ tới commit/rollback, cấp
`max(ID hiện tại, ID lịch sử audit nhà cung cấp)+1`; tránh dùng lại ID đã xóa có audit.
Không thêm sequence, migration hoặc sửa SQL hiện có. Cả POST legacy dùng cùng bộ cấp ID.

## PATCH /api/v1/nha_cung_cap/{id}

```mermaid
sequenceDiagram
    actor Client
    participant Router
    participant Auth as AuthService / SqlAlchemyAuthRepository
    participant Service as SupplierService
    participant Tx as SqlAlchemyTransaction
    participant Repo as SqlAlchemySupplierRepository
    participant Audit as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    Client->>Router: PATCH NhaCungCapPatch + JWT + If-Match
    Router->>Auth: Xác thực JWT, pwdv, account, quyền Q
    Auth->>DB: SELECT tài khoản và vai trò
    alt Không xác thực hoặc không có quyền
        Auth-->>Client: 401 hoặc 403
    else Q hợp lệ
        Router->>Router: Validate ID, body, query, header không lặp
        alt Input sai
            Router-->>Client: 422
        else Input hợp lệ
            Router->>Service: patch_supplier(id, payload, If-Match, actor, request_id)
            Service->>Tx: Dùng transaction request
            Service->>Repo: lock_by_id(id), bỏ qua SQL nếu ID vượt INTEGER
            Repo->>DB: SELECT FOR UPDATE, đọc lại bản ghi hiện tại
            DB-->>Service: Bản ghi hoặc không có
            alt Không tồn tại
                Service-->>Client: 404 khong_tim_thay sau rollback
            else Tồn tại
                Service->>Service: Tính ETag và so If-Match dưới khóa
                alt Thiếu hoặc không khớp ETag
                    Service-->>Client: 428 thieu_if_match hoặc 412 du_lieu_da_thay_doi sau rollback
                else ETag đúng
                    opt Có đổi ma_ncc
                        Service->>Repo: has_references(id)
                        Repo->>DB: SELECT EXISTS phieu_nhap WHERE ncc_id=id
                        DB-->>Service: Có/không phiếu tham chiếu
                    end
                    alt Đổi mã khi đã tham chiếu
                        Service-->>Client: 409 dang_duoc_tham_chieu sau rollback
                    else Được phép sửa
                        opt Có giá trị thực sự thay đổi
                            Service->>Repo: update các trường được gửi
                            Repo->>DB: UPDATE RETURNING
                            Service->>Audit: append sua, snapshot trước/sau
                            Audit->>DB: INSERT audit khi flush/commit
                        end
                        alt Mã trùng hoặc lỗi ghi/audit
                            Service->>Tx: Rollback
                            Tx->>DB: ROLLBACK
                            Service-->>Client: 409 ma_bi_trung / conflict, hoặc 500
                        else Thành công
                            Service->>Tx: Commit
                            Tx->>DB: COMMIT, nhả khóa
                            Service-->>Router: data, meta, ETag hiện tại
                            Router-->>Client: 200 + ETag
                        end
                    end
                end
            end
        end
    end
```

PATCH bỏ qua field nghĩa là giữ nguyên; null chỉ xóa trường nullable. Không được gửi null/rỗng
cho `ma_ncc`/`ten_ncc`. Dữ liệu legacy có tên NULL vẫn được sửa các field khác.
Nếu không có giá trị thay đổi (`{}` hoặc gửi lại giá trị hiện tại), trả 200 và ETag cũ,
không ghi audit. Nếu đã tham chiếu, vẫn cho sửa tên/liên hệ/địa chỉ và gửi lại mã cũ.
Hai PATCH thực sự thay đổi dữ liệu dùng cùng ETag: request thắng commit, request sau nhận 412.

## DELETE /api/v1/nha_cung_cap/{id}

```mermaid
sequenceDiagram
    actor Client
    participant Router
    participant Auth as AuthService / SqlAlchemyAuthRepository
    participant Service as SupplierService
    participant Tx as SqlAlchemyTransaction
    participant Repo as SqlAlchemySupplierRepository
    participant Audit as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    Client->>Router: DELETE + JWT + If-Match
    Router->>Auth: Xác thực JWT, pwdv, account, quyền Q
    Auth->>DB: SELECT tài khoản và vai trò
    alt Không xác thực hoặc không có quyền
        Auth-->>Client: 401 hoặc 403
    else Q hợp lệ
        Router->>Router: Validate ID, không query, không lặp If-Match
        alt Input sai
            Router-->>Client: 422
        else Input hợp lệ
            Router->>Service: delete_supplier(id, If-Match, actor)
            Service->>Tx: Dùng transaction request
            Service->>Repo: lock_by_id(id)
            Repo->>DB: SELECT FOR UPDATE
            DB-->>Service: Bản ghi hoặc không có
            alt Không có hoặc ID vượt INTEGER
                Service-->>Client: 404 sau rollback
            else Tồn tại
                Service->>Service: So If-Match dưới khóa
                alt Thiếu hoặc cũ
                    Service-->>Client: 428 hoặc 412 sau rollback
                else Khớp
                    Service->>Repo: has_references(id)
                    Repo->>DB: SELECT EXISTS phieu_nhap WHERE ncc_id=id
                    DB-->>Service: Có/không tham chiếu
                    alt Có bất kỳ phiếu tham chiếu
                        Service-->>Client: 409 dang_duoc_tham_chieu sau rollback
                    else Chưa tham chiếu
                        Service->>Repo: delete(id)
                        Repo->>DB: DELETE nha_cung_cap
                        Service->>Audit: append xoa_nhap, snapshot trước, sau=NULL
                        Audit->>DB: INSERT audit khi flush/commit
                        alt Lỗi FK, ghi audit hoặc commit
                            Service->>Tx: Rollback
                            Tx->>DB: ROLLBACK
                            Service-->>Client: 409 conflict hoặc 500
                        else Thành công
                            Service->>Tx: Commit
                            Tx->>DB: COMMIT, nhả khóa
                            Service-->>Router: Hoàn tất
                            Router-->>Client: 204, không body
                        end
                    end
                end
            end
        end
    end
```

Chặn xóa nếu có phiếu nhập ở bất kỳ trạng thái nào. Khóa FOR UPDATE trên nhà cung cấp
xung đột với khóa FK của thao tác thêm phiếu nhập: nếu phiếu đã thêm trước, mutation chờ
commit rồi kiểm tra lại tham chiếu; nếu DELETE thắng trước, FK ngăn phiếu trỏ tới ID đã xóa.
Không sửa/xóa phiếu nhập, chi tiết, tồn kho hoặc audit cũ.

PATCH/DELETE yêu cầu một ETag cụ thể từ GET, kể cả dấu ngoặc kép. `*`, weak ETag,
giá trị trống hoặc danh sách ETag không khớp trả 412; lặp header trả 422. ID không tồn tại
được xử lý 404 trước khi kiểm tra If-Match. Mọi nhánh thất bại trong transaction đều rollback.
Snapshot không tồn tại được lưu SQL NULL; DELETE giữ snapshot đầy đủ trước khi xóa.
