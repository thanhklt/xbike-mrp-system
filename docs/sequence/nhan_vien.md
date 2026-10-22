# Sequence diagram — nhan_vien

Nguồn triển khai: `backend/app/modules/nhan_vien/{router,service,write_service,schemas,dto,ports,repository,models,errors}.py`,
`backend/app/dependencies.py`,
`backend/app/modules/auth/{service,repository}.py`, `backend/app/core/security.py`,
`backend/app/core/exceptions.py` và `backend/app/main.py`.
Đối chiếu quyền truy cập với `api-contract-v2.md` trên Google Drive của project.

`main.py` đăng ký tám endpoint từ hai router trong `nhan_vien.router`. Module sở hữu
ORM `User` và `Role`, được dùng chung với xác thực. Giữ nguyên schema hiện tại;
backend cấp ID và kiểm tra trạng thái trong service/repository, không tạo migration.

Quyết định đã chốt với dev ngày 20/10/2026, bổ sung/thay thế contract v2:
- DELETE chỉ dành cho Admin và là soft delete: chuyển `bi_khoa`, giữ bản ghi, mã và toàn bộ tham chiếu;
  tài khoản khóa vẫn xuất hiện trong GET và lịch sử. Không có kiểm tra chặn theo tham chiếu để xóa vật lý.
- PATCH cho phép Admin sửa hồ sơ hoặc chính chủ sửa `ho_ten`, `ngay_sinh`, `so_dien_thoai`, `email`.
  Chỉ Admin sửa `ngay_vao_lam`, `he_so_luong`; gửi trường vượt quyền từ chối toàn request bằng 403.
- Giữ đúng sáu API mới được yêu cầu; chưa có endpoint mở khóa trong module.

Nhóm API này dùng envelope v2 `{data, meta}` / `{error, meta}`; validation chỉ trả
`{field, reason}`, không echo input. Lỗi DB trả 503, lỗi chưa phân loại trả 500 và không lộ SQL.
Thiếu/token sai hoặc account không tồn tại trả 401; account khác `hoat_dong` trả 403.

`get_employee_repository` tạo `SqlAlchemyEmployeeRepository` từ session do `get_db` cung cấp.
Router truyền repository vào service theo hợp đồng `EmployeeRepository` trong `ports.py`.
Port là hợp đồng kiểu dữ liệu, không phải một tầng xử lý riêng khi chạy.
Repository tải quan hệ `User.role` (`lazy="selectin"`) rồi chuyển ORM thành `EmployeeData`
trước khi trả về. Service chỉ đọc DTO, không nhận ORM hoặc `AsyncSession`.
Các sơ đồ gom SELECT tải vai trò vào lời gọi database tương ứng.
Các nhánh validation mô tả kết quả khi xác thực thành công; không quy định thứ tự
ưu tiên lỗi nếu request đồng thời sai xác thực và đầu vào.

## GET /api/v1/nhan_vien — Lấy danh sách nhân viên

