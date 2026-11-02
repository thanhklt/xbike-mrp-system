# Sequence — mat_hang

Module sở hữu ORM `MatHang` ánh xạ bảng `"MatHang"`. Có sáu endpoint thực tế; đường dẫn danh mục cũng thuộc router này. Q/N được đọc, admin nhận 403, chỉ Q (`quan_ly`) được ghi.

GET trả cả bản ghi hoạt động và bị khóa; `is_active=false` không làm mất khả năng đọc. GET mặt hàng không truy vấn bảng MatHang; auth vẫn đọc DB để kiểm tra danh tính hiện hành. Giá là chuỗi decimal hai chữ số hoặc null; số dư và thời điểm tồn chỉ đọc. Snapshot gồm DTO bất biến, không giữ ORM/session.

## GET /api/v1/danh_muc_mat_hang/

Trả toàn bộ snapshot, không phân trang; meta.total và meta.request_id.

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
    R->>A: Yêu cầu Q/N, admin nhận 403
    alt Không có vai trò được phép
        A-->>C: 403
    end
    R->>R: Validate path/query (422 nếu không hợp lệ)
    R->>S: danh_muc()
    participant K as MatHangCache
    S->>K: Chụp một snapshot
    alt Chưa nạp hoặc đồng bộ lỗi
        K-->>C: 503 danh_muc_chua_san_sang
    else Snapshot sẵn sàng
        K-->>S: DTO bất biến, gồm mọi trạng thái
        S->>S: Lọc / tra ID / tính metadata
        alt ID không tồn tại hoặc filter/sort không hợp lệ
            S-->>C: 404 (chi tiết) hoặc 422 (list)
        else Thành công
            S-->>R: Response DTO
            R-->>C: 200 + data/meta.request_id
        end
    end
```

## GET /api/v1/mat_hang

Tìm mã/tên/SKU, lọc trạng thái chỉ khi được gửi; sort whitelist có ID làm tie-break; meta phân trang. Không lọc is_active mặc định.

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
    R->>A: Yêu cầu Q/N, admin nhận 403
    alt Không có vai trò được phép
        A-->>C: 403
    end
    R->>R: Validate path/query (422 nếu không hợp lệ)
    R->>S: list_mat_hang(filters, sort, page)
    participant K as MatHangCache
    S->>K: Chụp một snapshot
    alt Chưa nạp hoặc đồng bộ lỗi
        K-->>C: 503 danh_muc_chua_san_sang
    else Snapshot sẵn sàng
        K-->>S: DTO bất biến, gồm mọi trạng thái
        S->>S: Lọc / tra ID / tính metadata
        alt ID không tồn tại hoặc filter/sort không hợp lệ
            S-->>C: 404 (chi tiết) hoặc 422 (list)
        else Thành công
            S-->>R: Response DTO
            R-->>C: 200 + data/meta.request_id
        end
    end
```

## GET /api/v1/mat_hang/{id}

Trả envelope data/meta và ETag; ID không có trong snapshot trả 404, kể cả khi client biết ID từ nguồn khác.

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
    R->>A: Yêu cầu Q/N, admin nhận 403
    alt Không có vai trò được phép
        A-->>C: 403
    end
    R->>R: Validate path/query (422 nếu không hợp lệ)
    R->>S: get_mat_hang(id)
    participant K as MatHangCache
    S->>K: Chụp một snapshot
    alt Chưa nạp hoặc đồng bộ lỗi
        K-->>C: 503 danh_muc_chua_san_sang
    else Snapshot sẵn sàng
        K-->>S: DTO bất biến, gồm mọi trạng thái
        S->>S: Lọc / tra ID / tính metadata và ETag
        alt ID không tồn tại hoặc filter/sort không hợp lệ
            S-->>C: 404 (chi tiết) hoặc 422 (list)
        else Thành công
            S-->>R: Response DTO
            R-->>C: 200 + data/meta.request_id + ETag
        end
    end
