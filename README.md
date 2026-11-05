# xBike MRP System

## 1. Giới thiệu project

**xBike MRP System** là hệ thống nội bộ hỗ trợ quản lý nhu cầu vật tư, sản xuất và tồn kho cho doanh nghiệp sản xuất, lắp ráp và bán xe đạp.

Phạm vi nghiệp vụ gồm quản lý mặt hàng (nguyên vật liệu, linh kiện, bán thành phẩm, thành phẩm), nhà cung cấp, công thức BOM nhiều cấp, nhập/xuất kho, yêu cầu và lệnh sản xuất, chứng từ hoàn thành sản xuất, điều chỉnh kho, báo cáo và lịch sử thao tác.

Hệ thống phục vụ ba nhóm người dùng: **Quản trị viên**, **Quản lý kho** và **Nhân viên**. Backend tổ chức theo kiến trúc **modular monolith**, frontend giao tiếp với backend qua REST API.

Phạm vi sản phẩm tham chiếu [PRD v0.2 — `xbike_prd_v2.docx`](https://drive.google.com/file/d/1OaRwraXHxPGA6l7P2vJwhdjdc5juXdDY/view) và [SRS — `SRS_v4.txt` (nội dung phiên bản 3.0)](https://drive.google.com/file/d/1GTqAuq1JTyMBt-Xu6BXorSJAFDhg87zn/view). Đây là mô tả phạm vi nghiệp vụ, không phải xác nhận toàn bộ chức năng đã được triển khai và kiểm thử.

## 2. Công thức BOM

**BOM (Bill of Materials)** là danh sách thành phần và định mức số lượng cần để sản xuất **một đơn vị** thành phẩm hoặc bán thành phẩm.

Theo mục 3 của SRS và FR-03, FR-07, FR-08 của PRD trên Drive, bốn model thành phẩm demo là **Mountain Pro**, **City Ride**, **Speed Sport** và **Kids Fun**. Mỗi model có BOM riêng với cấu trúc thành phần sau:

```text
Xe đạp (thành phẩm, theo từng model)
├── Khung xe
├── Phuộc xe
├── Cụm bánh xe (bán thành phẩm)
│   ├── Vành bánh xe
│   ├── Moay-ơ
│   └── Nan hoa
├── Lốp xe
├── Xích xe
├── Bàn đạp
├── Dây phanh
├── Yên xe
├── Đĩa xích
└── Bộ ốc vít
```

Các thành phần ngoài cụm bánh xe được phân loại là nguyên vật liệu/linh kiện. Tài liệu nguồn **chưa ấn định định mức số lượng kỹ thuật hoặc mã linh kiện dùng chung giữa các model**. Quản lý kho khai báo mã mặt hàng, đơn vị tính và định mức dương cho từng dòng BOM.

Cách tính nhu cầu theo tài liệu:

| Đại lượng | Công thức |
| --- | --- |
| Số lượng thành phẩm cần sản xuất | `max(0, số lượng yêu cầu − tồn thành phẩm hiện có)` |
| Nhu cầu trực tiếp của một thành phần | `số lượng của lệnh × định mức thành phần trong BOM đã chốt` |
| Số lượng bán thành phẩm cần sản xuất thêm | `max(0, nhu cầu bán thành phẩm − tồn bán thành phẩm được phân bổ)` |
| Nhu cầu linh kiện cho lệnh con | `số lượng bán thành phẩm cần sản xuất thêm × định mức trong BOM của bán thành phẩm` |

Ưu tiên dùng bán thành phẩm có sẵn; chỉ phân rã BOM và lập lệnh con cho phần thiếu. Lệnh cha lưu nhu cầu cụm bánh xe, lệnh con lưu nhu cầu vành, moay-ơ và nan hoa; tránh tính trùng linh kiện của cụm đã có trong kho hoặc phân bổ cùng một lượng tồn cho nhiều nhánh.

Ví dụ trong PRD: lệnh cha cần **20 cụm bánh xe**, kho có **8 cụm**, thì nhu cầu trực tiếp của cha vẫn là **20 cụm**, lệnh con sản xuất thêm **12 cụm**. Đây là dữ liệu minh họa kiểm thử, không phải định mức kỹ thuật đã chốt.

BOM không được trùng mã thành phần hoặc có tham chiếu vòng. Mỗi mặt hàng có tối đa một BOM hiện hành; BOM đã được lệnh sử dụng phải giữ bất biến, thay đổi bằng phiên bản mới. Mỗi lệnh chốt BOM và lưu bản chụp nhu cầu. Việc tính nhu cầu không giữ chỗ hoặc thay đổi tồn kho; tồn được kiểm tra lại khi duyệt xuất.

## 3. Cấu trúc thư mục

Cấu trúc chính theo repository hiện tại, lược bỏ thư mục cache, môi trường ảo, dependency và kết quả build:

```text
xbike-mrp-system/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, middleware, đăng ký router
│   │   ├── dependencies.py         # Ghép dependency và kiểm tra xác thực
│   │   ├── models.py               # Đăng ký ORM của các module
│   │   ├── config/                 # Cấu hình ứng dụng
│   │   ├── core/                   # Database, security, lỗi và transaction
│   │   ├── shared/                 # Enum, phân trang và cấu trúc dùng chung
│   │   └── modules/                # Các module nghiệp vụ
│   │       ├── audit/
│   │       ├── auth/
│   │       ├── bom/
│   │       ├── dieu_chinh_kho/
│   │       ├── finished_goods_issuing/
│   │       ├── inventory/
│   │       ├── material_issuing/
│   │       ├── mat_hang/
│   │       ├── nhan_vien/
│   │       ├── nha_cung_cap/
│   │       ├── phieu_nhap/
│   │       ├── phieu_xuat/
│   │       ├── reporting/
│   │       └── san_xuat/
│   ├── tests/                      # Kiểm thử backend
│   ├── Dockerfile
│   ├── pyproject.toml              # Dependency Python và cấu hình công cụ
│   ├── poetry.lock
│   └── README.md                   # Tài liệu riêng cho backend
├── frontend/
│   ├── src/
│   │   ├── main.jsx                # Điểm khởi tạo React
│   │   ├── app/                    # App và provider
│   │   ├── components/             # Thành phần giao diện dùng chung
│   │   ├── features/               # Giao diện theo nhóm nghiệp vụ
│   │   ├── layouts/                # Bố cục trang
│   │   ├── lib/                    # API client, query client và tiện ích
│   │   └── routes/                 # Điều hướng và bảo vệ route
│   ├── tests/                      # Kiểm thử logic và trình duyệt
│   ├── Dockerfile
│   ├── package.json                # Dependency JavaScript và script
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── playwright.config.js
│   └── README.md                   # Tài liệu riêng cho frontend
├── infra/
│   ├── postgres/
│   │   ├── init.sql                # Schema bootstrap cho database mới/trống
│   │   └── seed.sql                # Dữ liệu khởi tạo
│   ├── nginx/nginx.conf            # Cấu hình reverse proxy
│   └── docker-compose.yml
├── docs/
│   ├── sequence/                  # Sequence diagram theo module backend
│   ├── plans/                     # Kế hoạch và biên bản kiểm chứng
│   ├── examples/                  # Ví dụ request/dữ liệu API
│   ├── architecture.md
│   ├── api-conventions.md
│   └── api_contract_v3.md
├── intent/                        # Ghi nhận ý định và phạm vi công việc
├── .handoff/                      # Tài liệu bàn giao và kiểm chứng
├── .env.example
├── docker-compose.yml             # Điều phối PostgreSQL, backend, frontend, Nginx
├── Makefile
└── README.md
```

## 4. Tech stack

| Thành phần | Công nghệ đang sử dụng |
| --- | --- |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Validation | Pydantic 2 |
| ORM và driver | SQLAlchemy 2 với AsyncSession, asyncpg |
| Database | PostgreSQL 16 |
| Xác thực và phân quyền | JWT qua python-jose, phân quyền theo vai trò; mật khẩu mới dùng Argon2id, hỗ trợ kiểm tra bcrypt cũ |
| Frontend | React 18, JavaScript (`.jsx`/`.js`), Vite 5 |
| Điều hướng | React Router 6 |
| Dữ liệu phía frontend | TanStack Query 5, Axios |
| Giao diện | CSS, Lucide React, clsx |
| Quản lý dependency | Poetry cho backend; npm cho frontend |
| Hạ tầng | Docker, Docker Compose, Nginx |
| Kiểm thử và chất lượng | pytest, pytest-asyncio, HTTPX, Ruff, mypy; Node.js test runner, Playwright, ESLint, Prettier |

Tech stack được đối chiếu với [backend/pyproject.toml](backend/pyproject.toml), [frontend/package.json](frontend/package.json) và [docker-compose.yml](docker-compose.yml). Demo Docker hiện tại khởi tạo database mới/trống qua `init.sql` và `seed.sql`; chưa áp dụng migration.
