# Module reporting — UC-41 Xem báo cáo nhập-xuất-tồn; UC-42 Tra cứu lịch sử biến động kho

## GET /api/v1/bao_cao/nhap_xuat_ton

Nguồn: [UC-41](../../specs/use_cases/reporting/UC-41.md), [plan đã duyệt](../plans/UC-41.md),
`reporting/{router,schemas,service,ports,repository}.py`, `app/dependencies.py`,
`auth/service.py`, `nhan_vien/service.py` và `infra/postgres/init.sql`.

```mermaid
sequenceDiagram
    actor Client as Quản lý kho / người gọi
    participant Router as reporting.router / dependencies
    participant Auth as AuthService
    participant NV as NhanVienService / repository
    participant Service as BaoCaoService
    participant Repo as SqlAlchemyBaoCaoRepository
    participant DB as PostgreSQL

    Client->>Router: GET /api/v1/bao_cao/nhap_xuat_ton + Bearer token + query
    alt Thiếu token
        Router-->>Client: 401 Unauthorized
    else Có token
        Router->>Auth: current_payload(token)
        Auth->>Auth: Kiểm tra chữ ký, hạn và claims JWT
        Auth->>NV: Đọc credentials hiện tại
        NV->>DB: SELECT NhanVien, VaiTro
        DB-->>NV: Credentials và vai trò
        NV-->>Auth: Credentials
        Auth->>Auth: Kiểm tra trạng thái, phiên và phiên bản mật khẩu
        alt Token/phiên không hợp lệ
            Auth-->>Client: 401 Unauthorized (qua exception handler)
        else Tài khoản bị khóa
            Auth-->>Client: 403 tai_khoan_bi_vo_hieu_hoa (qua exception handler)
        else Đã xác thực
            Auth-->>Router: Payload với vai trò hiện tại
            Router->>Router: require_roles([quan_ly])
            alt Nhân viên / Quản trị viên
                Router-->>Client: 403 Forbidden (A3)
            else Quản lý kho
                Router->>Router: Depends(get_report_query), NhapXuatTonQuery
                alt Query sai / thiếu / thừa trường, kỳ không hợp lệ
                    Router-->>Client: 422 Validation error
                else Query hợp lệ
                    Router->>Service: nhap_xuat_ton(query)
                    Service->>Service: bien_ky, Asia/Ho_Chi_Minh, đổi biên sang UTC
                    Service->>Repo: nhap_xuat_ton(tu_utc, den_utc, mat_hang_id, loai_mat_hang)
                    Repo->>DB: Một SELECT MatHang + LATERAL GiaoDichKho
                    Note over Repo,DB: Mọi mặt hàng thỏa lọc AND, kể cả ngừng KD/chưa giao dịch<br/>Snapshot cuối trước từ/đến, ORDER BY posted_at DESC, id DESC<br/>Tổng dương và trị tuyệt đối âm trong [từ, đến)
                    DB-->>Repo: Các dòng, sắp theo loại và mã
                    Repo-->>Service: list NhapXuatTonRow
                    Service-->>Router: NhapXuatTonResponse, biên kỳ giờ Việt Nam
                    Router-->>Client: 200 success, data, message
                    Note over Client,Service: A1: mat_hang=[] khi không thỏa lọc, không trả 404<br/>A2: không biến động thì nhập/xuất=0, tồn cuối=tồn đầu<br/>Chưa giao dịch thì số dư và phát sinh đều 0
                end
            end
        end
    end
```

- Query: `ky` (`thang`/`quy`/`nam`), `nam` (2–9998); `thang` (1–12) chỉ bắt buộc
  khi kỳ tháng, `quy` (1–4) chỉ bắt buộc khi kỳ quý. Hai trường bị cấm ở kỳ khác.
  `mat_hang_id > 0`, `loai_mat_hang` (`linh_kien`/`thanh_pham`) tùy chọn; cấm trường lạ.
- Biên kỳ là nửa mở `[tu_thoi_diem, den_thoi_diem)`, ISO với `+07:00` cho các kỳ
  hiện đại. `ZoneInfo` dùng dữ liệu múi giờ lịch sử cho năm rất sớm trong khoảng hợp lệ.
  Cho phép kỳ tương lai. Không phân trang và không phân biệt trường trả về theo vai trò;
  chỉ `quan_ly` được đọc.
- Không đọc trạng thái chứng từ trong truy vấn báo cáo: trigger `kiem_tra_nguon_giao_dich`
  bảo đảm sổ chỉ có nguồn đã ghi nhận. Tồn đầu/cuối lấy `so_luong_ton_sau`, không lấy
  tổng lịch sử hay số tồn hiện tại để thay cho snapshot. Chứng từ và tồn kho được cập nhật
  ở các nghiệp vụ nguồn; endpoint này không cập nhật dữ liệu, không audit, không commit,
  không có transaction ghi, không yêu cầu `If-Match` và không trả `ETag`.

## GET /api/v1/bao_cao/bien_dong_kho

Nguồn: [UC-42](../../specs/use_cases/reporting/UC-42.md), [plan đã duyệt](../plans/UC-42.md),
`reporting/{router,schemas,service,ports,repository}.py`, `app/dependencies.py`,
`auth/service.py`, `nhan_vien/service.py`, `shared/{pagination,records}.py` và `infra/postgres/init.sql`.

