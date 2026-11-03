# Luồng module audit

## GET /api/v1/audit

Endpoint đọc lịch sử dành cho A/Q. PageParams: page>=1, page_size 1..100, search, sort_by, sort_order asc/desc. Giữ response `{success,data,pagination,message}`; không có ETag. Không ghi audit khi đọc lịch sử. Sort theo cột có thật, fallback id; COUNT và truy vấn trang không bảo đảm chung snapshot khi có ghi đồng thời.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as AuditRouter
    participant D as Auth dependencies
    participant S as AuditService
    participant P as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/audit + JWT + query
    R->>D: get_current_user_payload và require_roles A/Q
    D->>DB: Đọc tài khoản, trạng thái và vai trò hiện tại
    alt JWT thiếu, hết hạn, không hợp lệ hoặc bị thu hồi
        D-->>C: 401
    else Account bị khóa hoặc vai trò không được phép
        D-->>C: 403
    else Được phép đọc
        R->>R: Validate PageParams
        alt Page, page_size hoặc sort_order không hợp lệ
            R-->>C: 422
        else Hợp lệ
            R->>S: list_entries(params)
            S->>P: list_entries(params)
            P->>DB: COUNT và SELECT lich_su_thao_tac phân trang
            P-->>S: RecordPage AuditLogResponse
            S-->>R: PaginatedResponse
            R-->>C: 200
        end
    end
    Note over R,DB: Lỗi nội bộ trả 500 an toàn
```

## API nội bộ ghi audit

`AuditService.append(CreationAudit)` là phương thức nội bộ, không phải endpoint HTTP. Phiếu nhập gọi service này thay vì inject repository trực tiếp. AuditService chuyển tiếp append xuống repository dùng chung session của phiếu nhập. Repository thêm bản ghi vào session; transaction phiếu nhập flush/commit, hoặc rollback toàn bộ khi lỗi. AuditService không tự flush, commit, rollback hay mở session mới. Các endpoint ghi phiếu nhập được mô tả tại [phieu_nhap.md](phieu_nhap.md).