```

## POST /api/v1/mat_hang

Tên bắt buộc không trắng, mã/SKU duy nhất; số dư server mặc định 0.

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
    R->>A: Yêu cầu quan_ly
    alt Admin / Nhân viên
        A-->>C: 403
    end
    R->>R: Validate input (422)
    R->>S: create_mat_hang(payload, actor)
    participant K as MatHangCache
    participant U as AuditService
    S->>K: Lấy khóa công bố, yêu cầu snapshot sẵn sàng
    alt Cache không sẵn sàng
        K-->>C: 503
    end
    S->>D: Mở transaction dùng chung theo request
    S->>D: Kiểm tra mã/SKU, INSERT MatHang
    alt Không có ID / thiếu If-Match / ETag cũ
        D-->>S: Dữ liệu hiện hành
        S->>D: ROLLBACK
        S-->>C: 404 / 428 / 412 (PATCH, DELETE)
    else Trùng mã/SKU hoặc vi phạm bất biến
        S->>D: ROLLBACK
        S-->>C: 409
    else Hợp lệ
        S->>D: Flush thay đổi
        opt Có thao tác cần ghi lịch sử
            S->>U: append(tao, snapshot trước/sau)
            U->>D: Thêm LichSuThaoTac cùng transaction
        end
        S->>K: Chuẩn bị snapshot mới, chưa công bố
        alt Audit / constraint / commit lỗi
            S->>D: ROLLBACK
            Note over S,K: Không công bố#59; commit không xác định thì cache unavailable
            S-->>C: 409 (constraint) hoặc 500
        else Commit thành công
            S->>D: COMMIT
            D-->>S: Thành công#59; trigger phát NOTIFY sau commit
            S->>K: Công bố snapshot trước khi trả response
            S-->>R: DTO / hoàn tất
            R-->>C: 201 + Location + ETag + data/meta
        end
    end
```

## PATCH /api/v1/mat_hang/{id}

PATCH bỏ qua field giữ nguyên; field NOT NULL không được gửi null; giữ các field bất biến sau tham chiếu.

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
    R->>A: Yêu cầu quan_ly
    alt Admin / Nhân viên
        A-->>C: 403
    end
    R->>R: Validate input (422)
    R->>S: patch_mat_hang(id, payload, If-Match, actor)
    participant K as MatHangCache
    participant U as AuditService
    S->>K: Lấy khóa công bố, yêu cầu snapshot sẵn sàng
    alt Cache không sẵn sàng
        K-->>C: 503
    end
    S->>D: Mở transaction dùng chung theo request
    S->>D: SELECT MatHang FOR UPDATE, đọc lại ETag
    alt Không có ID / thiếu If-Match / ETag cũ
        D-->>S: Dữ liệu hiện hành
        S->>D: ROLLBACK
        S-->>C: 404 / 428 / 412 (PATCH, DELETE)
    else Trùng mã/SKU hoặc vi phạm bất biến
        S->>D: ROLLBACK
        S-->>C: 409
    else Hợp lệ
        S->>D: Flush thay đổi
        opt Có thao tác cần ghi lịch sử
            S->>U: append(sua, snapshot trước/sau)
            U->>D: Thêm LichSuThaoTac cùng transaction
        end
        S->>K: Chuẩn bị snapshot mới, chưa công bố
        alt Audit / constraint / commit lỗi
            S->>D: ROLLBACK
            Note over S,K: Không công bố#59; commit không xác định thì cache unavailable
            S-->>C: 409 (constraint) hoặc 500
        else Commit thành công
            S->>D: COMMIT
            D-->>S: Thành công#59; trigger phát NOTIFY sau commit
            S->>K: Công bố snapshot trước khi trả response
            S-->>R: DTO / hoàn tất
            R-->>C: 200 + ETag + data/meta
        end
    end
