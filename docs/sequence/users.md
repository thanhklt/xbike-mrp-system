# Sequence diagram — users

Nguồn triển khai: `backend/app/modules/users/{router,service,schemas,models}.py`,
`backend/app/core/security.py`, `backend/app/core/exceptions.py` và `backend/app/main.py`.
Đối chiếu quyền truy cập với `api-contract-v2.md` trên Google Drive của project.

Các sơ đồ gom thao tác SQLAlchemy và tải quan hệ `User.role` (`lazy="selectin"`)
vào lời gọi database tương ứng. FastAPI cung cấp `AsyncSession` qua `get_db`.
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
    participant API as FastAPI / users.router
    participant Auth as security.py
    participant Service as users.service
    participant DB as PostgreSQL

    Client->>API: GET /api/v1/nhan_vien + query, Bearer JWT
    API->>Auth: get_current_user_payload()
    Auth->>Auth: Kiểm tra token và sub
    alt Thiếu token, token lỗi hoặc sub không hợp lệ
        Auth-->>API: Lỗi xác thực
        API-->>Client: 401 Unauthorized
    else Token hợp lệ
        Auth->>DB: Lấy nhân viên theo sub và vai trò hiện tại
        DB-->>Auth: Nhân viên và vai trò
        alt Không tồn tại hoặc trạng thái khác hoat_dong
            Auth-->>API: UnauthorizedException
            API-->>Client: 401 UNAUTHORIZED
        else Tài khoản hoạt động
            Auth->>Auth: Lấy roles từ database
            Auth-->>API: actor
            API->>API: get_list_query(), validate NhanVienListQuery
            alt Query không hợp lệ
                API-->>Client: 422 VALIDATION_ERROR
            else Query hợp lệ
                API->>API: Lấy hoặc tạo request_id
                API->>Service: list_employees(db, params, actor, request_id)
                alt Không có quyền quan_tri_vien hoặc quan_ly
                    Service-->>API: ForbiddenException
                    API-->>Client: 403 FORBIDDEN
                else Có quyền xem danh sách
                    Service->>Service: Tạo bộ lọc q, vai_tro_id, trang_thai
                    Service->>DB: COUNT theo bộ lọc
                    DB-->>Service: total
                    Service->>Service: offset = (page - 1) * page_size
                    alt offset nhỏ hơn total
                        Service->>DB: SELECT theo bộ lọc, ORDER BY sort và id, OFFSET, LIMIT
                        DB-->>Service: records cùng quan hệ role
                    else Trang không có dữ liệu
                        Service->>Service: records = []
                    end
                    loop Mỗi nhân viên trong records
                        alt actor có quyền quan_tri_vien
                            Service->>Service: _employee_response() dùng NhanVienRead
                        else actor có quyền quan_ly
                            Service->>Service: _employee_response() dùng NhanVienAssignmentRead
                        end
                    end
                    Service-->>API: NhanVienListResponse(data, meta)
                    API-->>Client: 200 OK, JSON data và meta
                end
            end
        end
    end
```

- `meta`: `request_id`, `page`, `page_size`, `total`, `total_pages = ceil(total / page_size)`.
- Trang vượt kết quả trả `200` với `data: []`; không trả `404`. Khi `total = 0`, `total_pages = 0`.
- `vai_tro_id` lớn hơn số nguyên signed 32-bit được chuyển thành điều kiện không khớp bản ghi.
- Quản trị viên nhận `NhanVienRead`; quản lý chỉ nhận `NhanVienAssignmentRead`:
  `id`, `ma_nhan_vien`, `ho_ten`, `vai_tro_id`, `ma_vai_tro`, `trang_thai`.
- Không trả `mat_khau` hoặc `tai_khoan_id`.

## GET /api/v1/nhan_vien/{id} — Lấy chi tiết nhân viên

`id` phải là số nguyên dương. Endpoint không nhận bất kỳ query parameter nào.
Quản trị viên và quản lý được xem nhân viên khác; nhân viên thông thường chỉ được xem chính mình.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI / users.router
    participant Auth as security.py
    participant Service as users.service
    participant DB as PostgreSQL

    Client->>API: GET /api/v1/nhan_vien/{id}, Bearer JWT
    API->>Auth: get_current_user_payload()
    Auth->>Auth: Kiểm tra token và sub
    alt Thiếu token, token lỗi hoặc sub không hợp lệ
        Auth-->>API: Lỗi xác thực
        API-->>Client: 401 Unauthorized
    else Token hợp lệ
        Auth->>DB: Lấy nhân viên theo sub và vai trò hiện tại
        DB-->>Auth: Nhân viên và vai trò
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
                API->>Service: get_employee(db, id, actor, request_id)
                alt id lớn hơn 2147483647
                    Service-->>API: NotFoundException, không truy vấn nhân viên đích
                    API-->>Client: 404 NOT_FOUND
                else id trong giới hạn
                    Service->>DB: SELECT nhân viên đích theo id
                    DB-->>Service: user cùng role hoặc không có bản ghi
                    alt Không tìm thấy nhân viên đích
                        Service-->>API: NotFoundException
                        API-->>Client: 404 NOT_FOUND
                    else Tìm thấy nhân viên đích
                        alt Không phải quản trị viên, quản lý hoặc chính mình
                            Service-->>API: ForbiddenException
                            API-->>Client: 403 FORBIDDEN
                        else Có quyền xem
                            alt Quản trị viên hoặc đang xem chính mình
                                Service->>Service: _employee_response(detail=True) dùng NhanVienRead
                            else Quản lý xem người khác
                                Service->>Service: _employee_response(detail=True) dùng NhanVienAssignmentRead
                            end
                            Service->>Service: SHA-256 của profile.model_dump_json() tạo strong ETag
                            Service-->>API: NhanVienDetailResponse và etag
                            API->>API: Gán response.headers.ETag
                            API-->>Client: 200 OK, JSON data và meta, header ETag
                        end
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
- `NhanVienRead` gồm các trường của `NhanVienAssignmentRead` và `ten_dang_nhap`,
  `ngay_sinh`, `so_dien_thoai`, `email`, `ngay_vao_lam`, `he_so_luong`.
  Không trả mật khẩu hoặc `tai_khoan_id`.