Query: `page` (mặc định 1, tối thiểu 1), `page_size` (mặc định 20, từ 1 đến 100),
`q`, `vai_tro_id` (số nguyên dương), `trang_thai` (`hoat_dong | bi_khoa`), `sort`
(mặc định `id`; hỗ trợ `id`, `ma_nhan_vien`, `ho_ten`, `ten_dang_nhap`, thêm `-` để giảm dần).
`q` tìm không phân biệt hoa thường theo mã nhân viên hoặc họ tên, escape ký tự wildcard.
Query lặp hoặc tham số không được khai báo bị từ chối.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI / nhan_vien.router
    participant Auth as dependencies / AuthService
    participant AuthRepo as SqlAlchemyAuthRepository
    participant Service as nhan_vien.service
    participant EmployeeRepo as SqlAlchemyEmployeeRepository
    participant DB as PostgreSQL

    Client->>API: GET /api/v1/nhan_vien + query, Bearer JWT
    API->>Auth: get_current_user_payload()
    Auth->>Auth: Kiểm tra token và sub
    alt Thiếu token, token lỗi hoặc sub không hợp lệ
        Auth-->>API: Lỗi xác thực
        API-->>Client: 401 Unauthorized
    else Token hợp lệ
        Auth->>AuthRepo: get_by_id(sub)
        AuthRepo->>DB: Lấy nhân viên theo sub và vai trò hiện tại
        DB-->>AuthRepo: Nhân viên và vai trò
        AuthRepo-->>Auth: AuthEmployee hoặc không có bản ghi
        alt Không tồn tại
            Auth-->>API: UnauthorizedException
            API-->>Client: 401 chua_xac_thuc
        else Trạng thái khác hoat_dong
            Auth-->>API: InactiveAccountException
            API-->>Client: 403 tai_khoan_bi_vo_hieu_hoa
        else Tài khoản hoạt động
            Auth->>Auth: Lấy roles từ database
            Auth-->>API: actor
            API->>API: get_list_query(), validate DanhSachNhanVienRequest
            alt Query không hợp lệ
                API-->>Client: 422 du_lieu_khong_hop_le
            else Query hợp lệ
                API->>API: Lấy hoặc tạo request_id
                API->>API: Nhận repo qua Depends(get_employee_repository)
                API->>Service: list_employees(repo, params, actor, request_id)
                alt Không có quyền quan_tri_vien hoặc quan_ly
                    Service-->>API: ForbiddenException
                    API-->>Client: 403 khong_co_quyen
                else Có quyền xem danh sách
                    Service->>Service: Tạo EmployeeListQuery từ params đã validate
                    Service->>EmployeeRepo: list(query)
                    EmployeeRepo->>EmployeeRepo: Tạo bộ lọc q, vai_tro_id, trang_thai
                    EmployeeRepo->>DB: COUNT theo bộ lọc
                    DB-->>EmployeeRepo: total
                    EmployeeRepo->>EmployeeRepo: offset = (page - 1) * page_size
                    alt offset nhỏ hơn total
                        EmployeeRepo->>DB: SELECT theo bộ lọc, ORDER BY sort và id, OFFSET, LIMIT
                        DB-->>EmployeeRepo: records cùng quan hệ role
                        EmployeeRepo->>EmployeeRepo: Chuyển từng ORM thành EmployeeData
                    else Trang không có dữ liệu
                        EmployeeRepo->>EmployeeRepo: items = ()
                    end
                    EmployeeRepo-->>Service: EmployeePage(items, total)
                    loop Mỗi EmployeeData trong items
                        alt actor có quyền quan_tri_vien
                            Service->>Service: _employee_response() chọn trường giao việc và hồ sơ
                        else actor có quyền quan_ly
                            Service->>Service: _employee_response() chỉ chọn trường giao việc
                        end
                        Service->>Service: Validate dữ liệu đã chọn bằng ChiTietNhanVien
                    end
                    Service-->>API: DanhSachNhanVienResponse(data, meta)
                    API->>API: Serialize với response_model_exclude_unset=True
                    API-->>Client: 200 OK, JSON data và meta
                end
            end
        end
    end
