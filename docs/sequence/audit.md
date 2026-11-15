# Sequence diagram — audit / UC-43

Nguồn: [spec UC-43](../../specs/use_cases/audit/UC-43.md), [plan backend](../plans/UC-43.md), `audit/{router,service,repository,ports,schemas,models}.py`, `app/dependencies.py`, `auth/service.py`, `nhan_vien/{service,repository}.py`, `core/{persistence,exceptions}.py`.
Runtime: **Router → AuditService → AuditRepository (Protocol) → SqlAlchemyAuditRepository → PostgreSQL**. Spec dùng để truy vết/test, không được gọi lúc chạy. Audit sở hữu ORM `LichSuThaoTac` ánh xạ SQL v4; không có migration hoặc thay database đang chạy. API nội bộ `append` giữ caller transaction, không tự commit; không có HTTP ghi/sửa/xóa audit.

## GET /api/v1/audit — Danh sách lịch sử

Bearer JWT bắt buộc; chỉ `quan_tri_vien`, `quan_ly` được đọc, cùng scope và cùng snapshot đã loại bí mật. Query riêng audit: `page=1`, `page_size=20` (1–100), `search`, `sort_by=id|created_at` (mặc định created_at), `sort_order=asc|desc` (mặc định desc), `nhan_vien_id`, `loai_doi_tuong`, `doi_tuong_id`, `thao_tac`, `bo_thao_tac`, `tu_ngay`, `den_ngay`.

Filter AND trước COUNT/phân trang. Search literal không phân biệt hoa/thường trên loại/thao tác/lý do, không search JSON. ID tiebreak cùng chiều sort. Ngày YYYY-MM-DD quy về Asia/Ho_Chi_Minh: từ đầu ngày ≥ đến trước đầu ngày tiếp theo <; hỗ trợ một đầu. Từ ngày tối thiểu Python và đến ngày tối đa bị từ chối tránh overflow. Query lạ/lặp, ID/enum/sort/ngày/page sai trả 422. `bo_thao_tac` chấp nhận bộ mã loại trừ legacy (kể cả `thu_hoi_quyen`) nhưng không thêm các mã đó vào giá trị ghi v4; chọn và loại cùng một thao tác trả tập rỗng.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as audit.router và dependencies
    participant A as auth.service
    participant N as nhan_vien.service
    participant NP as nhan_vien.repository
    participant S as AuditService
    participant P as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/audit, Bearer JWT, query
    R->>A: current_payload(token)
    A->>A: Verify JWT và sub
    A->>N: get_auth_identity(id, pwdv)
    N->>NP: get_credentials_by_id(id)
    NP->>DB: SELECT NhanVien và VaiTro
    DB-->>NP: Credentials
    NP-->>N: EmployeeCredentials
    N->>N: Kiểm tra account, role, pwdv
    alt Token/account mất hoặc pwdv cũ
        R-->>C: 401 UNAUTHORIZED
    else Account khóa hoặc role không hợp lệ
        R-->>C: 403 FORBIDDEN
    else Xác thực hợp lệ
        N-->>A: Verified identity
        A-->>R: Payload với roles hiện tại
        R->>R: require_roles, AuditListQuery và reject query lặp
        alt Role là nhan_vien
            R-->>C: 403 FORBIDDEN
        else Query số trang/kích thước/chiều sort hoặc enum bo_thao_tac không hợp lệ
            R-->>C: 422 VALIDATION_ERROR
        else Có quyền và input hợp lệ
            R->>S: list_entries(params, actor)
            S->>S: Require reader, chuyển ngày Việt Nam sang biên UTC
            alt Service actor không có quyền
                S-->>R: ForbiddenException, chưa gọi repository
                R-->>C: 403 legacy error
            else Service actor hợp lệ
                S->>P: list_entries(params, created_from, created_before)
                P->>DB: COUNT với cùng filter AND và literal search
                DB-->>P: Tổng sau filter
                opt Offset nhỏ hơn tổng
                    P->>DB: SELECT cùng filter, sort và ID tiebreak, OFFSET/LIMIT
                    DB-->>P: Các dòng đã lưu
                end
                P-->>S: RecordPage chứa AuditRecord
                S->>S: Copy, loại key bí mật ở mọi cấp JSON, giữ null/snapshot
                S-->>R: PaginatedResponse of AuditLogResponse
                R-->>C: 200 success, data, pagination, message
            end
        end
    end
    Note over R,DB: Lỗi đọc không dự kiến trả 500 an toàn, không trả tập rỗng giả
    Note over S,DB: Không append, khóa dòng hoặc commit nghiệp vụ
