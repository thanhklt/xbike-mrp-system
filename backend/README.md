# Backend xBike MRP — demo Docker

## Tech stack

| Thành phần | Công nghệ |
| --- | --- |
| Ngôn ngữ | Python 3.11+; Docker image dùng Python 3.11 |
| API / server | FastAPI, Uvicorn |
| Validation / DTO | Pydantic 2 |
| Database | PostgreSQL 16 |
| ORM / driver | SQLAlchemy 2 AsyncSession, asyncpg |
| Xác thực | JWT qua python-jose; hash mới bằng Argon2id, hỗ trợ kiểm tra bcrypt cũ |
| Cấu hình | YAML qua PyYAML, dataclass Settings |
| Dependency / môi trường | Poetry, Docker Compose |
| Kiểm thử / chất lượng code | pytest, pytest-asyncio, HTTPX, Ruff, mypy |

Backend tổ chức theo modular monolith. Auth gọi public service nhân viên; module nhân viên sở hữu tài khoản/vai trò, module audit sở hữu lịch sử thao tác.

## Cấu trúc thư mục

Các đường dẫn bên dưới tính từ thư mục gốc repository:

```text
backend/
├── app/
│   ├── main.py                 # FastAPI app, middleware, đăng ký router
│   ├── dependencies.py         # Ghép service/repository, auth dependency
│   ├── models.py               # Registry tập hợp ORM của các module
│   ├── config/
│   │   ├── config.yml          # Giá trị cấu hình ứng dụng
│   │   └── settings.py         # Đọc YAML, tạo Settings dùng chung
│   ├── core/                  # Database/session, security, lỗi, transaction
│   ├── shared/                # Pagination, records, enum dùng chung
│   └── modules/
│       ├── auth/              # router.py, schema.py, service.py
│       ├── nhan_vien/         # Nhân viên, tài khoản và vai trò
│       ├── audit/             # Đọc và append lịch sử thao tác
│       ├── bom/
│       ├── catalog/
│       ├── finished_goods_issuing/
│       ├── inventory/
│       ├── material_issuing/
│       ├── production/
│       ├── receiving/
│       ├── reporting/
│       └── suppliers/
├── tests/                     # Unit, API, repository, schema, boundaries
├── Dockerfile
├── pyproject.toml             # Dependency và cấu hình công cụ
└── README.md
infra/
├── docker-compose.yml         # Chạy riêng PostgreSQL
└── postgres/
    ├── init.sql               # Bootstrap schema trên database trống
    └── seed.sql               # Dữ liệu và tài khoản demo
docs/sequence/                 # Sequence diagram theo module
docker-compose.yml             # PostgreSQL, backend, frontend, nginx
```

Các module có tầng lưu trữ thường gồm `router.py`, `schemas.py`, `service.py`, `ports.py`, `repository.py`, `models.py`. Auth dùng `schema.py` số ít và không có ORM/repository riêng.

## How to run

### 1. Chuẩn bị cấu hình

Cần Docker Desktop; nếu chạy backend trên máy, cài thêm Python 3.11+ và Poetry 2.4.x. Các lệnh dưới đây dùng PowerShell, bắt đầu từ thư mục gốc repository.

Đối chiếu `.env` với `.env.example` để cấu hình PostgreSQL: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`. Backend đọc **`backend/app/config/config.yml`**, không tự lấy các giá trị ứng dụng từ `.env` hoặc environment của Compose.

Điền `database_url` trong YAML theo nơi chạy backend:

| Cách chạy backend | Host / port PostgreSQL trong URL |
| --- | --- |
| Trên máy host | `localhost` và `POSTGRES_PORT` đã publish, mặc định `5432` |
| Trong Compose gốc | `postgres:5432` |

Dạng URL: `postgresql+asyncpg://<user>:<password>@<host>:<port>/<database>`. Thay các phần trong dấu `<...>` bằng cấu hình thực tế; user/password/database phải khớp PostgreSQL. Các giá trị `secret_key`, `algorithm`, `access_token_expire_minutes` và CORS cũng lấy từ YAML; không ghi thông tin vận hành nhạy cảm lên log hoặc commit.

### 2. Chạy backend trên máy, PostgreSQL bằng Docker

Từ thư mục gốc, khởi động PostgreSQL riêng:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d postgres
docker compose --env-file .env -f infra/docker-compose.yml ps
```

Khi PostgreSQL healthy, chạy backend với `database_url` dùng host `localhost`:

```powershell
cd backend
poetry sync --with dev
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Giữ terminal chạy Uvicorn. Những lần sau chỉ cần chạy lại lệnh `poetry run uvicorn ...` khi dependency không thay đổi.

### 3. Cách thay thế: chạy backend và PostgreSQL trong Docker

Từ thư mục gốc, dùng Compose gốc và đặt host PostgreSQL trong YAML thành `postgres`:

```powershell
docker compose --env-file .env up -d --build backend
docker compose --env-file .env logs -f backend
```

Lệnh này khởi động cả PostgreSQL do backend phụ thuộc service đó. Không chạy đồng thời PostgreSQL của hai file Compose vào cùng cổng. Không chạy hai backend cùng cổng 8000. Với Docker, cổng backend mặc định 8000; nếu `.env` đặt `BACKEND_PORT` khác thì dùng cổng đó khi mở trình duyệt.