```

- `meta`: `request_id`, `page`, `page_size`, `total`, `total_pages = ceil(total / page_size)`.
- Trang vượt kết quả trả `200` với `data: []`; không trả `404`. Khi `total = 0`, `total_pages = 0`.
- `vai_tro_id` lớn hơn số nguyên signed 32-bit được chuyển thành điều kiện không khớp bản ghi.
- Cả hai vai trò dùng một schema `ChiTietNhanVien`; service chọn trường theo quyền.
  Quản trị viên nhận hồ sơ đầy đủ; quản lý chỉ nhận:
  `id`, `ma_nhan_vien`, `ho_ten`, `vai_tro_id`, `ma_vai_tro`, `trang_thai`.
- Không trả `mat_khau` hoặc `tai_khoan_id`.
- Các trường hồ sơ có mặc định `None` để hỗ trợ dữ liệu giới hạn. Service không truyền
  chúng khi người gọi không có quyền; router dùng `response_model_exclude_unset=True`
  để bỏ hoàn toàn khỏi JSON. Trường được service truyền rõ ràng với giá trị `None`
  vẫn được trả về dưới dạng `null`, kể cả trường chung như `ho_ten` và `ma_vai_tro`.
- OpenAPI mô tả một `ChiTietNhanVien` với các trường hồ sơ không bắt buộc;
  tập trường thực tế phụ thuộc quyền của người gọi.

## GET /api/v1/nhan_vien/{id} — Lấy chi tiết nhân viên

`id` phải là số nguyên dương. Endpoint không nhận bất kỳ query parameter nào.
Quản trị viên và quản lý được xem nhân viên khác; nhân viên thông thường chỉ được xem chính mình.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI / nhan_vien.router
    participant Auth as dependencies / AuthService
    participant AuthRepo as SqlAlchemyAuthRepository
    participant Service as nhan_vien.service
    participant EmployeeRepo as SqlAlchemyEmployeeRepository
    participant DB as PostgreSQL

    Client->>API: GET /api/v1/nhan_vien/{id}, Bearer JWT
    API->>Auth: get_current_user_payload()
    Auth->>Auth: Kiểm tra token và sub
    alt Thiếu token, token lỗi hoặc sub không hợp lệ
        Auth-->>API: Lỗi xác thực
        API-->>Client: 401 Unauthorized
    else Token hợp lệ
        Auth->>AuthRepo: get_by_id(sub)
        AuthRepo->>DB: Lấy nhân viên theo sub và vai trò hiện tại
        DB-->>AuthRepo: Nhân viên và vai trò
        AuthRepo-->>Auth: AuthEmployee hoặc không có bản ghi
        alt Không tồn tại
            Auth-->>API: UnauthorizedException
            API-->>Client: 401 chua_xac_thuc
        else Trạng thái khác hoat_dong
            Auth-->>API: InactiveAccountException
            API-->>Client: 403 tai_khoan_bi_vo_hieu_hoa
        else Tài khoản hoạt động
            Auth->>Auth: Lấy roles từ database
            Auth-->>API: actor
            API->>API: Validate id và validate_detail_query()
            alt id không hợp lệ hoặc có query parameter
                API-->>Client: 422 du_lieu_khong_hop_le
            else Đầu vào hợp lệ
                API->>API: Lấy hoặc tạo request_id
                API->>API: Nhận repo qua Depends(get_employee_repository)
                API->>Service: get_employee(repo, id, actor, request_id)
                Service->>EmployeeRepo: get_by_id(id)
                alt id lớn hơn 2147483647
                    EmployeeRepo-->>Service: None, không truy vấn nhân viên đích
                else id trong giới hạn
                    EmployeeRepo->>DB: SELECT nhân viên đích theo id
                    DB-->>EmployeeRepo: user cùng role hoặc không có bản ghi
                    alt Có nhân viên đích
                        EmployeeRepo->>EmployeeRepo: Chuyển ORM thành EmployeeData
                        EmployeeRepo-->>Service: EmployeeData
                    else Không tìm thấy nhân viên đích
                        EmployeeRepo-->>Service: None
                    end
                end
                alt Repository trả None
                    Service-->>API: NotFoundException
                    API-->>Client: 404 khong_tim_thay
                else Có EmployeeData
                    alt Không phải quản trị viên, quản lý hoặc chính mình
                        Service-->>API: ForbiddenException
                        API-->>Client: 403 khong_co_quyen
                    else Có quyền xem
                        alt Quản trị viên hoặc đang xem chính mình
                            Service->>Service: _employee_response(detail=True) chọn trường giao việc và hồ sơ
                        else Quản lý xem người khác
                            Service->>Service: _employee_response(detail=True) chỉ chọn trường giao việc
                        end
                        Service->>Service: Validate dữ liệu đã chọn bằng ChiTietNhanVien
                        Service->>Service: SHA-256 của profile.model_dump_json(exclude_unset=True) tạo strong ETag
                        Service-->>API: ChiTietNhanVienResponse và etag
                        API->>API: Gán response.headers.ETag
                        API->>API: Serialize với response_model_exclude_unset=True
                        API-->>Client: 200 OK, JSON data và meta, header ETag
                    end
                end
            end
        end
    end
```

