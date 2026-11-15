# Sequence diagram — nhan_vien

Nguồn: `nhan_vien/{router,service,repository,schemas,models}.py`, `auth/service.py`, `app/dependencies.py`, `core/{security,exceptions,request_context}.py`.
Module sở hữu ORM/bảng `NhanVien`, `VaiTro`; không có ORM trong auth. Public service cũng cung cấp xác thực/đổi mật khẩu cho auth, mô tả ở [auth.md](auth.md).
FastAPI cache dependency trong mỗi request nên kiểm tra auth dùng chung session với các truy vấn nhân viên. Nếu request đồng thời sai auth và input, sơ đồ không quy định thứ tự ưu tiên lỗi. Lỗi được chuyển thành HTTP qua exception handlers chung.

Theo [UC-06](../../specs/use_cases/identity_access/UC-06.md) A3/D1, `current_payload` truyền thêm `session_version=payload.get("pbdn", 0)` vào `get_auth_identity` cho mọi endpoint bên dưới. Service so với `NhanVien.phien_ban_dang_nhap`; lệch hoặc claim không phải số nguyên trả 401 `chua_xac_thuc` (`Please sign in again`). Tài khoản đang khóa vẫn trả 403. Chi tiết xác thực nằm trong [auth.md](auth.md).

## GET /api/v1/nhan_vien — Danh sách nhân viên

Nguồn nghiệp vụ: [UC-03 — Xem danh sách tài khoản](../../specs/use_cases/identity_access/UC-03.md), Main 2–4, R1–R4, A1–A4; D1 ngày 15/11/2026.

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
    A->>N: get_auth_identity(id, pwdv, session_version=pbdn hoặc 0)
    N->>P: get_credentials_by_id(id)
    P->>DB: SELECT NhanVien và VaiTro
    DB-->>N: Account qua repository
    N->>N: Kiểm tra trạng thái, role, password version và phiên bản đăng nhập
    alt Thiếu/token lỗi/account mất/pwdv hoặc pbdn cũ
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
                N->>N: QTV đủ hồ sơ#59; QLK bỏ ten_dang_nhap (R4)#59; tính total_pages
                N-->>R: NhanVienListResponse
                R-->>C: 200 data và meta phân trang
            end
        end
    end
```

- Admin nhận hồ sơ đầy đủ, có `ten_dang_nhap`. QLK nhận `id`, `ma_nhan_vien`, `ho_ten`, `vai_tro_id`, `ma_vai_tro`, `trang_thai`, `ngay_sinh`, `so_dien_thoai`, `email`, `ngay_vao_lam`, `he_so_luong`; không có `ten_dang_nhap` hoặc mật khẩu/hash (D1, R4). Nhân viên không được xem danh sách. Trang `/admin/tai-khoan` vẫn chỉ QTV vào được.
- Response QLK bổ sung các trường hồ sơ, tương thích ngược với caller hiện tại như `ProductionPage`; tham số query, phân trang và quyền NV giữ nguyên.
- `q` tìm không phân biệt hoa/thường theo mã/họ tên; escape `%` và `_`, không nội suy SQL. Sort thêm `id` để ổn định phân trang.
- Filter vai trò vượt signed 32-bit cho kết quả rỗng. Trang vượt tổng trả 200 với `data=[]`; tổng 0 có `total_pages=0`. Meta gồm request_id, page, page_size, total, total_pages.

## GET /api/v1/nhan_vien/{id} — Chi tiết nhân viên

Nguồn nghiệp vụ: [UC-03 — Xem danh sách tài khoản](../../specs/use_cases/identity_access/UC-03.md), R4; D1 ngày 15/11/2026.

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
    A->>N: get_auth_identity(actor_id, pwdv, session_version=pbdn hoặc 0)
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
                    N->>N: QTV/chính chủ đủ hồ sơ#59; QLK đọc người khác bỏ ten_dang_nhap (R4)
                    N->>N: Tính SHA-256 ETag từ hồ sơ sau projection
                    N-->>R: NhanVienDetailResponse và ETag
                    R-->>C: 200 data, meta.request_id, ETag
                end
            end
        end
    end
```

