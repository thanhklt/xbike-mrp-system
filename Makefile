.PHONY: help up down logs build backend-shell frontend-shell db-migrate db-upgrade test lint clean

help:
	@echo "=================================================="
	@echo "            xBike MRP System CLI                  "
	@echo "=================================================="
	@echo "Available commands:"
	@echo "  make up              - Start all services with Docker Compose"
	@echo "  make down            - Stop and remove all containers"
	@echo "  make clear           - Stop containers and delete these volumes"
	@echo "  make build           - Build or rebuild Docker services"
	@echo "  make logs            - Follow logs from all containers"
	@echo "  make backend-shell   - Open bash in backend container"
	@echo "  make frontend-shell  - Open shell in frontend container"
	@echo "  make db-migrate      - Create new Alembic migration (arg: MSG='...')"
	@echo "  make db-upgrade      - Apply Alembic migrations"
	@echo "  make test            - Run all unit and integration tests"
	@echo "  make test-backend    - Run backend pytest"
	@echo "  make lint            - Run backend & frontend lint checks"
	@echo "  make clean           - Remove temporary cache and build artifacts"

up:
	docker compose up -d
down:
	docker compose down
clear:
	docker compose down -v
build:
	docker compose build

logs:
	docker compose logs -f

backend-shell:
	docker compose exec backend bash

frontend-shell:
	docker compose exec frontend sh

db-migrate:
	docker compose exec backend poetry run alembic revision --autogenerate -m "$(MSG)"

db-upgrade:
	docker compose exec backend poetry run alembic upgrade head

test: test-backend

test-backend:
	docker compose exec backend poetry run pytest

lint:
	docker compose exec backend poetry run ruff check .
	docker compose exec frontend npm run lint

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