- `meta` chỉ chứa `request_id`. ETag có dấu ngoặc kép, được tính từ hồ sơ trả về,
  không bao gồm `meta`, nên không đổi chỉ vì `request_id` thay đổi.
- Code hiện tại trả `200` kèm ETag; chưa xử lý `If-None-Match` để trả `304`.
- Kiểm tra tồn tại nhân viên đích diễn ra trước kiểm tra quyền xem: ID không tồn tại trả `404`,
  nhân viên tồn tại nhưng ngoài quyền truy cập trả `403`.
- `ChiTietNhanVien` gồm các trường giao việc và các trường hồ sơ `ten_dang_nhap`,
  `ngay_sinh`, `so_dien_thoai`, `email`, `ngay_vao_lam`, `he_so_luong`.
  Service chỉ điền các trường hồ sơ khi quản trị viên hoặc người xem chính mình;
  quản lý xem người khác nhận sáu trường giao việc giống endpoint danh sách.
  Không trả mật khẩu hoặc `tai_khoan_id`.
- ETag chỉ bao gồm các trường thực sự trả về. Thay đổi email/hệ số lương không
  làm đổi ETag của quản lý xem người khác; thay đổi trường giao việc vẫn làm đổi ETag.
- Hai endpoint chỉ đọc, không có transaction ghi dữ liệu.

## POST /api/v1/nhan_vien — Tạo tài khoản

Bắt buộc `ten_dang_nhap`, `mat_khau` tối thiểu 8 ký tự, `ma_nhan_vien`, `vai_tro_id`.
Hồ sơ nullable: `ho_ten`, `ngay_sinh`, `so_dien_thoai`, `email`, `ngay_vao_lam`, `he_so_luong`.
Hệ số lương là JSON string decimal không âm, tối đa 5 chữ số và 2 chữ số thập phân.
Không nhận ID, trạng thái, `tai_khoan_id` hay trường lạ. Mã/tên đăng nhập do client gửi, duy nhất và bất biến.

```mermaid
sequenceDiagram
    actor Client
    participant API as nhan_vien.router
    participant Auth as AuthService + SqlAlchemyAuthRepository
    participant Writer as EmployeeWriter
    participant Repo as SqlAlchemyEmployeeRepository
    participant Audit as SqlAlchemyAuditRepository
    participant Tx as SqlAlchemyTransaction
    participant DB as PostgreSQL
    Client->>API: POST /api/v1/nhan_vien, JSON + Bearer
    API->>Auth: Xác thực JWT, đọc account và quyền hiện tại từ DB
    alt JWT thiếu/sai hoặc account không tồn tại
        API-->>Client: 401 chua_xac_thuc
    else Account bị khóa
        API-->>Client: 403 tai_khoan_bi_vo_hieu_hoa
    else Input/query không hợp lệ
        API-->>Client: 422 du_lieu_khong_hop_le
    else Input hợp lệ
        API->>Writer: create(...)
        alt Không phải Admin
            Writer-->>API: 403 khong_co_quyen
        else Admin
            Writer->>Writer: Hash Argon2id trên worker thread
            Writer->>Tx: Bắt đầu thao tác atomic
            Writer->>Repo: lock_writes(), get_for_update(actor)
            Repo->>DB: Advisory transaction lock, khóa và đọc lại actor
            alt Actor mất quyền hoặc bị khóa trong lúc chờ
                Writer-->>API: 403, rollback
            else Actor còn quyền
                Writer->>Repo: get_role(vai_tro_id)
                Repo->>DB: SELECT vai_tro
                alt Vai trò không tồn tại hoặc mã vai trò sai
                    Writer-->>API: 404 hoặc 422, rollback
                else Vai trò hợp lệ
                    Writer->>Repo: create(NewEmployee)
                    Repo->>DB: Lấy MAX(id) dưới advisory lock, INSERT ID mới và trang_thai=hoat_dong, flush
                    alt Trùng tên đăng nhập hoặc mã
                        Repo-->>API: 409 ma_bi_trung, rollback
                    else Tạo được tài khoản
                        Repo-->>Writer: EmployeeData không có credentials
                        Writer->>Audit: append(tao, du_lieu_sau)
                        Audit->>DB: Thêm audit trong cùng session
                        Writer->>Tx: COMMIT account và audit
                        Writer-->>API: Hồ sơ, request_id, ETag
                        API-->>Client: 201, Location chi tiết, ETag, data/meta
                    end
                end
            end
        end
    end
```