Admin và chính chủ đọc hồ sơ đầy đủ, có `ten_dang_nhap`; QLK đọc người khác nhận cùng tập trường như danh sách QLK ở trên, trừ `ten_dang_nhap` và mật khẩu/hash (D1, R4). Thay đổi bổ sung trường hồ sơ cho QLK tương thích ngược với caller hiện tại; ETag được tính từ projection mới. Thiếu account đích được kiểm tra trước phạm vi truy cập. Nullable profile được giữ là null; `he_so_luong` được serialize thành JSON string. Không response nào có mật khẩu/hash, `tai_khoan_id`, JWT hoặc `loai_nhan_vien`.
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

Nguồn nghiệp vụ: [UC-04 — Thêm tài khoản](../../specs/use_cases/identity_access/UC-04.md), Main 2–6, R1–R7, A1–A7; D1–D4 trong [plan UC-04](../plans/UC-04.md).

NhanVienCreate bắt buộc `ten_dang_nhap` trim 1–255 ký tự; `mat_khau` 6–1024 ký tự không trim; `vai_tro_id` integer dương signed 32-bit. Chọn được cả `quan_tri_vien`, `quan_ly`, `nhan_vien`. Hồ sơ nullable là tùy chọn: `ho_ten`, `ngay_sinh`, `so_dien_thoai`, `email`, `ngay_vao_lam`, `he_so_luong`. `he_so_luong` là decimal JSON string 0–999.99, tối đa 2 số thập phân; ngày YYYY-MM-DD. `ly_do` tùy chọn, trim, tối đa 1000 ký tự, rỗng thành null; chỉ dùng cho lịch sử. Server tự cấp `ma_nhan_vien`, đặt `hoat_dong`; gửi kèm mã hoặc field dư trả 422. Không cần If-Match, không nhận query.

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
    C->>R: POST /api/v1/nhan_vien, JWT, body không có mã NV
    R->>A: current_payload(token)
    A->>A: Verify JWT và sub
    A->>N: get_auth_identity(actor_id, pwdv, session_version=pbdn hoặc 0)
    N->>P: get_credentials_by_id(actor_id)
    P->>DB: SELECT NhanVien và VaiTro hiện tại
    DB-->>N: Credentials qua repository
    N->>N: Kiểm tra trạng thái, vai trò, password version
    N-->>A: AuthIdentity hoặc lỗi 401/403
    A-->>R: Actor hiện tại hoặc 401/403
    R->>R: Validate body bắt buộc, mật khẩu, lý do#59; reject mã/query
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
        break Admin mất hiệu lực sau chờ khóa
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 401 phiên cũ/mất account hoặc 403 khóa/hạ quyền
        end
        N->>P: get_role(vai_tro_id)
        P->>DB: SELECT VaiTro
        break Vai trò không tồn tại
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 404 khong_tim_thay
        end
        N->>P: find_by_username(ten_dang_nhap)
        P->>DB: SELECT theo ten_dang_nhap
        break Tên đăng nhập đã có
            N->>T: __aexit__(DuplicateUsernameException)
            T->>DB: ROLLBACK
            R-->>C: 409 ten_dang_nhap_bi_trung
        end
        N->>P: next_employee_code()
        P->>DB: SELECT max(CAST(right(ma_nhan_vien, 6) AS INTEGER)) toàn NhanVien
        P->>P: max+1#59; rỗng bắt đầu NV-000001
        break Vượt NV-999999
            N->>T: __aexit__(InvalidWorkflowState)
            T->>DB: ROLLBACK
            R-->>C: 409 trang_thai_khong_hop_le, Đã hết mã nhân viên khả dụng
        end
        rect rgb(245, 245, 245)
            N->>P: create(NewEmployee)
            P->>DB: INSERT NhanVien hoat_dong, flush, refresh và tải role
            break Unique username/mã vi phạm khi tạo đồng thời
                N->>T: __aexit__(DuplicateUsernameException hoặc DuplicateCodeException)
                T->>DB: ROLLBACK
                R-->>C: 409 ten_dang_nhap_bi_trung hoặc ma_bi_trung (thử lại)
            end
            N->>AU: append tao, actor_id, id mới, hồ sơ an toàn, ly_do
            AU->>AR: append(entry), session.add
            Note over AR,DB: created_at do PostgreSQL đặt mặc định khi lưu
            N->>T: __aexit__(error nếu append lỗi)
            alt Audit/commit lỗi
                T->>DB: ROLLBACK
                R-->>C: 409 constraint / 500 loi_noi_bo, không tạo tài khoản/lịch sử
            else Thành công
                T->>DB: Flush audit và COMMIT
                N-->>R: Profile an toàn và ETag
                R-->>C: 201 data, meta, Location và ETag
            end
        end
    end
