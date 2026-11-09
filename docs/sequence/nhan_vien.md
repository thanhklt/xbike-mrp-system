# Sequence diagram — nhan_vien

Nguồn: `nhan_vien/{router,service,repository,schemas,models}.py`, `auth/service.py`, `app/dependencies.py`, `core/{security,exceptions,request_context}.py`.
Module sở hữu ORM/bảng `NhanVien`, `VaiTro`; không có ORM trong auth. Public service cũng cung cấp xác thực/đổi mật khẩu cho auth, mô tả ở [auth.md](auth.md).
FastAPI cache dependency trong mỗi request nên kiểm tra auth dùng chung session với các truy vấn nhân viên. Nếu request đồng thời sai auth và input, sơ đồ không quy định thứ tự ưu tiên lỗi. Lỗi được chuyển thành HTTP qua exception handlers chung.

## GET /api/v1/nhan_vien — Danh sách nhân viên

Query: `page` mặc định 1, tối thiểu 1; `page_size` mặc định 20, từ 1 đến 100; `q`, `vai_tro_id` dương, `trang_thai=hoat_dong|bi_khoa`; `sort` mặc định `id`, cho phép `id`, `ma_nhan_vien`, `ho_ten`, `ten_dang_nhap` và tiền tố `-` cho chiều giảm dần. Query lặp hoặc không khai báo trả 422.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as nhan_vien.router và dependencies
    participant A as auth.service
    participant N as nhan_vien.service
    participant P as nhan_vien.repository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/nhan_vien, Bearer JWT, query
    R->>A: current_payload(token)
    A->>A: Verify JWT và định dạng sub
    A->>N: get_auth_identity(id, pwdv)
    N->>P: get_credentials_by_id(id)
    P->>DB: SELECT NhanVien và VaiTro
    DB-->>N: Account qua repository
    N->>N: Kiểm tra trạng thái, role và password version
    alt Thiếu/token lỗi/account mất/pwdv cũ
        R-->>C: 401 chua_xac_thuc
    else Account khóa hoặc role không hợp lệ
        R-->>C: 403
    else Xác thực hợp lệ
        N-->>A: AuthIdentity
        A-->>R: Actor với roles hiện tại
        R->>R: Validate query, reject duplicate/unknown
        alt Query không hợp lệ
            R-->>C: 422 du_lieu_khong_hop_le
        else Query hợp lệ
            R->>N: list_employees(params, actor, request_id)
            alt Actor không là quan_tri_vien hoặc quan_ly
                N-->>C: 403 khong_co_quyen
            else Có quyền
                N->>P: list_employees(params)
                P->>DB: COUNT NhanVien theo bộ lọc
                DB-->>P: total
                opt offset nhỏ hơn total
                    P->>DB: SELECT theo bộ lọc, sort và id, OFFSET/LIMIT#59; tải VaiTro
                    DB-->>P: Nhân viên và vai trò
                end
                P-->>N: RecordPage các EmployeeRecord
                N->>N: Chọn projection theo vai trò, tính total_pages
                N-->>R: NhanVienListResponse
                R-->>C: 200 data và meta phân trang
            end
        end
    end
