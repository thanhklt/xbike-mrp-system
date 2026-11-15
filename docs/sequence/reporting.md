# Module reporting — UC-41 Xem báo cáo nhập-xuất-tồn

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
