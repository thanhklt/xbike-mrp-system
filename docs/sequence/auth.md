# Sequence diagram — auth

Nguồn: `modules/auth/{router,service,repository,schemas}.py`, `dependencies.py`, `core/security.py`.
Các endpoint auth hiện giữ đường dẫn và envelope đang triển khai; chưa có `/auth/dang_nhap`
hay `/auth/doi_mat_khau`. Mật khẩu mới dùng Argon2id, bộ xác minh vẫn nhận bcrypt cũ.

## POST /api/v1/auth/login — Đăng nhập JSON

Body hiện tại `{email, password}`; `email` được dùng như tên đăng nhập hoặc email.

```mermaid
sequenceDiagram
    actor Client
    participant API as auth.router
    participant Service as AuthService
    participant Repo as SqlAlchemyAuthRepository
    participant DB as PostgreSQL
    Client->>API: POST /api/v1/auth/login, JSON
    alt Body không hợp lệ
        API-->>Client: 422 validation envelope hiện tại
    else Body hợp lệ
        API->>Service: authenticate(identifier, password)
        Service->>Repo: find_by_username(identifier)
        Repo->>DB: SELECT nhan_vien và role
        opt Không có tên đăng nhập
            Service->>Repo: find_unique_by_email(identifier)
            Repo->>DB: SELECT theo email, chỉ chấp nhận một kết quả
        end
        Service->>Service: Xác minh Argon2id/bcrypt và trang_thai=hoat_dong
        alt Không có account, mật khẩu sai hoặc account không hoạt động
            Service-->>API: UnauthorizedException, thông báo chung
            API-->>Client: 401
        else Thông tin hợp lệ
            Service->>Service: Tạo JWT với sub, vai trò và hạn dùng
            Service-->>API: TokenResponse
            API-->>Client: 200 access_token, token_type, expires_in
        end
    end
```

## POST /api/v1/auth/token — Đăng nhập OAuth2 form

```mermaid
sequenceDiagram
    actor Client
    participant API as auth.router
    participant Service as AuthService
    participant Repo as SqlAlchemyAuthRepository
    participant DB as PostgreSQL
    Client->>API: POST /api/v1/auth/token, username/password form
    alt Form không hợp lệ
        API-->>Client: 422
    else Form hợp lệ
        API->>Service: authenticate(username, password)
        Service->>Repo: find_by_username, fallback find_unique_by_email
        Repo->>DB: SELECT nhân viên và vai trò
        Service->>Service: Xác minh Argon2id/bcrypt và trạng thái hoạt động
        alt Không có account, mật khẩu sai hoặc account bị khóa
            API-->>Client: 401, thông báo chung
        else Account hoạt động
            Service->>Service: Ký JWT, lấy TTL cấu hình
            API-->>Client: 200 TokenResponse
        end
    end
```

## GET /api/v1/auth/me — Hồ sơ xác thực hiện tại

```mermaid
sequenceDiagram
    actor Client
    participant API as auth.router
    participant Auth as dependencies + AuthService
    participant Repo as SqlAlchemyAuthRepository
    participant DB as PostgreSQL
    Client->>API: GET /api/v1/auth/me, Bearer JWT
    API->>Auth: current_payload(token)
    Auth->>Auth: Kiểm tra JWT và sub
    alt Token thiếu/sai hoặc sub sai
        API-->>Client: 401
    else Token hợp lệ
        Auth->>Repo: get_by_id(sub)
        Repo->>DB: SELECT nhân viên và vai trò hiện tại
        alt Không có account hoặc trạng thái khác hoat_dong
            API-->>Client: 401 theo envelope auth hiện tại
        else Account hoạt động
            Auth-->>API: actor với quyền từ DB
            API->>Auth: get_current_user(sub)
            Auth->>Repo: get_by_id(sub)
            Repo->>DB: SELECT hồ sơ và role
            alt Account không còn tồn tại
                API-->>Client: 401
            else Có hồ sơ
                Auth-->>API: AuthUserResponse, không chứa password/hash
                API-->>Client: 200 id, email, full_name, ten_dang_nhap, roles
            end
        end
    end
```

Ba endpoint chỉ đọc dữ liệu, không có audit/transaction ghi. Quyền/trạng thái được đọc lại từ DB
trên mỗi request được bảo vệ; không tin quyền ghi sẵn trong JWT. Nhóm `/nhan_vien` và `/vai_tro`
dịch trạng thái account bị khóa thành 403 theo contract v2; auth giữ mã 401 hiện tại.