```

- Admin nhận hồ sơ đầy đủ. Quản lý chỉ nhận `id`, `ma_nhan_vien`, `ho_ten`, `vai_tro_id`, `ma_vai_tro`, `trang_thai` để giao việc. Nhân viên không được xem danh sách.
- `q` tìm không phân biệt hoa/thường theo mã/họ tên; escape `%` và `_`, không nội suy SQL. Sort thêm `id` để ổn định phân trang.
- Filter vai trò vượt signed 32-bit cho kết quả rỗng. Trang vượt tổng trả 200 với `data=[]`; tổng 0 có `total_pages=0`. Meta gồm request_id, page, page_size, total, total_pages.

## GET /api/v1/nhan_vien/{id} — Chi tiết nhân viên

Path ID nguyên dương; không nhận query. Strong ETag được tính từ profile sau projection, không từ request_id.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as nhan_vien.router và dependencies
    participant A as auth.service
    participant N as nhan_vien.service
    participant P as nhan_vien.repository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/nhan_vien/{id}, Bearer JWT
    R->>A: current_payload(token)
    A->>A: Verify JWT và sub
    A->>N: get_auth_identity(actor_id, pwdv)
    N->>P: get_credentials_by_id(actor_id)
    P->>DB: SELECT NhanVien và VaiTro
    DB-->>N: Account hiện tại qua repository
    N->>N: Kiểm tra trạng thái/role/password version
    alt Token/account mất hoặc version cũ
        R-->>C: 401 chua_xac_thuc
    else Account khóa hoặc role không hợp lệ
        R-->>C: 403
    else Auth hợp lệ
        A-->>R: Actor với roles từ DB
        R->>R: Validate path ID và reject_query
        alt ID không dương hoặc có query
            R-->>C: 422 du_lieu_khong_hop_le
        else Input hợp lệ
            R->>N: get_employee(id, actor, request_id)
            alt ID vượt signed 32-bit
                N-->>C: 404 khong_tim_thay
            else ID trong phạm vi
                N->>P: get_by_id(id)
                P->>DB: SELECT NhanVien và tải VaiTro
                DB-->>P: Record hoặc None
                P-->>N: EmployeeRecord hoặc None
                alt Không tồn tại
                    N-->>C: 404 khong_tim_thay
                else Nhân viên đọc hồ sơ người khác
                    N-->>C: 403 khong_co_quyen
                else Admin, quản lý hoặc chính mình
                    N->>N: Chọn projection và tính SHA-256 ETag
                    N-->>R: NhanVienDetailResponse và ETag
                    R-->>C: 200 data, meta.request_id, ETag
                end
            end
        end
    end
```

Admin và chính chủ đọc hồ sơ đầy đủ; quản lý đọc người khác chỉ có projection giao việc. Thiếu account đích được kiểm tra trước phạm vi truy cập. Nullable profile được giữ là null; `he_so_luong` được serialize thành JSON string. Không response nào có password hash, `tai_khoan_id`, JWT hoặc `loai_nhan_vien`.
GET không ghi audit hoặc commit. Ngoài các nhánh trên, lỗi không dự kiến được handler chung trả 500 an toàn. Module có đủ 8 endpoint bên dưới. Quyết định ngày 01/11/2026 thay DELETE xóa thật bằng soft delete, bỏ POST /vo_hieu_hoa và giữ /mo_khoa.


## Quy ước chung cho thao tác ghi

- PATCH chỉ admin và chỉ sửa hồ sơ. POST/PUT/DELETE/mở khóa cũng chỉ admin.
- Một admin được bootstrap sẵn. API chặn tạo/cấp thêm admin, hạ quyền hoặc khóa admin hiện tại. Schema chưa có unique constraint singleton-admin; SQL trực tiếp nằm ngoài chính sách API này.
- `_lock_admin` khóa dòng admin bằng SELECT FOR UPDATE và refresh account/role/password version sau khi chờ khóa, tuần tự hóa request quản trị. `_target` khóa/refresh dòng đích trước kiểm tra ETag.
- Thiếu If-Match trả 428 `thieu_if_match`; ETag cũ, wildcard hoặc weak ETag trả 412 `du_lieu_da_thay_doi`. Không có tài khoản đích trả 404 trước kiểm tra ETag. Admin mất hiệu lực trong lúc chờ khóa trả 401/403 và rollback.
- SqlAlchemyTransaction dùng session chung với auth, repository nhân viên và audit. Auth có thể đã mở transaction bằng SELECT; __aenter__ không mở transaction lồng nhau. AuditService gọi audit repository để session.add; flush audit và COMMIT khi transaction kết thúc. Lỗi rollback toàn bộ thay đổi.
- Lỗi nhân viên/vai trò dùng `{error: {code, message, details}, meta: {request_id}}` giống auth theo contract v2; thay envelope GET cũ có success/timestamp. Validation chỉ trả tên trường/lý do, không echo input nhạy cảm.
- Thao tác ghi không nhận query. Không response/audit nào chứa mật khẩu/hash/JWT.


