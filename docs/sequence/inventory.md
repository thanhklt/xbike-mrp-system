# Sequence inventory — đường nhận v4 và các endpoint legacy

Nguồn: `inventory/{router,service,repository,ports,models}.py`, `dependencies.py`,
core persistence và [phiếu nhập](phieu_nhap.md). Chỉ đường nhận hàng nội bộ được nâng v4
trong tác vụ Goods Receipt. Endpoint đọc vẫn dùng StockLevel/StockMovement, bảng legacy
`ton_kho`/`giao_dich_kho` lowercase, không tồn tại trong bootstrap v4. Không coi chúng
là API tồn v4 đã nghiệm thu; trên DB v4 chúng có thể trả 500. Đường xuất/điều chỉnh
legacy cũng giữ nguyên theo Q5.

## GET /api/v1/inventory/stock

Ảnh: [GET stock](assets/inventory/01-stock.png). QLK/NV; query PageParams chung:
page1/size20/max100, search, sort_by, sort_order. Không ETag, không ghi kho.

```mermaid
%%{init: {"sequence": {"width": 220, "wrap": true, "actorMargin": 40}}}%%
sequenceDiagram
    actor C as QLK / NV
    participant R as inventory.router<br/>dependencies
    participant A as AuthService<br/>NhanVienService
    participant N as SqlAlchemy<br/>NhanVienRepository
    participant S as InventoryService
    participant P as SqlAlchemy<br/>InventoryRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/inventory/stock + JWT + query
    R->>A: current_payload / get_auth_identity
    A->>N: get_credentials_by_id
    N->>DB: Current employee and role
    alt Invalid credentials / locked or forbidden role
        R-->>C: 401 / 403
    else Invalid pagination / sort direction
        R-->>C: 422
    else Valid request
        R->>S: list_stock(params)
        S->>P: list_stock(params)
        P->>DB: select_page COUNT and SELECT legacy StockLevel
        alt Legacy schema available
            P-->>S: RecordPage
            S-->>C: 200 success/data/pagination/message
        else Missing legacy table on v4
            R-->>C: Safe 500, no writes
        end
    end
```

## GET /api/v1/inventory/movements

Ảnh: [GET movements](assets/inventory/02-movements.png). Cùng quyền/query/envelope
với GET stock. Read model chưa chuyển sang GiaoDichKho v4 trong tác vụ này.

```mermaid
%%{init: {"sequence": {"width": 220, "wrap": true, "actorMargin": 40}}}%%
sequenceDiagram
    actor C as QLK / NV
    participant R as inventory.router<br/>dependencies
    participant A as AuthService<br/>NhanVienService
    participant N as SqlAlchemy<br/>NhanVienRepository
    participant S as InventoryService
    participant P as SqlAlchemy<br/>InventoryRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/inventory/movements + JWT + query
    R->>A: current_payload / get_auth_identity
    A->>N: get_credentials_by_id
    N->>DB: Current employee and role
    alt Invalid credentials / locked or forbidden role
        R-->>C: 401 / 403
    else Invalid pagination / sort direction
        R-->>C: 422
    else Valid request
        R->>S: list_movements(params)
        S->>P: list_movements(params)
        P->>DB: select_page COUNT and SELECT legacy StockMovement
        alt Legacy schema available
            P-->>S: RecordPage
            S-->>C: 200 success/data/pagination/message
        else Missing legacy table on v4
            R-->>C: Safe 500
        end
    end
```

## POST /api/v1/inventory/movements

Ảnh: [POST movements](assets/inventory/03-record-movement.png). Route legacy còn đăng
ký nhưng service luôn báo WorkflowNotImplemented (501). Không ghi ledger qua route này.

```mermaid
%%{init: {"sequence": {"width": 220, "wrap": true, "actorMargin": 40}}}%%
sequenceDiagram
    actor C as QLK
    participant R as inventory.router<br/>dependencies
    participant A as AuthService<br/>NhanVienService
    participant N as SqlAlchemy<br/>NhanVienRepository
    participant S as InventoryService
    participant DB as PostgreSQL
    C->>R: POST /api/v1/inventory/movements + JWT
    R->>A: current_payload / get_auth_identity
    A->>N: get_credentials_by_id
    N->>DB: Current employee and role
    alt Invalid credentials / not active QLK
        R-->>C: 401 / 403
    else Authorized
        R->>S: record_movement
        S-->>R: WorkflowNotImplemented
        R-->>C: 501, no writes
    end
```

## Port nhận hàng nội bộ — không phải endpoint

`PhieuNhapService → InventoryWriter → SqlAlchemyInventoryRepository → PostgreSQL`.
Service đã khóa phiếu/chi tiết trước khi gọi lock_receipt_stock. Repository khóa
MatHang tăng dần ID, đọc tồn/đang giữ/loại/active và SUM ledger, trả ReceiptStock frozen
detached. Service quyết định loại đúng/số dư khớp/giới hạn INTEGER. receive_receipt chỉ
ghi dữ liệu đã kiểm tra dưới cùng khóa: tăng tồn + timestamp, lấy tồn sau, INSERT
nhap_linh_kien với line FK duy nhất/actor/time/so_luong_ton_sau. Không đổi held/GiuHang,
giá danh mục hoặc nguồn sản xuất. Không commit riêng, không đọc/ghi cache trong TX.
Xem sequence hoàn tất để theo dõi AuditService và một commit/rollback toàn luồng.
