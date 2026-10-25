# Sequence diagram — inventory

Nguồn triển khai: `backend/app/modules/inventory/{router,service,schemas,ports,repository,models}.py`,
`backend/app/dependencies.py`, `backend/app/core/errors.py` và `backend/app/main.py`.
Đối chiếu quy tắc nghiệp vụ với `infra/postgres/init.sql` và `docs/api-conventions.md`.

Các sơ đồ mô tả luồng qua các tầng Clean Architecture:
- Presentation / Routing: `ton_kho_router` và `giao_dich_kho_router`
- Authentication / Authorization: `get_current_user_payload`
- Use Cases: `InventoryService`
- Persistence Abstraction: `InventoryRepository` / `SqlAlchemyInventoryRepository`
- Database: PostgreSQL tables `ton_kho`, `giao_dich_kho`, `phieu_dieu_chinh_kho`, `chi_tiet_phieu_dieu_chinh_kho`

---

## 1. API-029: GET /api/v1/ton_kho — Lấy danh sách tồn kho phân trang

Query params: `page` (mặc định 1, >= 1), `page_size` (mặc định 20, 1..100), `mat_hang_id` (tùy chọn, > 0), `sort_by` (mặc định id), `sort_order` (asc|desc, mặc định desc).

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI / ton_kho_router
    participant Auth as dependencies.get_current_user_payload
    participant Service as InventoryService
    participant Repo as SqlAlchemyInventoryRepository
    participant DB as PostgreSQL (ton_kho)

    Client->>API: GET /api/v1/ton_kho?page=1&page_size=20&mat_hang_id=1, Bearer JWT
    API->>Auth: Xác thực Bearer Token
    alt Token thiếu hoặc không hợp lệ
        Auth-->>API: UnauthorizedException
        API-->>Client: 401 UNAUTHORIZED
    else Token hợp lệ
        Auth-->>API: actor payload
        API->>Service: list_stock(params, mat_hang_id)
        Service->>Repo: list_stock(params, mat_hang_id)
        Repo->>DB: COUNT(*) FROM ton_kho WHERE (mat_hang_id = :id)
        DB-->>Repo: total
        Repo->>DB: SELECT * FROM ton_kho WHERE (mat_hang_id = :id) ORDER BY ... LIMIT :limit OFFSET :offset
        DB-->>Repo: records
        Repo-->>Service: RecordPage[StockLevelResponse]
        Service->>Service: create_paginated_response(items, total, page, page_size)
        Service-->>API: PaginatedResponse[StockLevelResponse]
        API-->>Client: 200 OK (Envelope PaginatedResponse)
    end
```

---

## 2. API-030: GET /api/v1/ton_kho/{mat_hang_id} — Chi tiết tồn kho theo mặt hàng kèm ETag

Path param: `mat_hang_id` (bắt buộc, số nguyên > 0).

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI / ton_kho_router
    participant Auth as dependencies.get_current_user_payload
    participant Service as InventoryService
    participant Repo as SqlAlchemyInventoryRepository
    participant DB as PostgreSQL (ton_kho)

    Client->>API: GET /api/v1/ton_kho/1, Bearer JWT
    API->>Auth: Xác thực Bearer Token
    alt Token thiếu hoặc không hợp lệ
        Auth-->>API: UnauthorizedException
        API-->>Client: 401 UNAUTHORIZED
    else Token hợp lệ
        Auth-->>API: actor payload
        API->>Service: get_stock_by_mat_hang(mat_hang_id=1)
        Service->>Repo: get_stock_by_mat_hang(1)
        Repo->>DB: SELECT * FROM ton_kho WHERE mat_hang_id = 1
        alt Không tìm thấy bản ghi tồn kho
            DB-->>Repo: None
            Repo-->>Service: None
            Service-->>API: NotFoundException (Resource not found)
            API-->>Client: 404 NOT_FOUND
        else Tìm thấy bản ghi
            DB-->>Repo: StockLevel row
            Repo-->>Service: StockLevelResponse
            Service->>Service: etag = sha256(record.json)
            Service-->>API: record, etag
            API->>API: Set header ETag
            API-->>Client: 200 OK + Header ETag + StockLevelResponse
        end
    end
```