## POST /api/v1/nhan_vien — Tạo nhân viên

NhanVienCreate bắt buộc ten_dang_nhap trim 1–255 ký tự; mat_khau 8–1024 ký tự không trim; ma_nhan_vien NV-NNNNNN khác NV-000000; vai_tro_id integer dương signed 32-bit. Hồ sơ nullable là tùy chọn. he_so_luong là decimal JSON string 0–999.99, tối đa 2 số thập phân; ngày YYYY-MM-DD. Server đặt hoat_dong; field dư trả 422. Không cần If-Match.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as nhan_vien.router và dependencies
    participant A as auth.service
    participant N as NhanVienService
    participant P as nhan_vien.repository
    participant AU as audit.service
    participant AR as audit.repository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: POST /api/v1/nhan_vien, JWT, body và headers
    R->>A: current_payload(token)
    A-->>R: Actor hiện tại hoặc 401/403
    R->>R: Validate path/body và reject query
    alt Auth/input lỗi
        R-->>C: 401 / 403 / 422
    else Request hợp lệ
        R->>N: create_employee
        N->>N: Require admin
        break Actor không là admin
            N-->>R: ForbiddenException
            R-->>C: 403 khong_co_quyen
        end
        N->>N: Hash Argon2id qua worker thread
        N->>T: __aenter__
        N->>P: lock_credentials_by_id(admin_id)
        P->>DB: SELECT admin FOR UPDATE và refresh
        N->>N: Recheck account/role/password version
        N->>P: get_role(vai_tro_id)
        P->>DB: SELECT VaiTro
        N->>N: Check role tồn tại và không phải admin
        alt Điều kiện nghiệp vụ lỗi hoặc admin mất hiệu lực sau chờ khóa
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 401/403 sau recheck hoặc 404 role / 409 admin thứ hai
        else Điều kiện hợp lệ
            N->>P: create(NewEmployee)
            P->>DB: INSERT NhanVien, flush và tải role
            break Trùng username hoặc mã nhân viên
                N->>T: __aexit__(DuplicateCodeException)
                T->>DB: ROLLBACK
                R-->>C: 409 ma_bi_trung
            end
            opt Có thay đổi thực tế
                N->>AU: append tao
                AU->>AR: append(entry), session.add
            end
            N->>T: __aexit__
            alt Audit/commit lỗi
                T->>DB: ROLLBACK
                R-->>C: 409 constraint / 500 nội bộ
            else Thành công
                T->>DB: Flush audit và COMMIT
                N-->>R: Profile an toàn và ETag
                R-->>C: 201 data, meta, Location và ETag
            end
        end
    end
