# Sequence diagram — auth

Nguồn: `backend/app/modules/auth/{router,service,schemas,ports,repository}.py`,
`app/dependencies.py`, `app/core/{security,exceptions,request_context,sqlalchemy_transaction}.py`,
ORM `users` và repository `audit`. Đối chiếu phần 2, 3, 4, 14 của
[API contract v2](https://drive.google.com/file/d/16hj1yTLvhQ4peRENCLjbCKhNdGy_L2Xz/view).

Quyết định dev xác nhận ngày 18/10/2026: theo contract v2 và ORM hiện tại;
JWT mặc định 60 phút; đổi mật khẩu vô hiệu hóa mọi token đã cấp;
đọc bcrypt cũ, ghi mật khẩu mới bằng Argon2id.

- Ba API contract trả `{data, meta: {request_id}}`; lỗi auth trả
  `{error: {code, message, details}, meta: {request_id}}`.
- Tất cả response auth có `Cache-Control: no-store`, `Pragma: no-cache`;
  lỗi 401 có `WWW-Authenticate: Bearer`. Validation trả 422 với `field`, `reason`,
  không chứa giá trị password/token hoặc input gốc.
- A/Q/N đều được dùng API của chính mình; quyền và trạng thái đọc lại từ DB.
  Account không hoạt động trả 403 `tai_khoan_bi_vo_hieu_hoa`; không có vai trò
  hợp lệ trả 403 `khong_co_quyen`.
- `pwdv` trong JWT là HMAC-SHA256 của password hash bằng khóa ký và tiền tố riêng,
  không phải hash mật khẩu gốc. Mọi request có xác thực so sánh với phiên bản
  hiện tại trong DB. Token thiếu `pwdv` hoặc phiên bản cũ trả 401.
- Password giữ nguyên khoảng trắng/Unicode, không trim; tối đa 1024 ký tự.
  Tên đăng nhập trim, từ 1 đến 255 ký tự. Không tự nâng hash bcrypt khi đăng nhập,
  nên thao tác đọc/login không ghi DB. Đổi mật khẩu mới ghi Argon2id.
- Thứ tự validation/auth có thể phụ thuộc dependency của FastAPI nếu request
  đồng thời sai đầu vào và xác thực. Không cam kết ưu tiên lỗi trong trường hợp này.

## POST /api/v1/auth/dang_nhap

Công khai. JSON `LoginInput`: `ten_dang_nhap`, `mat_khau` bắt buộc;
không nhận field dư hoặc query. Chỉ đăng nhập bằng tên đăng nhập ở endpoint mới.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as auth.router / FastAPI
    participant S as AuthService
    participant P as SqlAlchemyAuthRepository
    participant K as core.security
    participant DB as PostgreSQL
    C->>R: POST /api/v1/auth/dang_nhap + LoginInput
    R->>R: Validate body, reject query, tạo request_id
    alt Thiếu/sai field hoặc có query
        R-->>C: 422 du_lieu_khong_hop_le
    else Đầu vào hợp lệ
        R->>S: login(username, password)
        S->>P: find_by_username(username)
        P->>DB: SELECT nhan_vien và vai_tro
        DB-->>P: Account hoặc không có
        P-->>S: AuthEmployee hoặc None
        alt Không có account
            S-->>R: InvalidCredentialsException
            R-->>C: 401 thong_tin_dang_nhap_khong_hop_le
        else Có account
            S->>K: verify_password trong worker thread
            K-->>S: Kết quả bcrypt hoặc Argon2id
            alt Mật khẩu sai hoặc hash không hợp lệ
                S-->>R: InvalidCredentialsException
                R-->>C: 401 cùng thông báo chung
            else Mật khẩu đúng
                S->>S: Kiểm tra hoat_dong và vai trò A/Q/N
                alt Account khóa hoặc vai trò không hợp lệ
                    S-->>R: InactiveAccountException / ForbiddenException
                    R-->>C: 403
                else Được phép đăng nhập
                    S->>K: password_version và create_access_token
                    K-->>S: JWT sub, exp, iat, roles, pwdv
                    S-->>R: TokenRead và NhanVienRead của chính mình
                    R-->>C: 200 data và meta, no-store
                end
            end
        end
    end
```

`TokenRead` gồm `access_token`, `token_type: bearer`, `expires_in: 3600`
với cấu hình mặc định, `nhan_vien: NhanVienRead`. Không trả hash, `tai_khoan_id`
hoặc `loai_nhan_vien`. Lỗi DB/nội bộ trả 500 `loi_noi_bo`, không lộ SQL.

## GET /api/v1/auth/me

Bearer JWT bắt buộc; không nhận query. A/Q/N đều nhận hồ sơ đầy đủ của chính mình,
không áp dụng projection giao việc của endpoint danh sách nhân viên.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as auth.router / FastAPI
    participant D as get_current_user_payload
    participant S as AuthService
    participant K as core.security
    participant P as SqlAlchemyAuthRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/auth/me + Bearer JWT
    R->>D: Lấy actor từ dependency
    alt Thiếu Bearer token
        D-->>R: UnauthorizedException
        R-->>C: 401 chua_xac_thuc
    else Có token
        D->>S: current_payload(token)
        S->>K: Verify chữ ký, exp, iat, sub
        alt JWT hết hạn/sai chữ ký hoặc sub ngoài giới hạn
            S-->>R: UnauthorizedException
            R-->>C: 401 chua_xac_thuc
        else JWT hợp lệ
            S->>P: get_by_id(sub)
            P->>DB: SELECT account và vai trò hiện tại
            DB-->>P: Account
            P-->>S: AuthEmployee
            alt Không còn account hoặc pwdv cũ/thiếu
                S-->>R: UnauthorizedException
                R-->>C: 401 chua_xac_thuc
            else Account khóa hoặc vai trò không hợp lệ
                S-->>R: InactiveAccountException / ForbiddenException
                R-->>C: 403
            else Account hợp lệ
                S-->>D: payload với roles từ DB
                D-->>R: payload
                R->>R: Reject query, tạo request_id
                alt Có query
                    R-->>C: 422 du_lieu_khong_hop_le
                else Không có query
                    R->>S: get_current_user(payload)
                    S->>P: get_by_id(sub)
                    P->>DB: SELECT account và vai trò
                    DB-->>P: Account
                    P-->>S: AuthEmployee
                    S->>S: Kiểm tra lại trạng thái, quyền, pwdv
                    alt Account thay đổi và không còn hợp lệ
                        S-->>R: Lỗi xác thực/quyền
                        R-->>C: 401 hoặc 403
                    else Vẫn hợp lệ
                        S-->>R: NhanVienRead
                        R->>R: SHA256 của JSON hồ sơ tạo ETag
                        R-->>C: 200 data, meta, ETag, no-store
                    end
                end
            end
        end
    end
```

ETag bao trong dấu ngoặc kép và không chứa `meta.request_id`; chưa xử lý
`If-None-Match`/304. Không có phân trang, không sửa account, tồn kho hoặc audit.
Account đã xóa trả 401 vì đây là resource của người xác thực, không phải GET ID tùy ý.
Lỗi DB/nội bộ trả 500 với envelope auth.

## POST /api/v1/auth/doi_mat_khau

Bearer JWT và `DoiMatKhauInput` bắt buộc: `mat_khau_hien_tai`, `mat_khau_moi`.
Mật khẩu mới từ 8 đến 1024 ký tự; không nhận ID nhân viên/role/query trong request.
Không yêu cầu `If-Match` theo contract; xác minh mật khẩu hiện tại dưới khóa account.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant R as auth.router / FastAPI
    participant D as get_current_user_payload
    participant S as AuthService
    participant P as SqlAlchemyAuthRepository
    participant K as core.security
    participant T as SqlAlchemyTransaction
    participant A as SqlAlchemyAuditRepository
    participant DB as PostgreSQL
    C->>R: POST /api/v1/auth/doi_mat_khau + body, JWT
    R->>R: Validate schema và reject query
    alt Body/query không hợp lệ
        R-->>C: 422, không echo password
    else Đầu vào hợp lệ
        R->>D: get_current_user_payload
        D->>S: current_payload(token)
        S->>K: Verify JWT và sub
        S->>P: get_by_id(sub)
        P->>DB: SELECT account và vai trò
        DB-->>P: Account
        P-->>S: AuthEmployee
        S->>S: Kiểm tra trạng thái, vai trò và pwdv
        alt Thiếu/sai/hết hạn JWT, account mất hoặc token cũ
            S-->>R: UnauthorizedException
            R-->>C: 401
        else Account khóa hoặc vai trò không hợp lệ
            S-->>R: Lỗi quyền
            R-->>C: 403
        else Xác thực hợp lệ
            S-->>D: actor
            D-->>R: actor
            R->>S: change_password(actor, current, new)
            S->>T: Vào transaction của session hiện tại
            S->>P: lock_by_id(sub)
            P->>DB: SELECT FOR UPDATE nhan_vien, tải vai trò
            DB-->>P: Account mới nhất sau khi lấy khóa
            P-->>S: AuthEmployee
            S->>S: Kiểm tra lại account, quyền và pwdv dưới khóa
            alt Account/token không còn hợp lệ
                S->>T: Ném lỗi
                T->>DB: ROLLBACK
                R-->>C: 401 hoặc 403
            else Account/token còn hợp lệ
                S->>K: verify_password(current) trong worker thread
                K-->>S: Đúng / sai
                alt Mật khẩu hiện tại sai
                    S->>T: InvalidCredentialsException
                    T->>DB: ROLLBACK
                    R-->>C: 401 thong_tin_dang_nhap_khong_hop_le
                else Mật khẩu hiện tại đúng
                    S->>K: get_password_hash(new), Argon2id trong worker thread
                    K-->>S: Hash mới
                    S->>P: set_password_hash(sub, hash)
                    P->>DB: UPDATE nhan_vien.mat_khau
                    S->>A: append audit sua, da_doi_mat_khau=true
                    A->>DB: INSERT audit khi flush/commit
                    S->>T: Kết thúc thành công
                    T->>DB: COMMIT password và audit cùng transaction
                    alt Ghi hoặc commit thất bại
                        T->>DB: ROLLBACK
                        R-->>C: 409 lỗi constraint hoặc 500 lỗi nội bộ
                    else Commit thành công
                        R-->>C: 200 data.da_doi=true và meta
                        Note over C,DB: Mọi token đã cấp không còn khớp pwdv, phải đăng nhập lại
                    end
                end
            end
        end
    end
```

Hai request đồng thời được tuần tự hóa bằng khóa dòng. Request thua cuộc đọc lại hash
mới và bị từ chối 401 trước khi ghi. Audit chỉ chứa ID, thao tác `sua` và cờ
`da_doi_mat_khau`; không lưu password/hash/JWT. Không sửa quyền hoặc dữ liệu kho.
Không trả token thay thế; client đăng nhập lại sau thành công.

## POST /api/v1/auth/login — endpoint tương thích

Giữ JSON `{email, password}` và response `TokenResponse` phẳng để tương thích.
`email` có thể là tên đăng nhập hoặc email duy nhất. Áp dụng trạng thái/quyền,
JWT có `pwdv`, no-store và error envelope auth như endpoint mới.

```mermaid
sequenceDiagram
    actor C as Client cũ
    participant R as auth.router / FastAPI
    participant S as AuthService
    participant P as SqlAlchemyAuthRepository
    participant K as core.security
    participant DB as PostgreSQL
    C->>R: POST /api/v1/auth/login + LoginRequest
    alt Body không hợp lệ
        R-->>C: 422
    else Body hợp lệ
        R->>S: authenticate(email, password)
        S->>P: find_by_username, nếu thiếu thì find_unique_by_email
        P->>DB: SELECT account và role
        DB-->>P: Account duy nhất hoặc None
        P-->>S: AuthEmployee hoặc None
        S->>K: verify_password nếu account tồn tại
        K-->>S: Kết quả
        alt Không có account hoặc mật khẩu sai
            R-->>C: 401 thông báo chung
        else Account khóa hoặc vai trò không hợp lệ
            R-->>C: 403
        else Hợp lệ
            S->>K: Tạo JWT với pwdv, exp, sub
            K-->>S: JWT
            S-->>R: TokenResponse
            R-->>C: 200 access_token, token_type, expires_in
        end
    end
```

Không ghi dữ liệu. Lỗi DB/nội bộ trả 500; endpoint cũ không áp dụng reject query.

## POST /api/v1/auth/token — OAuth2 cho Swagger

Giữ form `application/x-www-form-urlencoded`: `username`, `password` theo
`OAuth2PasswordRequestForm`. Response token phẳng để nút Authorize của Swagger dùng được.

```mermaid
sequenceDiagram
    actor C as Swagger / OAuth2 client
    participant R as auth.router / FastAPI
    participant S as AuthService
    participant P as SqlAlchemyAuthRepository
    participant K as core.security
    participant DB as PostgreSQL
    C->>R: POST /api/v1/auth/token + username, password
    alt Form thiếu trường bắt buộc
        R-->>C: 422
    else Form hợp lệ
        R->>S: authenticate(username, password)
        S->>P: Tra username, fallback email duy nhất
        P->>DB: SELECT account và role
        DB-->>P: Account hoặc None
        P-->>S: AuthEmployee hoặc None
        S->>K: verify_password nếu account tồn tại
        K-->>S: Kết quả
        alt Không có account hoặc mật khẩu sai
            R-->>C: 401 thông báo chung
        else Account khóa hoặc vai trò không hợp lệ
            R-->>C: 403
        else Hợp lệ
            S->>K: Tạo JWT với pwdv, exp, sub
            K-->>S: JWT
            S-->>R: TokenResponse
            R-->>C: 200 token phẳng, no-store
        end
    end
```

Không ghi dữ liệu. Lỗi DB/nội bộ trả 500; endpoint cũ không áp dụng reject query.