---

## 3. API-031: GET /api/v1/giao_dich_kho — Lấy sổ giao dịch kho phân biệt lượng hiệu lực và biến động ledger

Query params: `page` (mặc định 1), `page_size` (mặc định 20), `mat_hang_id` (tùy chọn, > 0), `loai_giao_dich` (tùy chọn), `sort_by`, `sort_order`.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI / giao_dich_kho_router
    participant Auth as dependencies.get_current_user_payload
    participant Service as InventoryService
    participant Repo as SqlAlchemyInventoryRepository
    participant DB as PostgreSQL (giao_dich_kho & phieu_dieu_chinh)

    Client->>API: GET /api/v1/giao_dich_kho?mat_hang_id=1, Bearer JWT
    API->>Auth: Xác thực Bearer Token
    alt Token thiếu hoặc không hợp lệ
        Auth-->>API: UnauthorizedException
        API-->>Client: 401 UNAUTHORIZED
    else Token hợp lệ
        Auth-->>API: actor payload
        API->>Service: list_movements(params, mat_hang_id, loai_giao_dich)
        Service->>Repo: list_movements(params, mat_hang_id, loai_giao_dich)
        Repo->>DB: COUNT(*) FROM giao_dich_kho WHERE filters
        DB-->>Repo: total
        Note over Repo,DB: Correlated subquery: so_luong_hieu_luc = so_luong_bien_dong + sum(điều chỉnh đã duyệt)
        Repo->>DB: SELECT g.*, (g.so_luong_bien_dong + COALESCE((SELECT sum(cd.so_luong_bien_dong) ... WHERE cd.giao_dich_goc_id = g.id AND pd.trang_thai = 'da_duyet'), 0)) AS so_luong_hieu_luc FROM giao_dich_kho g ...
        DB-->>Repo: records with effective quantity
        Repo-->>Service: RecordPage[StockMovementResponse]
        Service->>Service: create_paginated_response(items, total, page, page_size)
        Service-->>API: PaginatedResponse[StockMovementResponse]
        API-->>Client: 200 OK (PaginatedResponse chứa cả so_luong_bien_dong và so_luong_hieu_luc)
    end
```

---

## 4. API-032: GET /api/v1/giao_dich_kho/{id} — Chi tiết giao dịch kho kèm ETag

Path param: `id` (bắt buộc, số nguyên > 0).

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI / giao_dich_kho_router
    participant Auth as dependencies.get_current_user_payload
    participant Service as InventoryService
    participant Repo as SqlAlchemyInventoryRepository
    participant DB as PostgreSQL (giao_dich_kho & phieu_dieu_chinh)

    Client->>API: GET /api/v1/giao_dich_kho/10, Bearer JWT
    API->>Auth: Xác thực Bearer Token
    alt Token thiếu hoặc không hợp lệ
        Auth-->>API: UnauthorizedException
        API-->>Client: 401 UNAUTHORIZED
    else Token hợp lệ
        Auth-->>API: actor payload
        API->>Service: get_movement_by_id(id=10)
        Service->>Repo: get_movement_by_id(10)
        Repo->>DB: SELECT g.*, (g.so_luong_bien_dong + COALESCE(subquery, 0)) AS so_luong_hieu_luc FROM giao_dich_kho g WHERE g.id = 10
        alt Giao dịch không tồn tại
            DB-->>Repo: None
            Repo-->>Service: None
            Service-->>API: NotFoundException (Resource not found)
            API-->>Client: 404 NOT_FOUND
        else Tìm thấy giao dịch
            DB-->>Repo: row
            Repo-->>Service: StockMovementResponse
            Service->>Service: etag = sha256(record.json)
            Service-->>API: record, etag
            API->>API: Set header ETag
            API-->>Client: 200 OK + Header ETag + StockMovementResponse
        end
    end
```