```

![Danh sách audit](assets/audit/audit-01-danh-sach.png)

200 giữ `{success, data: [...], pagination: {page, page_size, total_items, total_pages, has_next, has_prev}, message}`. Trang vượt tổng trả tập rỗng, total vẫn đúng; thứ tự phân trang xác định với tập dữ liệu không đổi, không hứa ổn định khi có INSERT xen kẽ các request.

## GET /api/v1/audit/{id} — Chi tiết lịch sử

Bearer JWT, role và tài khoản được kiểm tra như danh sách. Detail không nhận query. Path phải integer > 0; sai cấu trúc trả 422. ID dương vượt miền INTEGER hoặc không có record trả 404. Không yêu cầu ETag/If-Match.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as audit.router và dependencies
    participant A as AuthService
    participant N as NhanVienService
    participant NP as NhanVienRepository
    participant S as AuditService
    participant P as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/audit/id, Bearer JWT
    R->>A: current_payload(token)
    A->>A: Verify signature, exp, iat, sub
    A->>N: get_auth_identity(id, pwdv)
    N->>NP: get_credentials_by_id(id)
    NP->>DB: SELECT NhanVien và VaiTro
    DB-->>NP: Credentials và role hiện tại
    NP-->>N: EmployeeCredentials
    N->>N: Check active account và pwdv
    alt Token/account mất, token sai hoặc pwdv cũ
        R-->>C: 401 legacy error
    else Account khóa hoặc role không được đọc
        R-->>C: 403 legacy error
    else Xác thực hợp lệ
        N-->>A: Verified identity
        A-->>R: Actor với role DB hiện tại
        R->>R: Validate positive path ID, reject mọi query
        alt Path ID hoặc query sai
            R-->>C: 422 legacy validation error
        else Input hợp lệ
            R->>S: get_entry(id, actor)
            S->>S: Require reader và kiểm miền INTEGER
            alt Service actor không có quyền
                S-->>R: ForbiddenException
                R-->>C: 403 legacy error
            else ID vượt miền INTEGER
                S-->>R: NotFoundException không query DB
                R-->>C: 404 legacy error
            else ID trong miền
                S->>P: get_entry(id)
                P->>DB: SELECT LichSuThaoTac theo primary key
                DB-->>P: Row hoặc none
                P-->>S: AuditRecord hoặc none
                alt Không có record
                    S-->>R: NotFoundException
                    R-->>C: 404 legacy error
                else Có record
                    S->>S: Copy snapshot, loại key bí mật, giữ trạng thái và null
                    S-->>R: AuditDetailResponse
                    R-->>C: 200 success, data, message
                end
            end
        end
    end
    Note over R,DB: Lỗi đọc hoặc serialize không dự kiến trả 500 an toàn
    Note over S,DB: Chỉ đọc bằng chứng đã lưu, không ghi audit hay tính lại snapshot
```

![Chi tiết audit](assets/audit/audit-02-chi-tiet.png)

200: `{success: true, data: AuditLogResponse, message}`. Hai trường trạng thái, hai snapshot và lý do giữ null theo SQL. Danh sách thiếu đọc từ `du_lieu_sau.danh_sach_thieu`; không truy dữ liệu hiện tại để dựng lại lịch sử. Hai vai trò nhận cùng dữ liệu đã redaction.

## Transaction, lỗi và giới hạn

- Giữ lỗi audit legacy: 401/403/404/422 dạng `{success:false,error,timestamp}`, lỗi không dự kiến 500 dạng `{detail:"Internal Server Error"}`. Không trả tập rỗng giả khi DB lỗi. Khi request sai nhiều điều kiện, thứ tự validation/auth tùy dependency thực tế, không suy từ thứ tự sơ đồ.
- GET không có transaction ghi/khóa dòng và không gọi append/commit nghiệp vụ. Middleware hiện có có thể đếm request vào bảng kỹ thuật `LuuLuongTruyCap`, không vào lịch sử nghiệp vụ.
- `created_at` là TIMESTAMPTZ; hai snapshot JSONB(none_as_null=True). SQL v4 có ba index và trigger `trg_audit_bat_bien`; ORM create_all đơn thuần không tạo trigger này. HTTP POST/PUT/PATCH/DELETE không được đăng ký, trả 405; PostgreSQL chặn UPDATE/DELETE.
- Luồng ghi giữ `Service UC nguồn → AuditService.append → SqlAlchemyAuditRepository.append` cùng caller transaction; append không commit. Lỗi caller/flush/commit rollback cả nghiệp vụ và audit. Không refactor các producer khác trong UC-43.
- Redaction nhận key password/mat_khau/hash/token/authorization/cookie/secret/pwdv/credential_version và biến thể snake/camel/kebab case ở mọi cấp dict/mảng. `da_doi_mat_khau` là kết quả nghiệp vụ được giữ. Không sửa dữ liệu DB; không bảo đảm tìm được bí mật giấu trong field văn bản tự do có tên vô hại. UC nguồn vẫn phải tuân thủ BR-016 không lưu bí mật.
- Auth hiện dùng `pwdv` và role/trạng thái đọc lại DB; chưa nâng toàn auth sang `phien_ban_dang_nhap` v4. Các producer v3 với mã `ve_nhap`, `vo_hieu_hoa`, đối tượng `lenh_san_xuat`… vẫn là dependency ngoài phạm vi, chưa được xác nhận E2E với SQL v4.
- **Frontend UC-43 hoãn theo dev**; không khẳng định AC-19 giao diện đã đạt. Sequence này mô tả hai endpoint backend thực sự hiện có.