```

## DELETE /api/v1/mat_hang/{id}

Chỉ UPDATE is_active=false; cho phép có BOM/chứng từ/tồn dương. Không DELETE SQL hoặc sửa số dư. Nếu đã false, ETag hiện hành trả 204 và không thêm audit.

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
    R->>A: Yêu cầu quan_ly
    alt Admin / Nhân viên
        A-->>C: 403
    end
    R->>R: Validate input (422)
    R->>S: delete_mat_hang(id, If-Match, actor)
    participant K as MatHangCache
    participant U as AuditService
    S->>K: Lấy khóa công bố, yêu cầu snapshot sẵn sàng
    alt Cache không sẵn sàng
        K-->>C: 503
    end
    S->>D: Mở transaction dùng chung theo request
    S->>D: SELECT MatHang FOR UPDATE, đọc lại ETag
    alt Không có ID / thiếu If-Match / ETag cũ
        D-->>S: Dữ liệu hiện hành
        S->>D: ROLLBACK
        S-->>C: 404 / 428 / 412 (PATCH, DELETE)
    else Trùng mã/SKU hoặc vi phạm bất biến
        S->>D: ROLLBACK
        S-->>C: 409
    else Hợp lệ
        S->>D: Flush thay đổi is_active=false
        opt Có thao tác cần ghi lịch sử
            S->>U: append(vo_hieu_hoa, snapshot trước/sau)
            U->>D: Thêm LichSuThaoTac cùng transaction
        end
        S->>K: Chuẩn bị snapshot mới, chưa công bố
        alt Audit / constraint / commit lỗi
            S->>D: ROLLBACK
            Note over S,K: Không công bố#59; commit không xác định thì cache unavailable
            S-->>C: 409 (constraint) hoặc 500
        else Commit thành công
            S->>D: COMMIT
            D-->>S: Thành công#59; trigger phát NOTIFY sau commit
            S->>K: Công bố snapshot trước khi trả response
            S-->>R: DTO / hoàn tất
            R-->>C: 204 không body
        end
    end
```

## Startup, đồng bộ và shutdown

Listener riêng đăng ký trước khi đọc dữ liệu; refresh dùng session ngắn riêng. Tín hiệu được gom bằng Event; tín hiệu đến trong lúc refresh sẽ kích hoạt lần đọc kế tiếp. Khóa refresh dùng cùng thứ tự với ghi cục bộ để dữ liệu đọc trước không ghi đè commit mới. GET giữ snapshot cũ nguyên vẹn trong khi một lần refresh bình thường đang chạy.

```mermaid
sequenceDiagram
participant L as FastAPI lifespan
    participant W as MatHangSynchronizer
    participant K as MatHangCache
    participant D as PostgreSQL
    L->>W: start()
    W->>D: Kết nối riêng, LISTEN mat_hang_changed
    W->>D: Session riêng SELECT toàn bộ MatHang
    W->>K: Công bố snapshot đầu tiên
    alt Startup lỗi
        W->>D: Đóng listener
        W-->>L: Startup thất bại, không phục vụ danh mục rỗng giả
    else Đã nạp
        W-->>L: Cho ứng dụng phục vụ
        loop NOTIFY hoặc mỗi 30 giây
            D-->>W: Tín hiệu sau commit / timer
            W->>K: Lấy khóa refresh
            W->>D: Đọc dữ liệu đã commit
            W->>K: Thay snapshot nguyên tử
        end
        alt Mất listener hoặc refresh lỗi
            W->>K: Đánh dấu unavailable (GET trả 503)
            W->>D: Reconnect có backoff, LISTEN lại và full reload
            W->>K: Khôi phục snapshot khi nạp thành công
        end
        L->>W: stop()
        W->>W: Hủy và đợi worker
        W->>D: Đóng listener
        W->>K: Đánh dấu unavailable
    end
```

NOTIFY không lưu bền cho client đã mất kết nối; full reload khi reconnect và đối soát định kỳ bù khoảng trống này. Tính GET thấy ngay sau API ghi được kiểm chứng cho một worker. Nhiều worker có snapshot riêng, đồng bộ bất đồng bộ; chưa cam kết tính thấy-ngay giữa các worker.

Các module dùng ton_kho/ORM cũ chưa chuyển đổi. Public MatHangAvailabilityService kiểm tra/khóa DB khi tạo tài liệu, không dùng cache làm quyết định ghi; xem sequence các module liên quan. Chưa có endpoint yêu cầu sản xuất theo contract và không mô tả nó như đã triển khai.
