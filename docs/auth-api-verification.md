# Ba API xác thực — triển khai và kiểm chứng 18/10/2026

## Phạm vi và nguồn đã chốt

- `POST /api/v1/auth/dang_nhap`: JSON `LoginInput` → `TokenRead` trong envelope v2.
- `GET /api/v1/auth/me`: hồ sơ đầy đủ của chính mình, envelope v2 và strong ETag.
- `POST /api/v1/auth/doi_mat_khau`: xác minh mật khẩu hiện tại, cập nhật hash và
  audit cùng transaction, trả `data.da_doi=true`.

Theo [API contract v2](https://drive.google.com/file/d/16hj1yTLvhQ4peRENCLjbCKhNdGy_L2Xz/view),
phần 2, 3, 4 và 14. Dev xác nhận dùng contract v2/ORM hiện tại thay cho khác biệt
trong data model v3 đính kèm; JWT mặc định 60 phút; token cũ mất hiệu lực sau đổi
mật khẩu; đọc bcrypt cũ, ghi Argon2id mới.

Không triển khai CRUD tài khoản, khóa/mở khóa account, quản lý vai trò, refresh token
hoặc giao diện trong tác vụ này. Các endpoint auth không nhận ID người khác để đổi mật khẩu.

## Request và response mẫu

Các giá trị bên dưới là placeholder, không phải thông tin đăng nhập thật.

```http
POST /api/v1/auth/dang_nhap
Content-Type: application/json

{"ten_dang_nhap":"<ten-dang-nhap>","mat_khau":"<mat-khau-hien-tai>"}
```

Response 200 gồm:

```json
{
  "data": {
    "access_token": "<JWT>",
    "token_type": "bearer",
    "expires_in": 3600,
    "nhan_vien": {
      "id": 1,
      "ma_nhan_vien": "NV-000001",
      "ho_ten": "Nhân viên mẫu",
      "vai_tro_id": 3,
      "ma_vai_tro": "nhan_vien",
      "trang_thai": "hoat_dong",
      "ten_dang_nhap": "<ten-dang-nhap>",
      "ngay_sinh": null,
      "so_dien_thoai": null,
      "email": null,
      "ngay_vao_lam": null,
      "he_so_luong": null
    }
  },
  "meta": {"request_id": "<request-id>"}
}
```

```http
GET /api/v1/auth/me
Authorization: Bearer <JWT>
```

Response 200 có `data` chính là hồ sơ `nhan_vien` ở trên và `meta.request_id` mới;
header `ETag` được tính từ hồ sơ, không tính metadata. Không nhận query.

```http
POST /api/v1/auth/doi_mat_khau
Authorization: Bearer <JWT>
Content-Type: application/json

{"mat_khau_hien_tai":"<mat-khau-hien-tai>","mat_khau_moi":"<mat-khau-moi-it-nhat-8-ky-tu>"}
```

```json
{"data":{"da_doi":true},"meta":{"request_id":"<request-id>"}}
```

Đổi mật khẩu không yêu cầu `If-Match`. Client đăng nhập lại để nhận token mới.
Mật khẩu giữ nguyên Unicode/khoảng trắng, giới hạn 1024 ký tự; mật khẩu mới tối thiểu
8 ký tự. Login mới chỉ dùng tên đăng nhập. Tên đăng nhập được trim, giới hạn 255 ký tự.
Account khóa trả 403; sai credentials hoặc token cũ/hết hạn trả 401; body/query sai trả 422.
Tất cả response auth có `Cache-Control: no-store`, `Pragma: no-cache`.

## Tương thích

- `/auth/login` giữ body `email/password`, chấp nhận username hoặc email duy nhất;
  `/auth/token` giữ form OAuth2. Hai endpoint giữ response token phẳng cho client cũ/Swagger.
- `/auth/me` đổi response sang `{data, meta}` và tên field tiếng Việt theo contract v2.
  Client dùng response cũ `full_name/roles` cần cập nhật. Frontend hiện tại chưa tích hợp.
- Error envelope của module auth theo v2, gồm `error` và `meta.request_id`;
  validation chỉ trả tên field và lý do, không trả input/password/hash/token.
- JWT cũ chưa có `pwdv` không còn được chấp nhận: người dùng phải đăng nhập lại khi
  triển khai. Không có refresh token hoặc token mới tự động trong response đổi mật khẩu.
- Cơ chế xác thực dùng chung bảo vệ các module khác: trạng thái/vai trò lấy từ DB,
  token cũ sau đổi mật khẩu bị chặn cả ở API ngoài auth. Account không hoạt động trả 403.
- SQLAlchemy ẩn parameters để hash mật khẩu không xuất hiện trong log truy vấn.

## Migration

`init.sql` dành cho database mới có `trang_thai NOT NULL DEFAULT 'hoat_dong'` và CHECK
`hoat_dong/bi_khoa`. Vẫn giữ cột legacy `loai_nhan_vien` trong SQL để bảo toàn dữ liệu;
ORM/API chỉ dùng vai trò qua `vai_tro_id`, không trả cột legacy này.

Chuỗi Alembic:

1. `20261018_status_default`: thêm cột nullable nếu bản SQL cũ chưa có, sau đó đặt default
   cho account tạo mới. Bản migration đã tồn tại được bổ sung nhánh tương thích này;
   database đã áp dụng revision không chạy lại nó.
2. `20261018_auth_status`: kiểm tra dữ liệu rồi thêm NOT NULL/CHECK và default.
   Giữ nguyên account `hoat_dong`/`bi_khoa`. Nếu có NULL hoặc giá trị lạ, migration
   dừng với lỗi rõ ràng, không tự kích hoạt, khóa hay chuyển loại account.

Trước khi áp dụng lên database hiện có, kiểm tra schema và trạng thái account bằng truy vấn
chỉ đọc. Nếu thiếu trạng thái, cần mapping được dev xác nhận cho từng account trước khi
chạy head. Có thể áp dụng tới revision `20261018_status_default` trước để có cột nullable,
sau đó thực hiện mapping đã được duyệt trong transaction riêng, rồi mới nâng lên head.
Không coi chạy `init.sql` hoặc seed là cách cập nhật database hiện có.

Trong lần kiểm chứng này chỉ chạy migration trên database test riêng; chưa áp dụng database
ứng dụng và chưa thay đổi trạng thái hay mật khẩu tài khoản ứng dụng.

Rollback: downgrade về `20261018_status_default` chỉ gỡ NOT NULL/CHECK mới, không xóa
cột hoặc dữ liệu. Không rollback verifier về bcrypt-only sau khi đã có password Argon2id;
cần giữ hỗ trợ đọc Argon2id hoặc triển khai bản sửa tiếp theo. Không thể khôi phục plaintext
mật khẩu từ hash. Đây là thay đổi xác thực/schema, mức rủi ro HIGH theo checklist clean-code.

## Kiểm chứng

Môi trường: Windows, Python 3.13, dependency từ `backend/poetry.lock`, PostgreSQL 16
trong container test riêng, dữ liệu lưu tạm, không mount volume ứng dụng.

Lệnh chạy từ `backend/` sau khi cài dependency dev:

```powershell
$env:TEST_DATABASE_URL = 'postgresql+asyncpg://<user>:<password>@127.0.0.1:<port>/<database>_test'
$env:ENVIRONMENT = 'test'
poetry run pytest -q
poetry run ruff check .
poetry run ruff format --check .
poetry check --lock
```

Test auth yêu cầu database riêng có tên kết thúc `_test`. Mỗi test thông thường tạo schema
ngẫu nhiên và dùng outer transaction/savepoint để rollback. Test concurrent cần commit thật
nên dùng schema ngẫu nhiên riêng trong database test; schema này tồn tại đến khi hủy môi trường
test. Test không dùng hoặc sửa các bảng `public` đã seed.

Đã kiểm tra:

- 36 test toàn bộ backend: 29 test auth/API, 4 test migration, 3 test khởi động/health/ping.
- Đăng nhập và hồ sơ cho đủ A/Q/N; full profile của chính mình, không lộ dữ liệu bí mật.
- Body thiếu/sai/thừa, giới hạn mật khẩu, Unicode và khoảng trắng; query không được hỗ trợ.
- JWT thiếu, lỗi, hết hạn, chưa có phiên bản mật khẩu; account bị xóa/khóa; quyền được
  đọc lại từ DB thay vì tin role cũ trong JWT.
- Đổi password ghi Argon2id, chặn mật khẩu/token cũ, không đổi tài khoản khác.
- Sai mật khẩu hiện tại và lỗi ghi audit đều rollback; lỗi nội bộ không lộ chi tiết.
- Hai request đồng thời cùng qua bước xác thực: đúng một request commit, một request 401,
  đúng một audit, chỉ mật khẩu của request thắng đăng nhập được.
- Migration trên schema cũ chưa có cột; upgrade/downgrade; giữ trạng thái hiện có;
  từ chối dữ liệu trạng thái chưa được xác định.
- `init.sql`, `seed.sql`, `alembic upgrade head` chạy thành công trên database bootstrap test.
- HTTP thật qua Uvicorn với account seed: login 200, me 200, change 200, token cũ 401,
  password cũ 401, login mới 200; audit thêm đúng 1; toàn bộ tồn kho và sổ giao dịch không đổi.
- Ruff lint/format và kiểm tra Poetry lock.
- Mermaid CLI render thành công 5 sơ đồ auth và 2 sơ đồ users.
- Map cấu trúc module auth và rà soát import thủ công. Công cụ kiểm tra boundary tự động
  không chạy được vì project chưa có block khai báo `clean-architecture`; không coi đây là
  bằng chứng đã vượt kiểm tra boundary tự động.

Không chạy GitHub Actions trên remote, không build frontend/Docker image, không commit/push.
Dockerfile hiện tham chiếu `backend/poetry.toml` chưa có trong checkout; đây là giới hạn sẵn có
của việc build image, không thuộc phần API đã kiểm thử.

## File thay đổi

| Nhóm | File và mục đích |
|---|---|
| Auth | `app/modules/auth/router.py`, `schemas.py`, `service.py`, `ports.py`, `repository.py`: ba API, hợp đồng dữ liệu, khóa account, ghi mật khẩu và audit. |
| Dùng chung | `app/core/security.py`, `errors.py`, `exceptions.py`, `database.py`, `request_context.py`, `app/dependencies.py`: Argon2id, JWT revocation, lỗi auth, chống lộ thông tin và wiring. |
| Nhân viên | `app/modules/users/models.py`: ràng buộc trạng thái; `router.py`: dùng lại helper request ID và kiểm tra query, giữ hợp đồng endpoint users. |
| Migration | `migrations/versions/20261018_employee_status_default.py`, `20261018_auth_status_constraints.py`, `migrations/env.py`, `alembic.ini`: hỗ trợ schema cũ, trạng thái hợp lệ, test migration qua connection riêng. |
| SQL | `infra/postgres/init.sql`: trạng thái account cho database mới. |
| Dependency | `backend/pyproject.toml`, `backend/poetry.lock`: thêm và khóa Argon2id; `.gitignore`: cho phép lưu test mới và lock. |
| Test | `backend/tests/test_auth_api.py`, `test_auth_migrations.py`: các kịch bản API, transaction, concurrency và migration. |
| Tài liệu | `docs/sequence/auth.md`, `docs/sequence/users.md`, tài liệu này. |

Các đường dẫn `app/`, `migrations/`, `alembic.ini` trong bảng tính từ `backend/`.
