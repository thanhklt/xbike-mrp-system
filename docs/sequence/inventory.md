# Luồng API inventory

Đối chiếu router/service/repository/schema và dependency ngày 03/11/2026. `StockLevel`/`ton_kho` chỉ giữ để đối soát lịch sử. Số dư hiện hành nằm trên `mat_hang`; API liệt kê cả mặt hàng có tồn 0. Không thay đổi quyền của các route cũ.

## GET /api/v1/inventory/stock

Giữ response `{success,data,pagination,message}` và field `id,mat_hang_id,so_luong,updated_at`; `id` nay bằng ID mặt hàng. `updated_at` lấy từ `ton_kho_updated_at` có múi giờ. Query page>=1, page_size 1..100, sort_order asc/desc; sort_by ánh xạ bốn field, không hợp lệ fallback id như trước. Search vẫn không lọc vì projection số dư không có cột text. COUNT/trang là hai truy vấn, không bảo đảm snapshot giữa hai lần đọc khi có ghi đồng thời.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as InventoryRouter
    participant D as Auth dependencies
    participant S as InventoryService
    participant P as InventoryRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/inventory/stock + JWT + query
    R->>D: get_current_user_payload
    D->>DB: Đọc tài khoản, trạng thái, vai trò và phiên bản mật khẩu
    alt JWT không hợp lệ hoặc bị thu hồi
        D-->>C: 401
    else Tài khoản bị khóa
        D-->>C: 403
    else Tài khoản hợp lệ A/Q/N
        R->>R: Validate PageParams
        alt Phân trang hoặc sort_order không hợp lệ
            R-->>C: 422
        else Hợp lệ
            R->>S: list_stock(params)
            S->>P: list_stock(params)
            P->>DB: COUNT mat_hang
            P->>DB: SELECT id, số dư, thời gian cập nhật, ORDER/OFFSET/LIMIT
            P-->>S: RecordPage StockLevelResponse
            S-->>R: PaginatedResponse
            R-->>C: 200
        end
    end
    Note over R,DB: Chỉ đọc, không audit, lỗi nội bộ trả 500 an toàn
```

## GET /api/v1/inventory/movements

Giữ nguyên đọc giao dịch đã lưu; không thay đổi tồn hoặc trạng thái. Cùng PageParams/envelope với stock. Sắp theo cột có thật, fallback id; không có cột text để search. `so_luong_bien_dong` là biến động ledger, không phải lượng hiệu lực sau điều chỉnh.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as InventoryRouter
    participant D as Auth dependencies
    participant S as InventoryService
    participant P as InventoryRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/inventory/movements + JWT + query
    R->>D: Kiểm tra JWT và tài khoản hiện tại
    D->>DB: SELECT tài khoản và vai trò
    alt Thiếu JWT, token sai hoặc bị thu hồi
        D-->>C: 401
    else Tài khoản bị khóa
        D-->>C: 403
    else A/Q/N được phép
        R->>R: Validate PageParams
        alt Sai phân trang hoặc sort_order
            R-->>C: 422
        else Hợp lệ
            R->>S: list_movements(params)
            S->>P: list_movements(params)
            P->>DB: COUNT và SELECT giao_dich_kho phân trang
            P-->>S: RecordPage
            S-->>C: 200 PaginatedResponse
        end
    end
    Note over R,DB: Không ghi dữ liệu, lỗi nội bộ trả 500
```

## POST /api/v1/inventory/movements

Route cũ tồn tại nhưng nghiệp vụ chưa triển khai; không phải đường tạo ledger thay thế hoàn tất phiếu nhập.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as InventoryRouter
    participant D as Auth dependencies
    participant S as InventoryService
    participant DB as PostgreSQL
    C->>R: POST /api/v1/inventory/movements + JWT
    R->>D: Xác thực và require_roles A/Q
    D->>DB: SELECT tài khoản, trạng thái và vai trò
    alt JWT sai hoặc thiếu
        D-->>C: 401
    else Tài khoản bị khóa hoặc không có quyền
        D-->>C: 403
    else Được phép
        R->>S: record_movement()
        S-->>R: WorkflowNotImplemented
        R-->>C: 501
    end
    Note over S,DB: Không ghi stock, ledger hay audit
```