Không có If-Match khi tạo. Audit/commit thất bại rollback cả tài khoản.
Mật khẩu, hash và token không xuất hiện trong response, audit hoặc SQL parameter logs.

## PATCH /api/v1/nhan_vien/{id} — Sửa hồ sơ

Chỉ nhận các trường hồ sơ nullable của Create. Trường bỏ qua giữ nguyên, `null` xóa giá trị nullable.
Không nhận mật khẩu, tên đăng nhập, mã nhân viên, vai trò hoặc trạng thái.

```mermaid
sequenceDiagram
    actor Client
    participant API as nhan_vien.router
    participant Auth as AuthService + SqlAlchemyAuthRepository
    participant Writer as EmployeeWriter
    participant Repo as SqlAlchemyEmployeeRepository
    participant Audit as SqlAlchemyAuditRepository
    participant Tx as SqlAlchemyTransaction
    participant DB as PostgreSQL
    Client->>API: PATCH /api/v1/nhan_vien/{id}, Bearer, If-Match, JSON
    API->>Auth: Xác thực, đọc account và vai trò từ DB
    alt JWT lỗi hoặc account không tồn tại
        API-->>Client: 401
    else Account bị khóa
        API-->>Client: 403
    else ID/body/query không hợp lệ
        API-->>Client: 422
    else Input hợp lệ
        API->>Writer: patch(id, chỉ các trường được gửi, actor, If-Match)
        Writer->>Tx: Bắt đầu thao tác atomic
        Writer->>Repo: Advisory lock, khóa và đọc lại actor
        Repo->>DB: pg_advisory_xact_lock, SELECT FOR UPDATE
        alt Actor bị khóa, không phải Admin/chính chủ, hoặc gửi trường vượt quyền
            Writer-->>API: 403, rollback toàn request
        else Được sửa
            Writer->>Repo: get_for_update(id)
            Repo->>DB: SELECT FOR UPDATE nhân viên đích và tải role
            alt Không có nhân viên
                Writer-->>API: 404, rollback
            else Thiếu If-Match
                Writer-->>API: 428 thieu_if_match, rollback
            else ETag không khớp hồ sơ đầy đủ của Admin/chính chủ
                Writer-->>API: 412 du_lieu_da_thay_doi, rollback
            else Đúng phiên bản
                Writer->>Repo: update_profile(chỉ các trường đã gửi)
                Repo->>DB: UPDATE, flush, đọc snapshot mới
                opt Có trường được gửi
                    Writer->>Audit: append(sua, trước/sau)
                    Audit->>DB: INSERT audit
                end
                Writer->>Tx: COMMIT
                Writer-->>API: Hồ sơ đầy đủ, request_id, ETag mới
                API-->>Client: 200 data/meta, ETag
            end
        end
    end
```

Request `{}` vẫn kiểm tra quyền/ETag, trả hồ sơ hiện tại và không ghi audit.
Admin được sửa cả ngày vào làm/hệ số lương; mọi vai trò được tự sửa bốn trường đã chốt.

## DELETE /api/v1/nhan_vien/{id} — Xóa mềm bằng trạng thái bi_khoa

