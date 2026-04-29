.PHONY: help up down build logs shell-backend migrate seed test lint fmt

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Infrastructure ────────────────────────────────────────────────────────
up:  ## Start all services
	docker compose up -d

down:  ## Stop all services
	docker compose down

build:  ## Rebuild images
	docker compose build

logs:  ## Tail logs
	docker compose logs -f

logs-backend:  ## Backend logs only
	docker compose logs -f backend

logs-worker:  ## Celery worker logs
	docker compose logs -f celery_worker

# ─── Development ───────────────────────────────────────────────────────────
shell-backend:  ## Open shell in backend container
	docker compose exec backend bash

dev-backend:  ## Run backend locally (outside Docker)
	cd backend && uvicorn app.main:app --reload --port 8000

dev-worker:  ## Run Celery worker locally
	cd backend && celery -A app.tasks.celery_app worker --loglevel=info

dev-frontend:  ## Run frontend dev server
	cd frontend && pnpm dev

# ─── Database ──────────────────────────────────────────────────────────────
migrate:  ## Run Alembic migrations
	cd backend && alembic upgrade head

migrate-create:  ## Create a new migration (usage: make migrate-create MSG="add users table")
	cd backend && alembic revision --autogenerate -m "$(MSG)"

migrate-rollback:  ## Rollback last migration
	cd backend && alembic downgrade -1

db-shell:  ## Open psql shell
	docker compose exec db psql -U paraworks -d paraworks

# ─── Quality ───────────────────────────────────────────────────────────────
test:  ## Run backend tests
	cd backend && pytest -v

lint:  ## Run ruff linter
	cd backend && ruff check .

fmt:  ## Format code
	cd backend && ruff format .

# ─── Setup ─────────────────────────────────────────────────────────────────
setup:  ## First-time setup
	cp .env.example .env
	@echo "✅ .env created — please update it with real values"
	docker compose up -d db redis minio
	@echo "⏳ Waiting for DB..."
	sleep 5
	cd backend && alembic upgrade head
	@echo "✅ Migrations applied"