```

Location trỏ GET chi tiết mới; ETag từ hồ sơ trả về, meta có `request_id`. Response QTV đủ hồ sơ và vai trò, không chứa mật khẩu/hash hoặc `ly_do`. Không cấp JWT khi tạo; tài khoản mới đăng nhập qua UC-01 và xuất hiện trong danh sách UC-03. Đóng phần nhập trước khi lưu không gửi POST.

- Tài khoản và audit `tao` dùng chung transaction. Audit có người thực hiện, đối tượng mới, thời điểm do DB đặt, lý do tùy chọn; không lưu mật khẩu thô/hash.
- Cấp mã đọc toàn bảng, kể cả tài khoản khóa, dưới khóa dòng của QTV thực hiện. Hai QTV khác nhau có thể lấy cùng mã; unique `ma_nhan_vien` chặn bản ghi sau, trả 409 `ma_bi_trung` với thông báo “Mã nhân viên vừa được cấp cho tài khoản khác, vui lòng thử lại”. Không có retry tự động hoặc trigger cấp mã.
- Username trùng trước cấp mã hoặc lúc INSERT đều trả 409 `ten_dang_nhap_bi_trung`, “Tên đăng nhập đã tồn tại”. Username/mã bất biến sau tạo.
- Thay đổi hợp đồng API: client bỏ `ma_nhan_vien` (gửi trường cũ sẽ nhận 422), mật khẩu từ 6 ký tự, nhận thêm `ly_do` tùy chọn. Caller `EmployeeForm` đã được cập nhật. Không sửa schema/bootstrap hoặc database đang chạy.


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


## DELETE /api/v1/nhan_vien/{id} — Khóa tài khoản (UC-05)

Nguồn: [UC-05](../../specs/use_cases/identity_access/UC-05.md), R1–R7, Main 1–6, A1–A9.
Body `LyDoTuyChonInput` không bắt buộc: thiếu body, `{}`, `{"ly_do":null}` hoặc lý do chỉ khoảng trắng đều được coi là không có lý do; nếu nhập thì trim, tối đa 1000 ký tự. Bắt buộc `If-Match`. Chuyển `hoat_dong` sang `bi_khoa`, giữ nguyên dòng nhân viên, vai trò, hồ sơ, yêu cầu sản xuất đang giao, chứng từ và lịch sử. Không có endpoint xóa hẳn.

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
    C->>R: DELETE /api/v1/nhan_vien/{id}, JWT, body tùy chọn và If-Match
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
        N->>P: lock_admin_role()
        P->>DB: SELECT VaiTro WHERE ma_vai_tro = quan_tri_vien FOR UPDATE
        N->>P: lock_credentials_by_id(admin_id)
        P->>DB: SELECT admin FOR UPDATE và refresh
        N->>N: Recheck account/role/password version
        break Actor mất hiệu lực trong lúc chờ khóa
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 401 / 403
        end
        N->>P: get_for_update(id)
        P->>DB: SELECT nhân viên FOR UPDATE, refresh role
        N->>N: Check tồn tại và ETag
        break Không tồn tại hoặc ETag lỗi
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 404 / 428 / 412
        end
        N->>N: Check đang hoat_dong
        opt Đích là QTV đang hoạt động
            N->>P: count_active_admins()
            P->>DB: COUNT NhanVien JOIN VaiTro, QTV đang hoat_dong
            P-->>N: Số QTV hoạt động
        end
        alt Đích đã khóa hoặc đích là QTV hoạt động cuối cùng
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 409 trang_thai_khong_hop_le / quan_tri_vien_cuoi_cung
        else Điều kiện hợp lệ
            N->>P: set_status(id, bi_khoa)
            P->>DB: UPDATE trạng thái, phien_ban_dang_nhap = phien_ban_dang_nhap + 1 và đọc lại record
            N->>AU: append khoa, hoat_dong → bi_khoa, lý do và snapshot trước/sau
            AU->>AR: append(entry), session.add
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

Thứ tự khóa cố định trong transaction: dòng `VaiTro` QTV → actor → đích. Các thao tác khóa cùng chờ dòng vai trò, sau đó đọc lại quyền actor, trạng thái đích và số QTV hoạt động; không khóa được QTV cuối cùng kể cả khi có thao tác đồng thời. Actor mất hiệu lực sau chờ khóa trả 401/403 và rollback. QTV được khóa QTV khác hoặc tự khóa khi vẫn còn QTV khác đang hoạt động; QTV cuối nhận 409 `quan_tri_vien_cuoi_cung` (“Không khóa được Quản trị viên đang hoạt động cuối cùng”).

Gọi lại với ETag cũ trả 412 `du_lieu_da_thay_doi`; thiếu `If-Match` trả 428 `thieu_if_match`; ETag hiện tại nhưng đã khóa trả 409 `trang_thai_khong_hop_le`, không thêm audit. JWT đã cấp bị từ chối 403 `tai_khoan_bi_vo_hieu_hoa` ở request tiếp theo do xác thực đọc lại trạng thái tài khoản từ DB. FE kiểm tra lại phiên ngay sau tự khóa để kết thúc phiên và chuyển về đăng nhập; không cấp token mới.

Audit `khoa` ghi người thực hiện, đối tượng đích, `trang_thai_truoc=hoat_dong`, `trang_thai_sau=bi_khoa`, lý do đã trim hoặc null và snapshot hồ sơ trước/sau không có mật khẩu/hash. Thời điểm `created_at` do DB đặt. Theo UC-06 D1, khóa tăng `phien_ban_dang_nhap` đúng 1 bằng biểu thức SQL trong cùng transaction với trạng thái và audit; audit/commit lỗi rollback cả ba. Mở khóa không tăng và không khôi phục phiên cũ. Thành công trả 204 không body và ETag mới. Tài khoản vẫn có trong danh sách/lịch sử và hỗ trợ lọc trạng thái. Đóng hộp xác nhận trước khi lưu không gửi DELETE.

Thay đổi hợp đồng API: body/lý do DELETE trở thành tùy chọn, bổ sung lỗi QTV cuối; caller FE đã cập nhật. Không đổi đường dẫn, header, schema/bootstrap hay dữ liệu đang chạy. Test repo giả kiểm tra thứ tự gọi và SQL được biên dịch; chưa kiểm chứng khóa đồng thời trên PostgreSQL thật.


## PUT /api/v1/nhan_vien/{id}/vai_tro — Đổi vai trò (UC-07)

Nguồn: [UC-07](../../specs/use_cases/identity_access/UC-07.md), R1–R8, Main 1–6, A1–A9; D1–D5 trong plan UC-07.

Body `DoiVaiTroInput`: `vai_tro_id` integer dương signed 32-bit bắt buộc; `ly_do` tùy chọn, trim, rỗng thành null, tối đa 1000 ký tự. Field dư/không hợp lệ trả 422. Bắt buộc `If-Match`; không nhận query. Đổi được giữa cả ba vai trò, kể cả tự đổi khi còn QTV khác đang hoạt động.

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
    C->>R: PUT /api/v1/nhan_vien/{id}/vai_tro, JWT, If-Match, vai_tro_id và ly_do
    R->>A: current_payload(token)
    A-->>R: Actor hiện tại hoặc 401/403
    R->>R: Validate path/body và reject query
    alt Auth/input lỗi
        R-->>C: 401 / 403 / 422
    else Request hợp lệ
        R->>N: change_role(id, role_id, actor, If-Match, request_id, reason)
        N->>N: Require admin
        break Actor không là admin
            N-->>R: ForbiddenException
            R-->>C: 403 khong_co_quyen
        end
        N->>T: __aenter__
        N->>P: lock_admin_role()
        P->>DB: SELECT VaiTro QTV FOR UPDATE
        N->>P: lock_credentials_by_id(admin_id)
        P->>DB: SELECT admin FOR UPDATE và refresh
        N->>N: Recheck account/role/password version
        break Actor mất hiệu lực sau chờ khóa
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 401/403 sau recheck
        end
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
        break Vai trò không tồn tại
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 404 khong_tim_thay
        end
        break R7 - Vai trò mới trùng vai trò hiện tại
            N->>T: __aexit__(InvalidWorkflowState)
            T->>DB: ROLLBACK
            R-->>C: 409 trang_thai_khong_hop_le
        end
        opt Đích là QTV hoạt động và vai trò mới khác QTV
            N->>P: count_active_admins()
            P->>DB: COUNT NhanVien QTV hoat_dong
            break R3 - Không còn QTV hoạt động khác
                N->>T: __aexit__(LastActiveAdminException)
                T->>DB: ROLLBACK
                R-->>C: 409 quan_tri_vien_cuoi_cung
            end
        end
        opt Vai trò hiện tại là nhan_vien
            N->>P: count_unfinished_assigned_requests(id)
            P->>DB: SQL Core COUNT YeuCauSanXuat được giao, bốn trạng thái v4
            break R4 - Còn yêu cầu chưa kết thúc
                N->>T: __aexit__(UnfinishedAssignmentException)
                T->>DB: ROLLBACK
                R-->>C: 409 con_yeu_cau_chua_ket_thuc
            end
        end
        N->>P: set_role(id, role_id)
        P->>DB: UPDATE vai_tro_id, phien_ban_dang_nhap = phien_ban_dang_nhap + 1
        P->>DB: SELECT lại hồ sơ và vai trò
        N->>AU: append doi_vai_tro, hồ sơ trước/sau, ly_do
        AU->>AR: append(entry), session.add
        N->>T: __aexit__
        alt Audit/commit lỗi
            T->>DB: ROLLBACK vai trò, phiên bản, audit
            R-->>C: 409 constraint / 500 loi_noi_bo
        else Thành công
            T->>DB: Flush audit và COMMIT
            N-->>R: Profile đầy đủ và ETag
            R-->>C: 200 data, meta và ETag
        end
    end
```

