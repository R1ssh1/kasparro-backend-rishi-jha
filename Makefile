.PHONY: help up down restart logs migrate test clean

# Default target
help:
	@echo "Kasparro ETL Pipeline - Available Commands"
	@echo "=========================================="
	@echo "make up          - Start all services (API + Worker + DB)"
	@echo "make down        - Stop all services"
	@echo "make restart     - Restart all services"
	@echo "make logs        - View logs from all services"
	@echo "make logs-api    - View API logs only"
	@echo "make logs-worker - View worker logs only"
	@echo "make migrate     - Run database migrations"
	@echo "make test        - Run test suite"
	@echo "make clean       - Remove containers and volumes"
	@echo "make smoke       - Run smoke test"

# Start all services
up:
	docker-compose up -d --build
	@echo "Services started! API available at http://localhost:8000"
	@echo "View API docs at http://localhost:8000/docs"

# Stop all services
down:
	docker-compose down

# Restart services
restart:
	docker-compose restart

# View all logs
logs:
	docker-compose logs -f

# View API logs only
logs-api:
	docker-compose logs -f api

# View worker logs only
logs-worker:
	docker-compose logs -f worker

# Run database migrations
migrate:
	docker-compose exec api alembic upgrade head

# Run tests
test:
	docker-compose exec api pytest tests/ -v --cov=. --cov-report=term-missing

# Clean up everything
clean:
	docker-compose down -v
	@echo "Cleaned up containers and volumes"

# Smoke test
smoke:
	@echo "Running smoke test..."
	@echo "1. Checking API health..."
	curl -s http://localhost:8000/health | python -m json.tool
	@echo "\n2. Fetching crypto data..."
	curl -s "http://localhost:8000/data?per_page=5" | python -m json.tool
	@echo "\nSmoke test complete!"
