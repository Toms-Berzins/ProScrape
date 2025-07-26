# ProScrape Development Makefile
# Simplifies common Docker development tasks

.PHONY: help up down logs shell test seed clean build-prod dev-up dev-down status

# Default target
help:
	@echo "ProScrape Docker Commands"
	@echo "========================="
	@echo "  make up          - Start all services in production mode"
	@echo "  make dev-up      - Start all services in development mode"
	@echo "  make down        - Stop all services"
	@echo "  make dev-down    - Stop development services"
	@echo "  make logs        - Follow container logs"
	@echo "  make logs-api    - Follow API container logs"
	@echo "  make logs-worker - Follow worker container logs"
	@echo "  make shell-api   - Shell into API container"
	@echo "  make shell-worker- Shell into worker container"
	@echo "  make test        - Run test suite"
	@echo "  make seed        - Seed database with sample data"
	@echo "  make status      - Show container status"
	@echo "  make build       - Build all images"
	@echo "  make build-prod  - Build production images"
	@echo "  make clean       - Remove volumes and rebuild"
	@echo "  make monitor     - Open monitoring dashboards"
	@echo ""

# Production deployment
up:
	docker-compose up -d
	@echo "Services starting in production mode..."
	@echo "API: http://localhost:8000"
	@echo "Flower: http://localhost:5555"

# Development deployment
dev-up:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "Services starting in development mode..."
	@echo "================================================"
	@echo "Core Services:"
	@echo "  API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  Flower (Celery): http://localhost:5555"
	@echo ""
	@echo "Development Tools:"
	@echo "  Mongo Express: http://localhost:8081"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana: http://localhost:3001 (admin/admin123)"
	@echo ""
	@echo "Database Access:"
	@echo "  MongoDB: localhost:27017"
	@echo "  Redis: localhost:6379"
	@echo ""
	@echo "Debug Port: 5678 (Python debugger)"
	@echo "================================================"

# Stop services
down:
	docker-compose down

dev-down:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Logging
logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-worker:
	docker-compose logs -f celery_worker

logs-flower:
	docker-compose logs -f flower

logs-prometheus:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f prometheus

logs-grafana:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f grafana

# Shell access
shell-api:
	docker-compose exec api bash

shell-worker:
	docker-compose exec celery_worker bash

shell-redis:
	docker-compose exec redis redis-cli

shell-mongo:
	docker-compose exec mongodb mongosh

# Testing and development
test:
	docker-compose exec api pytest -v

test-coverage:
	docker-compose exec api pytest --cov=api --cov=models --cov=utils --cov-report=html

# Database operations
seed:
	docker-compose exec api python scripts/seed_data.py

seed-dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec api python scripts/seed_data.py

migrate:
	@echo "MongoDB doesn't require migrations, but running data validation..."
	docker-compose exec api python scripts/validate_data.py

# Container management
status:
	docker-compose ps

status-dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps

# Build operations
build:
	docker-compose build

build-prod:
	docker build -f docker/Dockerfile.api -t proscrape-api:latest .
	docker build -f docker/Dockerfile.worker -t proscrape-worker:latest .
	@echo "Production images built:"
	@echo "  proscrape-api:latest"
	@echo "  proscrape-worker:latest"

# Cleanup operations
clean:
	docker-compose down -v
	docker system prune -f
	@echo "All containers, volumes, and unused images removed"

clean-dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
	docker system prune -f

# Reset database
reset-db:
	docker-compose stop mongodb
	docker volume rm proscrape_mongodb_data || true
	docker-compose up -d mongodb
	@echo "Database reset complete"

# Monitoring shortcuts
monitor:
	@echo "Opening monitoring dashboards..."
	@echo "Grafana: http://localhost:3001"
	@echo "Prometheus: http://localhost:9090"
	@echo "Flower: http://localhost:5555"

# Development workflow shortcuts
dev-restart:
	make dev-down
	make dev-up

dev-rebuild:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Quick development commands
quick-test: dev-up test

quick-seed: dev-up seed-dev

# Production deployment helpers
prod-deploy:
	make build-prod
	make up
	@echo "Production deployment complete"

# Health checks
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health || echo "API not responding"
	@curl -s http://localhost:5555/api/workers || echo "Flower not responding"

# Docker system info
docker-info:
	@echo "Docker system information:"
	@echo "=========================="
	docker system df
	@echo ""
	@echo "Running containers:"
	docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Backup operations
backup-data:
	@echo "Creating data backup..."
	mkdir -p backups
	docker-compose exec mongodb mongodump --out /tmp/backup
	docker cp $$(docker-compose ps -q mongodb):/tmp/backup ./backups/mongodb-$$(date +%Y%m%d-%H%M%S)
	@echo "Backup created in ./backups/"

# Development environment setup
setup-dev:
	@echo "Setting up development environment..."
	@echo "1. Creating required directories..."
	mkdir -p docker/data/mongodb docker/data/redis
	mkdir -p docker/monitoring/grafana/dashboards
	mkdir -p docker/monitoring/grafana/provisioning/datasources
	mkdir -p docker/monitoring/grafana/provisioning/dashboards
	mkdir -p scripts/dev-tools
	@echo "2. Copying environment file..."
	cp .env.example .env || echo ".env already exists"
	@echo "3. Building development images..."
	make build
	@echo "Development environment setup complete!"
	@echo "Run 'make dev-up' to start services"