Thứ tự khóa dùng chung với UC-05: dòng `VaiTro` QTV → actor → đích `FOR UPDATE`. Khóa đích chặn giao việc đồng thời vì luồng giao việc khóa nhân viên `FOR SHARE`. Đếm yêu cầu bằng SQL Core trên `"YeuCauSanXuat"`, không dùng ORM v3: `nhan_vien_duoc_giao_id=id` và `trang_thai IN ('nhap','da_gui','cho_bo_sung_linh_kien','dang_thuc_hien')`. `hoan_thanh`, `da_huy` và yêu cầu của người khác không chặn. R4 áp dụng cả NV đang khóa; R3 chỉ tính QTV `hoat_dong`.

Mỗi lần đổi thành công ghi đúng một audit `doi_vai_tro`, cùng transaction với cập nhật vai trò/phiên bản: actor, đích, thời điểm do DB tạo, hồ sơ `du_lieu_truoc/sau` có `vai_tro_id`, `ma_vai_tro`, lý do tùy chọn. `trang_thai_truoc/sau=null` vì trạng thái tài khoản không đổi. Trùng vai trò trả 409, không audit hoặc tăng phiên bản; lỗi lưu rollback cả ba. Response 200 gồm hồ sơ đầy đủ và ETag mới, không trả phiên bản đăng nhập.