```

Location trỏ GET chi tiết mới; username/mã bất biến sau tạo. Không cấp JWT.


## PATCH /api/v1/nhan_vien/{id} — Sửa hồ sơ

NhanVienPatch chỉ nhận ho_ten, ngay_sinh, so_dien_thoai, email, ngay_vao_lam, he_so_luong. Bỏ qua giữ nguyên; null xóa giá trị nullable. Username, mã, mật khẩu, role, trạng thái và field dư trả 422. Bắt buộc If-Match.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as nhan_vien.router và dependencies
    participant A as auth.service
    participant N as NhanVienService
    participant P as nhan_vien.repository
    participant AU as audit.service
    participant AR as audit.repository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: PATCH /api/v1/nhan_vien/{id}, JWT, body và headers
    R->>A: current_payload(token)
    A-->>R: Actor hiện tại hoặc 401/403
    R->>R: Validate path/body và reject query
    alt Auth/input lỗi
        R-->>C: 401 / 403 / 422
    else Request hợp lệ
        R->>N: patch_employee
        N->>N: Require admin
        break Actor không là admin
            N-->>R: ForbiddenException
            R-->>C: 403 khong_co_quyen
        end
        N->>T: __aenter__
        N->>P: lock_credentials_by_id(admin_id)
        P->>DB: SELECT admin FOR UPDATE và refresh
        N->>N: Recheck account/role/password version
        N->>P: get_for_update(id)
        P->>DB: SELECT nhân viên FOR UPDATE, refresh role
        N->>N: Check tồn tại và ETag
        break Không tồn tại hoặc ETag lỗi
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 404 / 428 / 412
        end

        alt Điều kiện nghiệp vụ lỗi hoặc admin mất hiệu lực sau chờ khóa
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 401/403 sau recheck hoặc 404 / 428 / 412
        else Điều kiện hợp lệ
            opt Có trường thay đổi thực tế
                N->>P: update_profile(id, changes)
                P->>DB: UPDATE hồ sơ và đọc lại record
            end
            opt Có thay đổi thực tế
                N->>AU: append sua nếu có thay đổi
                AU->>AR: append(entry), session.add
            end
            N->>T: __aexit__
            alt Audit/commit lỗi
                T->>DB: ROLLBACK
                R-->>C: 409 constraint / 500 nội bộ
            else Thành công
                T->>DB: Flush audit và COMMIT
                N-->>R: Profile an toàn và ETag
                R-->>C: 200 data, meta và ETag
            end
        end
    end
```

Body rỗng hoặc giá trị không đổi là no-op, không thêm audit. Hai request cùng ETag chỉ một request thay đổi thành công; request sau nhận 412.


## DELETE /api/v1/nhan_vien/{id} — Soft delete bằng khóa tài khoản

Body LyDoInput bắt buộc: {"ly_do":"..."}, trim không rỗng. Bắt buộc If-Match. Thay thế POST /vo_hieu_hoa theo quyết định ngày 01/11/2026. Chuyển hoat_dong sang bi_khoa, giữ nguyên dòng nhân viên, role, chứng từ và lịch sử.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as nhan_vien.router và dependencies
    participant A as auth.service
    participant N as NhanVienService
    participant P as nhan_vien.repository
    participant AU as audit.service
    participant AR as audit.repository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: DELETE /api/v1/nhan_vien/{id}, JWT, body và headers
    R->>A: current_payload(token)
    A-->>R: Actor hiện tại hoặc 401/403
    R->>R: Validate path/body và reject query
    alt Auth/input lỗi
        R-->>C: 401 / 403 / 422
    else Request hợp lệ
        R->>N: soft_delete_employee rồi _change_status
        N->>N: Require admin
        break Actor không là admin
            N-->>R: ForbiddenException
            R-->>C: 403 khong_co_quyen
        end
        N->>T: __aenter__
        N->>P: lock_credentials_by_id(admin_id)
        P->>DB: SELECT admin FOR UPDATE và refresh
        N->>N: Recheck account/role/password version
        N->>P: get_for_update(id)
        P->>DB: SELECT nhân viên FOR UPDATE, refresh role
        N->>N: Check tồn tại và ETag
        break Không tồn tại hoặc ETag lỗi
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 404 / 428 / 412
        end
        N->>N: Check đang hoat_dong và không phải admin
        alt Điều kiện nghiệp vụ lỗi hoặc admin mất hiệu lực sau chờ khóa
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 401/403 sau recheck hoặc 404 / 428 / 412 / 409 đã khóa hoặc là admin
        else Điều kiện hợp lệ
            N->>P: set_status(id, bi_khoa)
            P->>DB: UPDATE trạng thái và đọc lại record
            opt Có thay đổi thực tế
                N->>AU: append vo_hieu_hoa, lý do và dữ liệu trước/sau
                AU->>AR: append(entry), session.add
            end
            N->>T: __aexit__
            alt Audit/commit lỗi
                T->>DB: ROLLBACK
                R-->>C: 409 constraint / 500 nội bộ
            else Thành công
                T->>DB: Flush audit và COMMIT
                N-->>R: Profile an toàn và ETag
                R-->>C: 204 không body, ETag mới
            end
        end
    end
