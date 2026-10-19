# Sequence diagram — nhan_vien

Nguồn triển khai: `backend/app/modules/nhan_vien/{router,service,schemas,dto,ports,repository,models}.py`,
`backend/app/dependencies.py`,
`backend/app/modules/auth/{service,repository}.py`, `backend/app/core/security.py`,
`backend/app/core/exceptions.py` và `backend/app/main.py`.
Đối chiếu quyền truy cập với `api-contract-v2.md` trên Google Drive của project.

`main.py` đăng ký hai endpoint từ `nhan_vien.router`. Module `nhan_vien.models`
sở hữu ORM `User` và `Role`, được dùng chung với xác thực. Việc chuyển module không đổi schema database.

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
        alt Không tồn tại hoặc trạng thái khác hoat_dong
            Auth-->>API: UnauthorizedException
            API-->>Client: 401 UNAUTHORIZED
        else Tài khoản hoạt động
            Auth->>Auth: Lấy roles từ database
            Auth-->>API: actor
            API->>API: get_list_query(), validate DanhSachNhanVienRequest
            alt Query không hợp lệ
                API-->>Client: 422 VALIDATION_ERROR
            else Query hợp lệ
                API->>API: Lấy hoặc tạo request_id
                API->>API: Nhận repo qua Depends(get_employee_repository)
                API->>Service: list_employees(repo, params, actor, request_id)
                alt Không có quyền quan_tri_vien hoặc quan_ly
                    Service-->>API: ForbiddenException
                    API-->>Client: 403 FORBIDDEN
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
        alt Không tồn tại hoặc trạng thái khác hoat_dong
            Auth-->>API: UnauthorizedException
            API-->>Client: 401 UNAUTHORIZED
        else Tài khoản hoạt động
            Auth->>Auth: Lấy roles từ database
            Auth-->>API: actor
            API->>API: Validate id và validate_detail_query()
            alt id không hợp lệ hoặc có query parameter
                API-->>Client: 422 VALIDATION_ERROR
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
                    API-->>Client: 404 NOT_FOUND
                else Có EmployeeData
                    alt Không phải quản trị viên, quản lý hoặc chính mình
                        Service-->>API: ForbiddenException
                        API-->>Client: 403 FORBIDDEN
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