Với đích đang hoạt động, mọi JWT cũ bị 401 ở request kế tiếp do claim `pbdn` lệch DB; đăng nhập lại nhận vai trò và phiên bản mới. Đích đang khóa tiếp tục bị 403 khi xác thực. FE tự đổi vai trò thì đăng xuất ngay với thông báo “Đã đổi vai trò. Vui lòng đăng nhập lại.”, dừng các bước lưu sau (kể cả mật khẩu). Đóng phần nhập trước khi lưu không gửi request. Không đổi mật khẩu, trạng thái tài khoản hoặc công việc đang giao.


## POST /api/v1/nhan_vien/{id}/mo_khoa — Mở khóa tài khoản (UC-06)

Nguồn: [UC-06](../../specs/use_cases/identity_access/UC-06.md), R1–R2, Main 1–6, A1–A6; D1–D3 trong plan UC-06.

Body `LyDoTuyChonInput | None` không bắt buộc: thiếu body, `{}`, `{"ly_do":null}`, chuỗi rỗng hoặc chỉ khoảng trắng đều lưu `ly_do=null`; lý do được trim, tối đa 1000 ký tự, field dư/không hợp lệ trả 422. Bắt buộc `If-Match`. Chỉ QTV được chuyển `bi_khoa` sang `hoat_dong`.

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
    C->>R: POST /api/v1/nhan_vien/{id}/mo_khoa, JWT, body tùy chọn và If-Match
    R->>A: current_payload(token)
    A->>N: get_auth_identity(actor_id, pwdv, session_version=pbdn hoặc 0)
    N->>P: get_credentials_by_id(actor_id)
    P->>DB: SELECT NhanVien và VaiTro
    DB-->>N: Credentials qua repository
    N->>N: Kiểm tra active, role, pwdv, pbdn so với DB
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
        break Actor mất hiệu lực sau khi chờ khóa
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 401 / 403
        end
        N->>P: get_for_update(id)
        P->>DB: SELECT nhân viên FOR UPDATE, refresh role
        N->>N: Check tồn tại và ETag
        break Không tồn tại hoặc ETag lỗi
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 404 / 428 / 412
        end
        N->>N: Check đang bi_khoa
        alt Đích đã hoạt động
            N->>T: __aexit__(error)
            T->>DB: ROLLBACK
            R-->>C: 409 trang_thai_khong_hop_le
        else Điều kiện hợp lệ
            N->>P: set_status(id, hoat_dong)
            P->>DB: UPDATE trạng thái, giữ nguyên phiên bản và đọc lại record
            N->>AU: append mo_khoa, bi_khoa → hoat_dong, lý do và snapshot trước/sau
            AU->>AR: append(entry), session.add
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

