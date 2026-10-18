# 🚴 xBike MRP System

**xBike MRP System** is a modern, enterprise-grade Manufacturing Resource Planning (MRP) solution engineered specifically for bicycle manufacturing and assembly operations. It streamlines material requirements planning, multi-level Bills of Materials (BOM), inventory tracking, procurement, work order execution, and dispatching.

---

## 🏗️ Architecture & Tech Stack

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+) - High performance, automatic OpenAPI documentation.
- **ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async Engine with `asyncpg`).
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/).
- **Validation & Serialization**: [Pydantic v2](https://docs.pydantic.dev/).
- **Authentication**: JWT-based OAuth2 with bcrypt password hashing and Role-Based Access Control (RBAC).
- **Testing & Code Quality**: `pytest`, `httpx`, `ruff`.

### Frontend
- **Framework**: [React 18+](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/) + [Vite](https://vitejs.dev/).
- **State & Data Fetching**: [TanStack Query (React Query)](https://tanstack.com/query/latest) + [Axios](https://axios-http.com/).
- **Styling**: Modular CSS / Modern UI tokens with sleek dark/light aesthetic.
- **Icons**: [Lucide React](https://lucide.dev/).
- **Routing**: [React Router v6](https://reactrouter.com/).

### Infrastructure & DevOps
- **Database**: PostgreSQL 16
- **Reverse Proxy**: Nginx
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions (linting, type checking, unit tests)

---

## 📁 Project Directory Structure

```text
xbike-mrp-system/
├── .github/
│   └── workflows/
│       ├── backend-ci.yml           # Backend linting & automated test workflow
│       └── frontend-ci.yml          # Frontend linting, typecheck & build workflow
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entrypoint & middleware
│   │   ├── core/                    # Core configuration, DB, security & exceptions
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── exceptions.py
│   │   │   ├── logging.py
│   │   │   └── security.py
│   │   │
│   │   ├── modules/                 # Modular domain-driven feature modules
│   │   │   ├── auth/                # Authentication & JWT tokens
│   │   │   ├── users/               # User management & roles
│   │   │   ├── catalog/             # Bicycle parts, assemblies & specifications
│   │   │   ├── suppliers/           # Vendor management & purchase catalog
│   │   │   ├── bom/                 # Multi-level Bill of Materials
│   │   │   ├── inventory/           # Stock on hand, bins & warehouse transactions
│   │   │   ├── receiving/           # Goods receipt notes (GRN) & quality inspection
│   │   │   ├── material_issuing/    # Material picking & staging for shop floor
│   │   │   ├── production/          # Work orders & shop floor assembly tracking
│   │   │   ├── finished_goods_issuing/ # Finished bike dispatch & shipment
│   │   │   ├── reporting/           # MRP run calculations, stock & production analytics
│   │   │   └── audit/               # Immutable compliance audit logging
│   │   │
│   │   └── shared/                  # Common utilities, enums & pagination
│   │       ├── enums.py
│   │       └── pagination.py
│   │
│   ├── migrations/                  # Alembic database migration scripts
│   ├── tests/                       # Pytest test suite
│   ├── alembic.ini                  # Alembic environment config
│   ├── Dockerfile                   # Backend Docker container recipe
│   ├── pyproject.toml               # Python dependencies and tool settings
│   └── .env.example                 # Backend environment variable template
│
├── frontend/
│   ├── src/
│   │   ├── app/                     # App entry point, routing setup, providers
│   │   ├── components/              # Shared UI components (Buttons, Modals, Tables)
│   │   ├── features/                # Domain-specific UI features & view models
│   │   │   ├── auth/
│   │   │   ├── materials/
│   │   │   ├── products/
│   │   │   ├── suppliers/
│   │   │   ├── bom/
│   │   │   ├── inventory/
│   │   │   ├── receiving/
│   │   │   ├── material-issuing/
│   │   │   ├── production/
│   │   │   ├── finished-goods-issuing/
│   │   │   └── reports/
│   │   ├── layouts/                 # Application layouts (Sidebar, Header, Main layout)
│   │   ├── lib/                     # Axios instance & TanStack query client
│   │   │   ├── api/
│   │   │   └── query-client.ts
│   │   ├── routes/                  # Route definitions and protected route wrappers
│   │   ├── types/                   # TypeScript interfaces & domain models
│   │   ├── main.tsx                 # React DOM mount point
│   │   └── vite-env.d.ts            # Vite client types
│   │
│   ├── Dockerfile                   # Frontend Docker container recipe
│   ├── package.json                 # Node dependencies and scripts
│   ├── tsconfig.json                # TypeScript compiler configuration
│   ├── vite.config.ts               # Vite bundler configuration
│   ├── eslint.config.js             # Modern ESLint configuration
│   ├── .prettierrc                  # Code formatter configuration
│   └── .env.example                 # Frontend environment variables template
│
├── infra/
│   └── nginx/
│       └── nginx.conf               # Nginx reverse proxy configuration
│
├── docs/
│   ├── architecture.md              # Domain architecture & MRP logic design
│   └── api-conventions.md           # REST conventions, response shapes & error codes
│
├── .env.example                     # Root Docker Compose environment variables
├── .gitignore                       # Repository-wide ignore rules
├── docker-compose.yml               # Multi-container local orchestration
├── Makefile                         # Helpful dev CLI commands
└── README.md                        # Project documentation
```

---

## 🚀 Quick Start

### 1. Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
- Alternatively for local dev: Python 3.11+, Node.js 20+, PostgreSQL 16+

### 2. Environment Setup
Copy the environment template files:
```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

### 3. Run with Docker Compose
To build and start all containers (Postgres, Backend, Frontend, Nginx):
```bash
docker compose up --build -d
```

Access the services:
- **Application Portal (via Nginx)**: [http://localhost](http://localhost)
- **Frontend Directly**: [http://localhost:5173](http://localhost:5173)
- **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **OpenAPI JSON**: [http://localhost:8000/api/v1/openapi.json](http://localhost:8000/api/v1/openapi.json)

---

## 💻 Local Development Without Docker

### Backend

Install Poetry 2.4.1 first: `python -m pip install "poetry==2.4.1"`.
Poetry manages the virtual environment outside this repository, using
[`backend/poetry.toml`](backend/poetry.toml). Dependency versions are locked
in `backend/poetry.lock`; include that file when committing dependency changes.

```bash
cd backend
poetry env use python3.11
poetry sync --with dev
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload --port 8000
```

On Windows, use `poetry env use python` if Python 3.11 is available as `python`.
Use `poetry add <package>` for runtime dependencies and
`poetry add --group dev <package>` for development tools.
Use `poetry run pytest`, `poetry run ruff check .`, and
`poetry run ruff format --check .` inside `backend` to verify changes.
See [Poetry environment documentation](https://python-poetry.org/docs/managing-environments/).

Docker installs only runtime dependencies by default. The development Compose
configuration enables the `dev` group so container test/lint commands work.

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Testing & Quality Checks

Run backend tests:
```bash
make test-backend
```

Run linter checks:
```bash
make lint
```

---

## 📄 License
Proprietary / Internal project for **xBike Manufacturing Systems**.