```

Không tự khóa admin. Gọi lại với ETag cũ trả 412; ETag hiện tại nhưng đã khóa trả 409, không thêm audit. JWT cũ bị từ chối 403 khi bị khóa. Tài khoản vẫn có trong danh sách/lịch sử và hỗ trợ lọc trạng thái.


## PUT /api/v1/nhan_vien/{id}/vai_tro — Đổi vai trò

DoiVaiTroInput chỉ nhận vai_tro_id integer dương signed 32-bit. Bắt buộc If-Match. Không cấp admin cho tài khoản khác hoặc hạ quyền admin hiện tại; chỉ đổi giữa vai trò không phải admin.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as nhan_vien.router và dependencies
    participant A as auth.service
    participant N as NhanVienService
    participant P as nhan_vien.repository
    participant AU as audit.service
    participant AR as audit.repository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: PUT /api/v1/nhan_vien/{id}/vai_tro, JWT, body và headers
    R->>A: current_payload(token)
    A-->>R: Actor hiện tại hoặc 401/403
    R->>R: Validate path/body và reject query
    alt Auth/input lỗi
        R-->>C: 401 / 403 / 422
    else Request hợp lệ
        R->>N: change_role
        N->>N: Require admin
        break Actor không là admin
            N-->>R: ForbiddenException
            R-->>C: 403 khong_co_quyen
        end
        N->>T: __aenter__
        N->>P: lock_credentials_by_id(admin_id)
        P->>DB: SELECT admin FOR UPDATE và refresh
        N->>N: Recheck account/role/password version
        N->>P: get_for_update(id)
        P->>DB: SELECT nhân viên FOR UPDATE, refresh role
        N->>N: Check tồn tại và ETag
        break Không tồn tại hoặc ETag lỗi
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 404 / 428 / 412
        end
        N->>P: get_role(role_id)
        P->>DB: SELECT VaiTro
        N->>N: Check role tồn tại và không thay đổi admin duy nhất
        alt Điều kiện nghiệp vụ lỗi hoặc admin mất hiệu lực sau chờ khóa
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 401/403 sau recheck hoặc 404 nhân viên hoặc role / 428 / 412 / 409 một admin
        else Điều kiện hợp lệ
            opt Vai trò thực sự thay đổi
                N->>P: set_role(id, role_id)
                P->>DB: UPDATE vai trò và đọc lại record
            end
            opt Có thay đổi thực tế
                N->>AU: append thu_hoi_quyen và cap_quyen nếu có thay đổi
                AU->>AR: append(entry), session.add
            end
            N->>T: __aexit__
            alt Audit/commit lỗi
                T->>DB: ROLLBACK
                R-->>C: 409 constraint / 500 nội bộ
            else Thành công
                T->>DB: Flush audit và COMMIT
                N-->>R: Profile an toàn và ETag
                R-->>C: 200 data, meta và ETag
            end
        end
    end
```

Vai trò không đổi là no-op sau kiểm tra ETag. Hai audit khi đổi role cùng transaction. Request tiếp theo dùng JWT cũ đọc quyền mới từ DB; không đổi password/trạng thái/công việc.


## POST /api/v1/nhan_vien/{id}/mo_khoa — Mở khóa