Audit `thao_tac=mo_khoa` thuộc enum v4; ghi actor, đích, `bi_khoa → hoat_dong`, lý do trim hoặc null và snapshot hồ sơ trước/sau an toàn. Thời điểm `created_at` do DB đặt. Trạng thái và audit commit cùng transaction; lỗi append/commit rollback, không thêm lịch sử, trạng thái và phiên bản giữ nguyên. Đích đã hoạt động trả 409 `trang_thai_khong_hop_le`, ETag cũ trả 412 `du_lieu_da_thay_doi`, thiếu If-Match trả 428 `thieu_if_match`; các nhánh này không ghi audit.

Không cấp JWT mới, không đổi password/role và không tăng `phien_ban_dang_nhap`. Token có từ trước khi khóa mang phiên bản cũ nên vẫn bị từ chối 401 sau mở khóa, kể cả còn hạn và đúng `pwdv`. Người dùng đăng nhập lại bằng mật khẩu hiện có sẽ nhận token với `pbdn` hiện tại và vai trò cũ. Response 200 là hồ sơ đầy đủ cho QTV, `meta.request_id` và ETag mới, không trả phiên bản đăng nhập.

FE giữ hộp xác nhận “Mở khóa tài khoản”, không `danger`, cho phép lý do trống và gửi POST với `{ly_do: lý do trim hoặc null}` cùng ETag đã xem. Đóng/hủy trước khi lưu không gửi request và không đổi trạng thái. QLK/NV bị chặn cả đường dẫn quản trị lẫn lời gọi API trực tiếp (403). Hợp đồng body mở khóa trở thành tùy chọn; không đổi đường dẫn/header, không cập nhật database đang chạy hoặc bootstrap.


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