### 4. Mở API và đăng nhập thử

- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs).
- Health: [http://localhost:8000/health](http://localhost:8000/health).
- Địa chỉ `http://localhost:8000/` trả 404 vì chưa có endpoint `/`.

Tài khoản được tạo bởi `infra/postgres/seed.sql` trên database demo mới/trống:

| Vai trò | Tên đăng nhập | Mật khẩu demo |
| --- | --- | --- |
| Quản trị viên | `quan_tri` | `DemoXbike2026!` |
| Quản lý | `quan_ly_kho` | `DemoXbike2026!` |
| Nhân viên | `nhan_vien_sx` | `DemoXbike2026!` |

Trong Swagger, bấm **Authorize**, nhập `username=quan_tri`, `password=DemoXbike2026!`, rồi xác nhận. Swagger dùng endpoint `/api/v1/auth/token`; sau đó có thể thử `GET /api/v1/auth/me`, `GET /api/v1/nhan_vien` và `GET /api/v1/audit` theo quyền tài khoản.

Hoặc thử `POST /api/v1/auth/dang_nhap` với JSON:

```json
{
  "ten_dang_nhap": "quan_tri",
  "mat_khau": "DemoXbike2026!"
}
```

Lấy `data.access_token` từ response để gửi header `Authorization: Bearer <access_token>` khi gọi API cần xác thực. Nếu đã đổi mật khẩu tài khoản, dùng mật khẩu mới; mật khẩu trong bảng chỉ là giá trị seed ban đầu.

### Lưu ý về bootstrap và phạm vi demo

PostgreSQL tự chạy `init.sql` rồi `seed.sql` trong `/docker-entrypoint-initdb.d` khi khởi tạo thư mục dữ liệu mới/trống. Ba bảng của luồng này là `"NhanVien"`, `"VaiTro"`, `"LichSuThaoTac"`; tên cột và mã nghiệp vụ giữ nguyên.

Không có migration hoặc bước Alembic. Restart/rebuild container dùng volume cũ không cập nhật schema hay tự tạo tài khoản seed. Nếu đã có dữ liệu/schema cũ, báo dev để bố trí môi trường demo trống riêng; không tự chạy `make clear`, `docker compose down -v` hoặc seed lại database.

Phạm vi refactor hiện tại là auth, nhân viên và audit; chưa đồng bộ toàn bộ ORM nghiệp vụ với SQL v4. Frontend vẫn dùng luồng demo riêng, chưa tích hợp đăng nhập thật.

## Kiểm tra API

- `GET /health`, `GET /api/v1/ping`: kiểm tra backend đang phục vụ.
- Swagger: `/docs`.
- `POST /api/v1/auth/dang_nhap`: JSON `ten_dang_nhap`, `mat_khau`; các tài khoản/mật khẩu demo được khai báo trong `infra/postgres/seed.sql`.
- `POST /api/v1/auth/token`: form OAuth2 cho Swagger, hỗ trợ username hoặc email duy nhất.
- `GET /api/v1/auth/me`: dùng Bearer JWT lấy hồ sơ bản thân và ETag.
- `POST /api/v1/auth/doi_mat_khau`: JSON `mat_khau_hien_tai`, `mat_khau_moi`; sau thành công token cũ hết hiệu lực, cần đăng nhập lại.
- `GET /api/v1/nhan_vien`, `GET /api/v1/nhan_vien/{id}`: quyền và projection theo vai trò.
- `GET /api/v1/audit`: admin/quản lý đọc lịch sử; đổi mật khẩu ghi audit cùng transaction. Không có endpoint công khai ghi/sửa/xóa lịch sử.

Auth có ba file chức năng `router.py`, `schema.py`, `service.py`; chỉ gọi public `NhanVienService`. Password hash và ORM không đi qua hợp đồng public sang auth. Xem sequence tại `docs/sequence/{auth,nhan_vien,audit}.md` tính từ root.

## Kiểm thử

Trong thư mục backend, cài dependency dev bằng Poetry và đặt `TEST_DATABASE_URL` trỏ PostgreSQL test riêng đã bootstrap SQL, tên database kết thúc `_test`:

```powershell
poetry run pytest tests/test_module_boundaries.py tests/test_auth_service.py tests/test_nhan_vien_auth_service.py tests/test_auth_api.py tests/test_nhan_vien_schema.py tests/test_audit_schema.py -q
poetry run pytest -q
```

Test HTTP dùng transaction/savepoint rollback; test concurrency dùng schema riêng trong database test. Tuyệt đối không trỏ TEST_DATABASE_URL về database ứng dụng. Test schema/trigger cần bootstrap SQL thật, không thay bằng `metadata.create_all()`.

`test_schema_contract.py` và `test_postgres_seed.py` còn kiểm tra toàn bộ ORM nghiệp vụ; các lỗi lệch SQL v4 ngoài ba bảng này được giữ để theo dõi, không làm yếu assertion để ép suite xanh. Dev đã xác nhận xử lý phần đó trong tác vụ riêng. Không có test hoặc target Makefile cho migration.