```mermaid
sequenceDiagram
    actor Client as Quản lý kho / người gọi
    participant Router as reporting.router / dependencies
    participant Auth as AuthService
    participant NV as NhanVienService / repository
    participant Service as BaoCaoService
    participant Repo as SqlAlchemyBaoCaoRepository
    participant DB as PostgreSQL

    Client->>Router: GET /api/v1/bao_cao/bien_dong_kho + Bearer token + query
    alt Thiếu token
        Router-->>Client: 401 Unauthorized
    else Có token
        Router->>Auth: current_payload(token)
        Auth->>Auth: Kiểm tra chữ ký, hạn và claims JWT
        Auth->>NV: Đọc credentials hiện tại
        NV->>DB: SELECT NhanVien, VaiTro
        DB-->>NV: Credentials và vai trò
        NV-->>Auth: Credentials
        Auth->>Auth: Kiểm tra trạng thái, phiên và phiên bản mật khẩu
        alt Token/phiên không hợp lệ
            Auth-->>Client: 401 Unauthorized (qua exception handler)
        else Tài khoản bị khóa
            Auth-->>Client: 403 tai_khoan_bi_vo_hieu_hoa (qua exception handler)
        else Đã xác thực
            Auth-->>Router: Payload với vai trò hiện tại
            Router->>Router: require_roles([quan_ly])
            alt Nhân viên / Quản trị viên
                Router-->>Client: 403 Forbidden (A2)
            else Quản lý kho
                Router->>Router: Depends(get_movement_query), BienDongKhoQuery
                alt Query thừa trường, sai mã/id/ngày/phân trang hoặc khoảng đảo/cực trị
                    Router-->>Client: 422 Validation error
                else Query hợp lệ
                    Router->>Service: bien_dong_kho(query)
                    Service->>Service: bien_ngay(tu_ngay, den_ngay), Asia/Ho_Chi_Minh sang UTC
                    Service->>Repo: bien_dong_kho(tu_utc, den_utc, mat_hang_id, loai_giao_dich, nhan_vien_id, offset, limit)
                    Repo->>DB: SELECT GiaoDichKho + LEFT JOIN dữ liệu hiển thị, LIMIT/OFFSET
                    Note over Repo,DB: AND các bộ lọc trên sổ, không lọc trạng thái phiếu<br/>ORDER BY g.posted_at DESC, g.id DESC<br/>JOIN MatHang, NhanVien, chi tiết/đầu phiếu nhập/xuất, ChungTuHoanThanhSx
                    DB-->>Repo: Các dòng trang hiện tại
                    Repo->>DB: SELECT COUNT(*) FROM GiaoDichKho, cùng bộ lọc AND
                    DB-->>Repo: Tổng số dòng thỏa lọc
                    Repo-->>Service: RecordPage[BienDongKhoRow]
                    Service->>Service: Tạo DTO lồng, create_paginated_response
                    Service-->>Router: PaginatedResponse[BienDongKhoDong]
                    Router-->>Client: 200 success, data, pagination, message
                    Note over Client,Service: A1: không thỏa bộ lọc trả data=[], total_items=0<br/>Trang vượt tổng trả data=[] nhưng vẫn giữ total_items
                end
            end
        end
    end
```

- Query tùy chọn: `mat_hang_id > 0`, `nhan_vien_id > 0`, `loai_giao_dich` thuộc
  `nhap_linh_kien`, `xuat_linh_kien`, `nhap_san_pham_san_xuat`, `xuat_thanh_pham`;
  `tu_ngay`, `den_ngay` đúng `YYYY-MM-DD`. `page >= 1` mặc định 1, `page_size` 1–100
  mặc định 20. Cấm trường lạ, tìm kiếm và tùy chỉnh sắp xếp.
- Ngày bao gồm cả hai đầu theo `Asia/Ho_Chi_Minh`: từ đầu `tu_ngay` đến trước đầu
  ngày sau `den_ngay`, đổi UTC. Bỏ một biên thì không lọc biên đó; bỏ cả hai thì đọc
  toàn bộ lịch sử có phân trang. Chặn `tu_ngay = date.min`, `den_ngay = date.max`,
  khoảng đảo và ngày sai bằng 422. Mặt hàng/nhân viên không tồn tại trả 200 rỗng.
- Chỉ `GiaoDichKho` quyết định tập dòng và COUNT. Trigger `kiem_tra_nguon_giao_dich`
  đã chặn nguồn chưa hoàn tất/chưa duyệt/từ chối khi ghi sổ; JOIN chỉ lấy dữ liệu hiển thị.
  `chung_tu.id` là ID đầu phiếu nhập/xuất hoặc chứng từ hoàn thành, không phải ID chi tiết.
  `nhan_vien` là người ghi nhận trên sổ, không phải người lập chứng từ; `ho_ten` có thể null.
- Không có dữ liệu khác nhau theo vai trò: chỉ `quan_ly` được đọc. Trả số lượng có dấu,
  snapshot `so_luong_ton_sau`, thời điểm ghi sổ và thông tin mặt hàng, chứng từ, nhân viên.
  Không ghi dữ liệu, không audit/commit/transaction ghi, không yêu cầu `If-Match`, không trả `ETag`.
- UC-42 gỡ `GET /api/v1/inventory/movements` cùng ba method `list_movements` cũ;
  gọi GET đường dẫn cũ trả 405/404. Sau đó router inventory v3 (`GET /inventory/stock`,
  `POST /inventory/movements`) và ORM legacy cũng đã gỡ; module inventory chỉ còn writer. Trang `/kho/giao-dich` gọi endpoint reporting mới;
  không liên kết chứng từ sang các trang phiếu hiện tại.