## POST /api/v1/nhan_vien/{id}/dat_lai_mat_khau — Admin đặt lại mật khẩu

Nguồn: [UC-08 — Đổi mật khẩu tài khoản](../../specs/use_cases/identity_access/UC-08.md), Main 2–6, R1–R7, A1–A6; thay hành vi cũ của D-MK-01 theo D1–D4. Body duy nhất `mat_khau_moi` là SecretStr 6–1024 ký tự, không trim; không nhận mật khẩu hiện tại hoặc field dư/query. Path ID nguyên dương. Không cần lý do, cho phép đích ở mọi vai trò/trạng thái và đích là chính admin. Không có nhánh lỗi nghiệp vụ 409 riêng; vi phạm ràng buộc DB trong transaction vẫn trả 409.

```mermaid
sequenceDiagram
    actor C as Client admin
    participant R as nhan_vien.router và dependencies
    participant A as auth.service
    participant N as nhan_vien.service
    participant P as nhan_vien.repository
    participant U as audit.service và repository
    participant DB as PostgreSQL
    C->>R: POST /api/v1/nhan_vien/{id}/dat_lai_mat_khau, JWT, If-Match, body
    R->>A: current_payload(token)
    A->>A: Verify JWT và sub
    A->>N: get_auth_identity(id actor, credential_version=pwdv, session_version=pbdn hoặc 0)
    N->>P: get_credentials_by_id(id actor)
    P->>DB: SELECT NhanVien và VaiTro
    DB-->>P: Credentials và quyền hiện tại
    P-->>N: Credentials
    alt Thiếu/token lỗi/account mất/pwdv hoặc pbdn cũ
        R-->>C: 401 chua_xac_thuc
    else Actor bị khóa hoặc role không hợp lệ
        R-->>C: 403
    else Xác thực hợp lệ
        N-->>A: AuthIdentity
        A-->>R: Actor hiện tại
        R->>R: reject_query, validate ID và DatLaiMatKhauInput
        alt Query hoặc body hoặc ID không hợp lệ
            R-->>C: 422 du_lieu_khong_hop_le
        else Input hợp lệ
            R->>N: reset_password(id, mật khẩu mới, actor, if_match, request_id)
            N->>N: _require_admin(actor)
            alt Không phải quan_tri_vien
                N-->>C: 403 khong_co_quyen
            else Admin
                N->>N: asyncio.to_thread(get_password_hash, new_password)
                Note over N,DB: Hash trước transaction
                N->>DB: Transaction bắt đầu / tiếp quản session hiện tại
                N->>P: _lock_admin → lock_credentials_by_id(actor.sub)
                P->>DB: SELECT admin FOR UPDATE
                DB-->>P: Credentials sau khi giữ khóa
                P-->>N: Credentials
                N->>N: Kiểm tra lại active, pwdv và quyền admin
                alt Actor mất / pwdv cũ / khóa / mất quyền khi chờ
                    N->>DB: ROLLBACK
                    N-->>C: 401 hoặc 403
                else Actor còn hợp lệ
                    N->>P: _target → get_for_update(id đích)
                    P->>DB: SELECT đích FOR UPDATE
                    DB-->>P: EmployeeRecord hoặc null
                    P-->>N: EmployeeRecord hoặc null
                    alt Không có đích
                        N->>DB: ROLLBACK
                        N-->>C: 404 khong_tim_thay
                    else Thiếu If-Match
                        N->>DB: ROLLBACK
                        N-->>C: 428 thieu_if_match
                    else If-Match khác ETag hiện tại
                        N->>DB: ROLLBACK
                        N-->>C: 412 du_lieu_da_thay_doi
                    else ETag hợp lệ
                        N->>P: set_password_hash(id đích, new_hash)
                        P->>DB: UPDATE NhanVien SET mat_khau=new_hash, phien_ban_dang_nhap=phien_ban_dang_nhap+1
                        N->>U: append(CreationAudit doi_mat_khau)
                        U->>DB: INSERT LichSuThaoTac, cùng session/transaction
                        alt Vi phạm ràng buộc khi ghi hoặc commit
                            N->>DB: ROLLBACK hash, phiên bản và audit
                            R-->>C: 409 trang_thai_khong_hop_le
                        else Cập nhật / audit / commit lỗi khác
                            N->>DB: ROLLBACK hash, phiên bản và audit
                            R-->>C: 500 loi_noi_bo
                        else Thành công
                            N->>DB: COMMIT
                            N->>N: _result(employee, actor, request_id)
                            N-->>R: NhanVienDetailResponse và ETag
                            R-->>C: 200 data, meta.request_id, header ETag
                        end
                    end
                end
            end
        end
    end
```

