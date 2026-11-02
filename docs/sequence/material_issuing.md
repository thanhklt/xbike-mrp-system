# Sequence — material_issuing

Đối chiếu router/service/repository/schema hiện có. Các tên bảng/ORM nghiệp vụ cũ trong module này chưa được chuyển sang SQL đã chốt; tác vụ hiện tại chỉ thêm guard mặt hàng và sửa FK trực tiếp cần thiết. Các sơ đồ mô tả luồng code khi persistence tương thích; không phải xác nhận E2E với init.sql hiện tại. Endpoint chưa triển khai không được bổ sung vào đây.

GET giữ response và pagination hiện có, vẫn đọc DB của module; yêu cầu GET từ cache chỉ áp dụng danh mục/mặt hàng. GET có auth, không thêm giới hạn vai trò mới. POST giữ nhóm vai trò cũ: quan_tri_vien / quan_ly / nhan_vien. Auth dùng public nhân viên service và kiểm tra trạng thái/credential hiện hành.

## GET /api/v1/material-issuing

```mermaid
sequenceDiagram
actor C as Client
    participant R as Router
    participant A as Auth/role dependencies
    participant S as Service
    participant D as Repository/PostgreSQL
    C->>R: Request + Bearer JWT
    R->>A: Kiểm tra JWT, tài khoản và vai trò hiện hành
    A->>D: Đọc danh tính hiện hành qua public nhân viên service
    alt Chưa xác thực / token lỗi
        A-->>C: 401
    else Tài khoản bị khóa
        A-->>C: 403
    end
    R->>R: Validate path/query (422)
    R->>S: list_entries(PageParams)
    S->>D: Truy vấn resource và tổng số/phân trang
    alt Không tìm thấy chi tiết
        S-->>C: 404
    else Thành công
        D-->>S: Dữ liệu resource
        S-->>R: Response DTO
        R-->>C: 200 + pagination
    end
    Note over S,D: SQL/ORM chưa tương thích có thể lỗi 500#59; đang hoãn đồng bộ
```

## GET /api/v1/material-issuing/{issue_id}

```mermaid
sequenceDiagram
actor C as Client
    participant R as Router
    participant A as Auth/role dependencies
    participant S as Service
    participant D as Repository/PostgreSQL
    C->>R: Request + Bearer JWT
    R->>A: Kiểm tra JWT, tài khoản và vai trò hiện hành
    A->>D: Đọc danh tính hiện hành qua public nhân viên service
    alt Chưa xác thực / token lỗi
        A-->>C: 401
    else Tài khoản bị khóa
        A-->>C: 403
    end
    R->>R: Validate path/query (422)
    R->>S: get_entry(id)
    S->>D: Truy vấn resource
    alt Không tìm thấy chi tiết
        S-->>C: 404
    else Thành công
        D-->>S: Dữ liệu resource
        S-->>R: Response DTO
        R-->>C: 200
    end
    Note over S,D: SQL/ORM chưa tương thích có thể lỗi 500#59; đang hoãn đồng bộ
```

## POST /api/v1/material-issuing

Guard kiểm tra cả đầu ra và các dòng đối với BOM/work order; các dòng đối với phiếu nhập/xuất. Caller giữ transaction; guard dùng cùng session và không commit. ID không có trả 404; mặt hàng bị khóa trả 409 `mat_hang_ngung_hoat_dong`. Các dòng bị khóa vẫn có thể được đọc trong chứng từ cũ. Kiểm tra loai_phieu đúng luồng trước khi tạo; sai loại trả 422.

```mermaid
sequenceDiagram
actor C as Client
    participant R as Router
    participant A as Auth/role dependencies
    participant S as Service
    participant D as Repository/PostgreSQL
    C->>R: Request + Bearer JWT
    R->>A: Kiểm tra JWT, tài khoản và vai trò hiện hành
    A->>D: Đọc danh tính hiện hành qua public nhân viên service
    alt Chưa xác thực / token lỗi
        A-->>C: 401
    else Tài khoản bị khóa
        A-->>C: 403
    end
    R->>A: Kiểm tra vai trò tạo theo router
    alt Không được phép
        A-->>C: 403
    end
    R->>R: Validate payload (422)
    R->>S: create_entry(payload, actor)
    participant G as MatHangAvailabilityService
    participant U as AuditService
    S->>D: Transaction của caller
    S->>G: require_active_items(tập ID)
    G->>D: SELECT MatHang ORDER BY id FOR SHARE, đọc lại trạng thái
    alt Thiếu ID hoặc is_active=false
        G-->>S: 404 hoặc 409
        S->>D: ROLLBACK
        S-->>C: Lỗi, chưa tạo tài liệu
    else Hợp lệ
        S->>D: Repository thêm tài liệu và chi tiết
        S->>U: append(tao, snapshot)
        U->>D: Thêm lịch sử cùng transaction
        alt Persistence / audit lỗi
            S->>D: ROLLBACK
            S-->>C: 409 (constraint) hoặc 500
        else Thành công
            S->>D: COMMIT, giải phóng khóa mặt hàng
            S-->>R: DTO tài liệu
            R-->>C: 201
        end
    end
    Note over G,D: Soft delete đợi khóa, không chen giữa kiểm tra và ghi
```

Không cộng/trừ tồn kho khi tạo các tài liệu này; không tự hủy/chỉnh sửa tài liệu cũ khi mặt hàng bị khóa. Chưa bổ sung chính sách mới cho các bước workflow chưa triển khai.
