# Sequence diagram — luu_luong

Nguồn: `luu_luong/{router,service,repository,ports,schemas,models,recorder,middleware}.py`, `app/main.py`, `app/dependencies.py`, `core/request_context.py`, `auth/service.py`, `nhan_vien/service.py`.
Module luu_luong sở hữu ORM `LuuLuongTruyCap` ánh xạ bảng `"LuuLuongTruyCap"` (mỗi giờ một dòng `gio_bat_dau`, `so_request`). Không có endpoint ghi; số đếm do middleware HTTP ghi. Quyết định nghiệp vụ: [D-LL-01](../DECISION.md#d-ll-01-lưu-lượng-truy-cập-cho-tổng-quan-admin).

## Middleware ghi số đếm (không phải endpoint)

Middleware `dem_luu_luong` bọc mọi request. Chỉ đếm path `/api/v1` hoặc `/api/v1/...` với method khác `OPTIONS`; đếm cả response lỗi 4xx/5xx và chính endpoint lưu lượng. Không đếm `/`, `/health`, `/docs`, `/redoc`. Recorder chỉ được gán vào `app.state` trong lifespan của ứng dụng; khi không có recorder (test không chạy lifespan) middleware bỏ qua. Ghi số đếm dùng session và transaction riêng, tách khỏi transaction của request. Lỗi khi ghi không đổi response gốc; log warning tối đa 1 lần mỗi 60 giây.

```mermaid
sequenceDiagram
    actor C as Client
    participant M as luu_luong.middleware
    participant H as Router/handler được gọi
    participant RC as luu_luong.recorder
    participant DB as PostgreSQL
    C->>M: HTTP request
    alt OPTIONS hoặc path ngoài /api/v1
        M->>H: call_next(request)
        H-->>M: Response
        M-->>C: Response, không đếm
    else Request /api/v1 cần đếm
        M->>H: call_next(request)
        H-->>M: Response (2xx/4xx/5xx)
        opt app.state.luu_luong_recorder có giá trị
            M->>RC: record()
            RC->>DB: INSERT LuuLuongTruyCap (date_trunc('hour', now()), 1) ON CONFLICT gio_bat_dau DO UPDATE so_request + 1
            alt Ghi thành công
                RC->>DB: COMMIT (session riêng)
            else Lỗi DB (ví dụ bảng chưa tồn tại)
                RC->>RC: Nuốt lỗi, log warning tối đa 1 lần/60 giây
            end
        end
        M-->>C: Response gốc
    end
```

## GET /api/v1/luu_luong_truy_cap — Chuỗi lưu lượng cho biểu đồ Tổng quan

Bearer JWT bắt buộc; chỉ `quan_tri_vien` được đọc, `quan_ly` và `nhan_vien` nhận 403. Query duy nhất `khoang_thoi_gian` ∈ `hom_nay` (mặc định) / `7_ngay` / `30_ngay`; giá trị khác, tham số lặp lại hoặc tham số lạ trả 422. Ranh giới ngày và giờ theo Asia/Ho_Chi_Minh, thời điểm trả về theo UTC. Response `data` gồm `khoang_thoi_gian`, `buoc` (`gio`/`ngay`), `timezone`, `tu_thoi_diem`, `den_thoi_diem_exclusive`, `tong_request`, `diem[]` (`bat_dau`, `so_request`, `trung_binh_7_ngay`); `meta.request_id`. Không phân trang, không ETag. Đọc chỉ dùng session của request, không mở transaction ghi.

- `hom_nay`: 24 điểm theo giờ của hôm nay; giờ sau giờ hiện tại có `so_request = null`.
- `7_ngay`: 7 điểm theo ngày, điểm cuối là hôm nay (số tạm tính); `trung_binh_7_ngay = null`.
- `30_ngay`: 30 điểm theo ngày, điểm cuối là hôm nay; `trung_binh_7_ngay` là trung bình của ngày đó và 6 ngày trước, làm tròn 1 chữ số. Repository đọc thêm 6 ngày trước khoảng hiển thị; 6 ngày này không vào `tong_request`.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as luu_luong.router và dependencies
    participant A as auth.service
    participant N as nhan_vien.service
    participant NP as nhan_vien.repository
    participant S as luu_luong.service
    participant P as luu_luong.repository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/luu_luong_truy_cap?khoang_thoi_gian=..., Bearer JWT
    R->>A: current_payload(token)
    A->>A: Verify JWT và sub
    A->>N: get_auth_identity(id, pwdv)
    N->>NP: get_credentials_by_id(id)
    NP->>DB: SELECT NhanVien và VaiTro
    DB-->>N: Credentials qua repository
    N->>N: Kiểm tra account, role, pwdv
    alt Thiếu token, token/account mất hoặc pwdv cũ
        R-->>C: 401 UNAUTHORIZED
    else Account khóa hoặc role không hợp lệ
        R-->>C: 403 FORBIDDEN
    else Xác thực hợp lệ
        A-->>R: Payload với roles hiện tại
        R->>R: require_roles(["quan_tri_vien"])
        alt Role khác quan_tri_vien
            R-->>C: 403 FORBIDDEN
        else Admin
            R->>R: Validate khoang_thoi_gian, reject tham số lặp và tham số lạ
            alt Query không hợp lệ
                R-->>C: 422 VALIDATION_ERROR
            else Query hợp lệ
                R->>S: get_series(khoang, request_id)
                S->>S: Lấy hôm nay theo Asia/Ho_Chi_Minh, tính [tu, den) theo UTC
                alt khoang = hom_nay (buoc = gio)
                    S->>P: sum_by_hour(tu, den)
                    P->>DB: SELECT gio_bat_dau, so_request WHERE tu <= gio_bat_dau < den
                    DB-->>P: Các giờ có request
                    P-->>S: dict giờ → số request
                    S->>S: Bù đủ 24 giờ, giờ chưa tới = null
                else khoang = 7_ngay hoặc 30_ngay (buoc = ngay)
                    opt khoang = 30_ngay
                        S->>S: Lùi cận dưới thêm 6 ngày cho trung bình trượt
                    end
                    S->>P: sum_by_day(cận dưới, den, Asia/Ho_Chi_Minh)
                    P->>DB: SELECT date(timezone(tz, gio_bat_dau)), sum(so_request) GROUP BY ngày
                    DB-->>P: Tổng theo ngày địa phương
                    P-->>S: dict ngày → số request
                    S->>S: Bù đủ ngày bằng 0
                    opt khoang = 30_ngay
                        S->>S: moving_average_7, bỏ 6 ngày đọc thêm khỏi chuỗi hiển thị
                    end
                end
                S->>S: tong_request = tổng so_request khác null
                S-->>R: LuuLuongResponse
                R-->>C: 200 data, meta.request_id
            end
        end
    end
```