- Auth và input là dependency FastAPI; khi cùng sai, sơ đồ không quy định ưu tiên lỗi. Các khóa nằm trong cùng transaction/session, kể cả khi khóa đích trùng dòng admin.
- Audit: `nhan_vien_id=admin`, `doi_tuong_id=id đích`, `loai_doi_tuong=nhan_vien`, `thao_tac=doi_mat_khau`, `du_lieu_truoc=null`, `du_lieu_sau={"da_doi_mat_khau": true}`, `ly_do=null`; không mật khẩu/hash/token; thời điểm do `LichSuThaoTac.created_at` mặc định `now()`. Append dùng service audit thực sự có trong code; transaction do service nhân viên sở hữu.
- Response là hồ sơ đầy đủ cho admin, không phân trang, không trả mật khẩu/hash. ETag có thể không đổi vì biểu diễn hồ sơ không chứa hash. Mọi token cũ của đích bị 401 qua kiểm tra `pwdv`/`pbdn` ở request sau; phiên bản tăng đúng 1 trong cùng UPDATE với hash và cùng transaction với audit; tài khoản khóa vẫn bị khóa.
- FE lưu hồ sơ → vai trò → reset; tự đổi mật khẩu thành công gọi `logout("Đã đổi mật khẩu. Vui lòng đăng nhập lại.")` rồi dừng trước cache/refetch, chuyển về `/dang-nhap`; đổi cho người khác giữ phiên QTV, cập nhật cache và báo thành công. Không tự đăng nhập lại hoặc cấp token mới. Đóng phần nhập/hủy xác nhận không gửi request (A5); lưu lỗi giữ mật khẩu, phiên bản và lịch sử cũ (A6).