Body LyDoInput bắt buộc: {"ly_do":"..."}, trim không rỗng. Bắt buộc If-Match. Chỉ chấp nhận bi_khoa và chuyển sang hoat_dong.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as nhan_vien.router và dependencies
    participant A as auth.service
    participant N as NhanVienService
    participant P as nhan_vien.repository
    participant AU as audit.service
    participant AR as audit.repository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: POST /api/v1/nhan_vien/{id}/mo_khoa, JWT, body và headers
    R->>A: current_payload(token)
    A-->>R: Actor hiện tại hoặc 401/403
    R->>R: Validate path/body và reject query
    alt Auth/input lỗi
        R-->>C: 401 / 403 / 422
    else Request hợp lệ
        R->>N: unlock_employee rồi _change_status
        N->>N: Require admin
        break Actor không là admin
            N-->>R: ForbiddenException
            R-->>C: 403 khong_co_quyen
        end
        N->>T: __aenter__
        N->>P: lock_credentials_by_id(admin_id)
        P->>DB: SELECT admin FOR UPDATE và refresh
        N->>N: Recheck account/role/password version
        N->>P: get_for_update(id)
        P->>DB: SELECT nhân viên FOR UPDATE, refresh role
        N->>N: Check tồn tại và ETag
        break Không tồn tại hoặc ETag lỗi
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 404 / 428 / 412
        end
        N->>N: Check đang bi_khoa
        alt Điều kiện nghiệp vụ lỗi hoặc admin mất hiệu lực sau chờ khóa
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 401/403 sau recheck hoặc 404 / 428 / 412 / 409 đã hoạt động
        else Điều kiện hợp lệ
            N->>P: set_status(id, hoat_dong)
            P->>DB: UPDATE trạng thái và đọc lại record
            opt Có thay đổi thực tế
                N->>AU: append sua, lý do và dữ liệu trước/sau
                AU->>AR: append(entry), session.add
            end
            N->>T: __aexit__
            alt Audit/commit lỗi
                T->>DB: ROLLBACK
                R-->>C: 409 constraint / 500 nội bộ
            else Thành công
                T->>DB: Flush audit và COMMIT
                N-->>R: Profile an toàn và ETag
                R-->>C: 200 data, meta và ETag
            end
        end
    end
```

Audit dùng sua vì enum chưa có mo_khoa. Không cấp JWT mới, không đổi password/role. JWT cũ còn hạn và đúng password version dùng lại được sau mở khóa.


## GET /api/v1/vai_tro — Danh sách vai trò

Thuộc module nhân viên, đăng ký vai_tro_router tại /api/v1. Chỉ admin/quản lý được đọc. Query chỉ có page mặc định 1 (>=1), page_size mặc định 20 (1–100); dư/lặp trả 422. Sắp xếp ID tăng dần; trang vượt tổng trả data rỗng. Response gồm id, ma_vai_tro, ten_vai_tro, mo_ta (string hoặc null) và meta phân trang giống danh sách nhân viên. Bộ vai trò cố định ba mã; không có API tạo/sửa/xóa vai trò (D-VT-01).

```mermaid
sequenceDiagram
    actor C as Client
    participant R as nhan_vien.router và dependencies
    participant A as auth.service
    participant N as NhanVienService
    participant P as nhan_vien.repository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/vai_tro, JWT, page/page_size
    R->>A: current_payload(token)
    A-->>R: Actor hoặc 401/403
    R->>R: get_role_query, validate và reject query dư/lặp
    alt Auth/query lỗi
        R-->>C: 401 / 403 / 422
    else Request hợp lệ
        R->>N: list_roles(params, actor, request_id)
        alt Actor không là admin hoặc quản lý
            N-->>R: ForbiddenException
            R-->>C: 403 khong_co_quyen
        else Có quyền
            N->>P: list_roles(params)
            P->>DB: COUNT VaiTro
            opt Offset nhỏ hơn total
                P->>DB: SELECT VaiTro ORDER BY id OFFSET LIMIT
            end
            P-->>N: RecordPage các VaiTroRead
            N-->>R: VaiTroListResponse
            R-->>C: 200 data, meta phân trang
        end
    end
```

GET không ghi audit hoặc commit. Chi tiết xác thực dùng get_auth_identity như hai GET nhân viên ở trên.
