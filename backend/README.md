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
│       ├── mat_hang/
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

Đã hợp nhất mặt hàng vào mat_hang theo init.sql hiện tại bên cạnh auth, nhân viên và audit; các module còn dùng ton_kho hoặc ORM nghiệp vụ cũ sẽ được chuyển đổi ở tác vụ sau. Frontend vẫn dùng luồng demo riêng, chưa tích hợp đăng nhập thật.

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


## API nhân viên và vai trò

Module có models.py, router.py, schemas.py, ports.py, repository.py, service.py và __init__.py. Xem [sequence nhân viên](../docs/sequence/nhan_vien.md) để đối chiếu chi tiết.

| Method | Path | Quyền |
| --- | --- | --- |
| GET | `/api/v1/nhan_vien` | Admin/quản lý, projection theo quyền |
| GET | `/api/v1/nhan_vien/{id}` | Admin/quản lý hoặc chính mình |
| POST | `/api/v1/nhan_vien` | Admin |
| PATCH | `/api/v1/nhan_vien/{id}` | Admin |
| DELETE | `/api/v1/nhan_vien/{id}` | Admin, chuyển sang bi_khoa |
| PUT | `/api/v1/nhan_vien/{id}/vai_tro` | Admin |
| POST | `/api/v1/nhan_vien/{id}/mo_khoa` | Admin |
| GET | `/api/v1/vai_tro` | Admin/quản lý |

GET chi tiết trả ETag. Gửi nguyên giá trị trong If-Match cho PATCH/PUT/DELETE/mở khóa: thiếu trả 428, cũ trả 412. POST tạo trả 201 cùng Location/ETag; các thao tác còn lại trả 200 cùng ETag, riêng DELETE trả 204 không body cùng ETag mới.

Quyết định ngày 01/11/2026: DELETE là soft delete, thay thế `/vo_hieu_hoa`. DELETE và mở khóa đều nhận body JSON bắt buộc `{"ly_do":"Lý do thao tác"}`. Với HTTPX, dùng client.request("DELETE", ..., json=...). Gọi sai trạng thái trả 409. Tài khoản khóa vẫn được lưu/tra cứu; mở khóa không cấp JWT mới.

Một admin được bootstrap sẵn; API chặn tạo/cấp thêm admin, hạ quyền hoặc khóa admin đó. PATCH chỉ admin và chỉ sửa hồ sơ. Lỗi nhân viên/vai trò dùng error/meta.request_id theo contract v2; client đang đọc success/timestamp cũ cần cập nhật phần xử lý lỗi.

Test PostgreSQL cần TEST_DATABASE_URL trỏ database riêng có tên kết thúc `_test`. test_nhan_vien_postgres.py tạo schema ngẫu nhiên để dùng connection cạnh tranh. Fixture đã commit được giữ trong database test; không reset hoặc ghi vào database ứng dụng.


## API mặt hàng và danh mục trong bộ nhớ

Module `mat_hang` sở hữu ORM `MatHang`, bảng `"MatHang"`. Xem [sequence mặt hàng](../docs/sequence/mat_hang.md). Nhóm `catalog/parts` cũ đã được thay thế; không còn module nghiệp vụ `catalog` hoặc `danh_muc_mat_hang` thứ hai.

| Method | Path | Quyền |
| --- | --- | --- |
| GET | `/api/v1/danh_muc_mat_hang/` | Admin/quản lý/nhân viên; toàn bộ danh mục, không phân trang |
| GET | `/api/v1/mat_hang` | Admin/quản lý/nhân viên; tìm kiếm, lọc, sort, phân trang |
| GET | `/api/v1/mat_hang/{id}` | Admin/quản lý/nhân viên; ETag |
| POST | `/api/v1/mat_hang` | Chỉ quản lý; 201, Location/ETag |
| PATCH | `/api/v1/mat_hang/{id}` | Chỉ quản lý; If-Match, 200/ETag |
| DELETE | `/api/v1/mat_hang/{id}` | Chỉ quản lý; If-Match, 204, soft delete |

GET mặc định bao gồm cả hoạt động và bị khóa. UI dùng `is_active` để hiển thị trạng thái; filter `is_active` chỉ áp dụng khi client gửi rõ. Danh mục trả `{data, meta: {total, request_id}}`; list mặt hàng có meta phân trang. Tên mặt hàng bắt buộc và không được trắng. Giá dùng NUMERIC(18,2)/Decimal, JSON là chuỗi như `"123.45"` hoặc null. `so_luong_ton` và `ton_kho_updated_at` chỉ đọc, không nhận qua POST/PATCH danh mục.

DELETE chỉ đặt `is_active=false`, không xóa bản ghi/quan hệ/tồn kho. Có BOM/chứng từ hoặc tồn dương vẫn được ngừng hoạt động. Mặt hàng bị khóa bị chặn ở backend khi tạo tài liệu mới qua các service nghiệp vụ hiện có. Lịch sử vẫn đọc được; không tự hủy các chứng từ đang xử lý. Các module nghiệp vụ còn lệch ORM/SQL chưa được tuyên bố đạt E2E, và endpoint yêu cầu sản xuất theo contract chưa được bổ sung trong tác vụ này.

Snapshot nạp trong lifespan trước khi phục vụ; auth vẫn kiểm tra DB hiện hành nhưng các GET mặt hàng không SELECT bảng MatHang. Ghi và audit dùng chung transaction; chỉ sau commit mới công bố cache trước response thành công. Cache bất biến theo application instance. Tác vụ async lắng nghe PostgreSQL LISTEN/NOTIFY, gom tín hiệu và nạp lại qua session riêng; reconnect kèm full reload và đối soát mỗi 30 giây. Chưa sẵn sàng/đồng bộ lỗi trả 503 thay vì giả danh mục rỗng hoặc fallback GET trực tiếp DB. Shutdown đóng listener và worker.

Giới hạn thấy-ngay-sau-ghi được kiểm chứng trên một worker. Nhiều worker/instance có snapshot riêng và đồng bộ bất đồng bộ; chưa cam kết GET tức thời giữa các worker. Không sửa init.sql để tạo lại ton_kho cho code cũ. Thay đổi bootstrap yêu cầu database mới/trống; không áp dụng SQL/seed lại lên database ứng dụng hiện có.

Kiểm thử mặt hàng (TEST_DATABASE_URL chỉ trỏ database riêng kết thúc _test):

```powershell
poetry run pytest tests/test_mat_hang.py tests/test_mat_hang_cache.py tests/test_mat_hang_schema.py tests/test_mat_hang_active_guard.py tests/test_mat_hang_postgres.py -q
```

Test notification/concurrency cần COMMIT thật trên database test riêng; không thay bằng SQLite hoặc chỉ outer rollback. Thư mục tests và docs/plans có quy tắc ignore hiện hữu; kiểm tra các file mới khi dev chuẩn bị commit, tác vụ này không stage/commit.