Không xóa bản ghi, không giải phóng mã/tên đăng nhập và không tác động chứng từ hoặc kho.
Không yêu cầu body/lý do. If-Match phải là ETag mới nhất từ GET của Admin.

```mermaid
sequenceDiagram
    actor Client
    participant API as nhan_vien.router
    participant Auth as AuthService + SqlAlchemyAuthRepository
    participant Writer as EmployeeWriter
    participant Repo as SqlAlchemyEmployeeRepository
    participant Audit as SqlAlchemyAuditRepository
    participant Tx as SqlAlchemyTransaction
    participant DB as PostgreSQL
    Client->>API: DELETE /api/v1/nhan_vien/{id}, Bearer, If-Match
    API->>Auth: Xác thực và đọc quyền hiện tại
    alt JWT lỗi/account không tồn tại
        API-->>Client: 401
    else Bị khóa hoặc không phải Admin
        API-->>Client: 403
    else ID/query sai
        API-->>Client: 422
    else Request hợp lệ
        API->>Writer: soft_delete(id, actor, If-Match)
        Writer->>Tx: Bắt đầu thao tác atomic
        Writer->>Repo: Advisory lock, khóa và đọc lại actor/target
        Repo->>DB: pg_advisory_xact_lock, SELECT FOR UPDATE
        alt Actor mất quyền/bị khóa
            Writer-->>API: 403, rollback
        else Target không tồn tại
            Writer-->>API: 404, rollback
        else Thiếu hoặc sai If-Match
            Writer-->>API: 428 hoặc 412, rollback
        else Tự khóa tài khoản đang gọi
            Writer-->>API: 409 khong_the_tu_khoa, rollback
        else Target đã bi_khoa
            Writer->>Tx: Kết thúc không thay đổi, không audit lặp
            API-->>Client: 204, không body
        else Target hoạt động
            Writer->>Repo: active_admin_count() nếu target là Admin
            Repo->>DB: COUNT Admin hoat_dong dưới advisory lock
            alt Là Admin cuối cùng
                Writer-->>API: 409 quan_tri_vien_cuoi_cung, rollback
            else Được phép khóa
                Writer->>Repo: set_status(id, bi_khoa)
                Repo->>DB: UPDATE, flush
                Writer->>Audit: append(vo_hieu_hoa, trước/sau, lý do null)
                Audit->>DB: INSERT audit
                Writer->>Tx: COMMIT
                API-->>Client: 204, không body
            end
        end
    end
```

Gọi lại vẫn phải gửi If-Match hiện tại: dùng ETag trước lần khóa vẫn trả 412.
JWT đã cấp cho tài khoản khóa bị chặn ở request sau; không cần thu hồi token để có hiệu lực.

## PUT /api/v1/nhan_vien/{id}/vai_tro — Đổi vai trò

Body duy nhất `{vai_tro_id: integer dương}`. Quyền chỉ từ vai trò hiện tại trong database.

```mermaid
sequenceDiagram
    actor Client
    participant API as nhan_vien.router
    participant Auth as AuthService + SqlAlchemyAuthRepository
    participant Writer as EmployeeWriter
    participant Repo as SqlAlchemyEmployeeRepository
    participant Audit as SqlAlchemyAuditRepository
    participant Tx as SqlAlchemyTransaction
    participant DB as PostgreSQL
    Client->>API: PUT /api/v1/nhan_vien/{id}/vai_tro, Bearer, If-Match, JSON
    API->>Auth: Xác thực, lấy vai trò hiện tại từ DB
    alt JWT lỗi/account không tồn tại
        API-->>Client: 401
    else Account bị khóa hoặc không phải Admin
        API-->>Client: 403
    else ID/body/query không hợp lệ
        API-->>Client: 422
    else Input hợp lệ
        API->>Writer: change_role(id, vai_tro_id, actor, If-Match)
        Writer->>Tx: Bắt đầu thao tác atomic
        Writer->>Repo: Advisory lock, khóa/đọc lại actor và target
        Repo->>DB: SELECT FOR UPDATE
        alt Actor mất quyền/bị khóa
            Writer-->>API: 403, rollback
        else Target không tồn tại
            Writer-->>API: 404, rollback
        else Thiếu hoặc sai If-Match
            Writer-->>API: 428 hoặc 412, rollback
        else ETag đúng
            Writer->>Repo: get_role(vai_tro_id)
            Repo->>DB: SELECT vai_tro
            alt Vai trò không tồn tại hoặc mã vai trò sai
                Writer-->>API: 404 hoặc 422, rollback
            else Vai trò không đổi
                Writer->>Tx: COMMIT không audit lặp
                API-->>Client: 200 hồ sơ, ETag hiện tại
            else Vai trò thay đổi
                Writer->>Repo: Kiểm tra active_admin_count() khi thu quyền Admin
                Repo->>DB: COUNT Admin hoạt động
                alt Hạ quyền Admin cuối cùng
                    Writer-->>API: 409 quan_tri_vien_cuoi_cung, rollback
                else Được đổi quyền
                    Writer->>Repo: set_role(id, vai_tro_id)
                    Repo->>DB: UPDATE, flush, tải lại quan hệ role
                    opt Có vai trò cũ
                        Writer->>Audit: append(thu_hoi_quyen, trước/sau)
                    end
                    Writer->>Audit: append(cap_quyen, trước/sau)
                    Audit->>DB: INSERT các audit trong cùng transaction
                    Writer->>Tx: COMMIT
                    API-->>Client: 200 hồ sơ, ETag mới
                end
            end
        end
    end
```

## POST /api/v1/nhan_vien/{id}/vo_hieu_hoa — Khóa có lý do

Body `{ly_do: string}` bắt buộc, trim và không được rỗng. Chỉ chuyển `hoat_dong → bi_khoa`.

```mermaid
sequenceDiagram
    actor Client
    participant API as nhan_vien.router
    participant Auth as AuthService + SqlAlchemyAuthRepository
    participant Writer as EmployeeWriter
    participant Repo as SqlAlchemyEmployeeRepository
    participant Audit as SqlAlchemyAuditRepository
    participant Tx as SqlAlchemyTransaction
    participant DB as PostgreSQL
    Client->>API: POST /api/v1/nhan_vien/{id}/vo_hieu_hoa, Bearer, If-Match, ly_do
    API->>Auth: Xác thực và lấy quyền từ DB
    alt JWT lỗi/account không tồn tại
        API-->>Client: 401
    else Account bị khóa hoặc không phải Admin
        API-->>Client: 403
    else ID/query/body/lý do không hợp lệ
        API-->>Client: 422
    else Input hợp lệ
        API->>Writer: disable(id, ly_do, actor, If-Match)
        Writer->>Tx: Bắt đầu thao tác atomic
        Writer->>Repo: Advisory lock, khóa/đọc lại actor và target
        Repo->>DB: pg_advisory_xact_lock, SELECT FOR UPDATE
        alt Actor mất quyền/bị khóa
            Writer-->>API: 403, rollback
        else Target không tồn tại
            Writer-->>API: 404, rollback
        else Thiếu hoặc sai If-Match
            Writer-->>API: 428 hoặc 412, rollback
        else Tự khóa
            Writer-->>API: 409 khong_the_tu_khoa, rollback
        else Target không hoat_dong
            Writer-->>API: 409 trang_thai_khong_hop_le, rollback
        else Trạng thái hợp lệ
            Writer->>Repo: Kiểm tra active_admin_count() nếu target là Admin
            Repo->>DB: COUNT Admin hoạt động
            alt Là Admin cuối cùng
                Writer-->>API: 409 quan_tri_vien_cuoi_cung, rollback
            else Được khóa
                Writer->>Repo: set_status(id, bi_khoa)
                Repo->>DB: UPDATE và flush
                Writer->>Audit: append(vo_hieu_hoa, trước/sau, ly_do)
                Audit->>DB: INSERT audit
                Writer->>Tx: COMMIT
                API-->>Client: 200 hồ sơ, ETag mới, data/meta
            end
        end
    end
```

## GET /api/v1/vai_tro — Danh sách vai trò

Query chỉ gồm `page` (>=1, mặc định 1), `page_size` (1..100, mặc định 20).
Không nhận query lặp/thừa. Sắp xếp ID tăng dần, trang vượt phạm vi trả danh sách rỗng.

```mermaid
sequenceDiagram
    actor Client
    participant API as nhan_vien.role_router
    participant Auth as AuthService + SqlAlchemyAuthRepository
    participant Service as nhan_vien.service
    participant Repo as SqlAlchemyEmployeeRepository
    participant DB as PostgreSQL
    Client->>API: GET /api/v1/vai_tro, query, Bearer
    API->>Auth: Xác thực, đọc account và role hiện tại từ DB
    alt JWT lỗi/account không tồn tại
        API-->>Client: 401
    else Account bị khóa
        API-->>Client: 403
    else Query không hợp lệ
        API-->>Client: 422
    else Input hợp lệ
        API->>Service: list_roles(repo, page, page_size, actor, request_id)
        alt Không phải Admin hoặc Quản lý
            Service-->>API: 403 khong_co_quyen
        else Có quyền
            Service->>Repo: list_roles(page, page_size)
            Repo->>DB: COUNT vai_tro
            opt Trang nằm trong kết quả
                Repo->>DB: SELECT vai_tro ORDER BY id, OFFSET, LIMIT
            end
            Repo-->>Service: RolePage
            Service-->>API: data gồm id, ma_vai_tro, ten_vai_tro và meta phân trang
            API-->>Client: 200 data/meta
        end
    end
```

## Schema và kiểm chứng

- Source v3 đã đối chiếu: DBML được liên kết trong `api-contract-v2.md`, schema PostgreSQL hiện tại.
  `infra/postgres/init.sql` còn model cũ (`loai_nhan_vien`), không phải nguồn bootstrap v3 hợp lệ.
- Theo yêu cầu dev: không tạo migration hoặc thay đổi schema. ID nhân viên không có identity/sequence;
  repository lấy MAX(id)+1 dưới cùng advisory transaction lock với mọi API ghi nhân viên, giữ khóa
  đến commit và kiểm tra giới hạn signed 32-bit. Các lần tạo đồng thời qua API không trùng ID.
  Tiến trình ghi trực tiếp bằng SQL ngoài API phải phối hợp cùng khóa/cơ chế cấp ID; khóa advisory
  không tự ép các client SQL khác tuân thủ. PK/UNIQUE của database vẫn chặn dữ liệu trùng.
- Backend đặt `hoat_dong` khi tạo và kiểm tra trạng thái trên mỗi request; không tự sửa dữ liệu cũ.
  Dữ liệu NULL/trạng thái lạ vẫn bị từ chối xác thực. Giữ bộ xác minh Argon2id/bcrypt khi rollback code
  để các tài khoản đã tạo tiếp tục đăng nhập được; không có bước downgrade schema trong tác vụ này.
- Unit/API dùng SQLite riêng; concurrency dùng database có tên bắt đầu `xbike_employee_test_` và
  tạo schema riêng mỗi lượt để các kết nối thấy fixture, không reset/xóa dữ liệu hoặc database có sẵn.
- Chạy trong `backend`: `poetry run pytest -q`, `poetry run ruff check .`, `poetry run ruff format --check .`.
  Đặt `EMPLOYEE_TEST_DATABASE_URL` tới DB test chuyên biệt để chạy thêm `test_nhan_vien_postgres.py`.
- Các nhánh lỗi audit/commit rollback mọi cập nhật; lỗi SQL trả 503, lỗi khác trả 500 theo envelope v2.
  Thứ tự validation và auth không cam kết khi request đồng thời sai nhiều điều kiện.
