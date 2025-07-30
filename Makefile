# AutoGen Platform Makefile
# Central command interface for all DevOps operations

.PHONY: help build up down test clean logs ps health ci

# Default target
help:
	@echo "AutoGen Platform DevOps Commands"
	@echo "================================"
	@echo "Build & Deploy:"
	@echo "  make build          - Build all Docker images"
	@echo "  make build-no-cache - Build all images without cache"
	@echo "  make up             - Start all services"
	@echo "  make up-prod        - Start with production config"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-e2e       - Run end-to-end tests"
	@echo "  make test-perf      - Run performance tests"
	@echo "  make test-coverage  - Run tests with coverage"
	@echo "  make test-watch     - Run tests in watch mode"
	@echo ""
	@echo "Development:"
	@echo "  make logs           - Show logs from all services"
	@echo "  make logs-f         - Follow logs from all services"
	@echo "  make ps             - Show running containers"
	@echo "  make health         - Check health of all services"
	@echo "  make shell-api      - Shell into API gateway"
	@echo "  make shell-core     - Shell into core engine"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Stop containers and clean volumes"
	@echo "  make prune          - Remove unused Docker resources"
	@echo "  make reset          - Full reset (clean + remove images)"
	@echo ""
	@echo "CI/CD:"
	@echo "  make ci             - Run full CI pipeline"
	@echo "  make lint           - Run code linters"
	@echo "  make security-scan  - Run security scans"

# Variables
COMPOSE_FILE = docker-compose.yml
COMPOSE_PROD_FILE = docker-compose.prod.yml
COMPOSE_TEST_FILE = docker-compose.test.yml
COMPOSE_OVERRIDE = docker-compose.override.yml

# Build commands
build:
	@echo "🔨 Building all services..."
	docker-compose -f $(COMPOSE_FILE) build

build-no-cache:
	@echo "🔨 Building all services (no cache)..."
	docker-compose -f $(COMPOSE_FILE) build --no-cache

build-control-board:
	@echo "🔨 Building control board..."
	docker-compose -f $(COMPOSE_FILE) build control-board

# Deployment commands
up:
	@echo "🚀 Starting all services..."
	docker-compose -f $(COMPOSE_FILE) up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 5
	@make health

up-prod:
	@echo "🚀 Starting services with production config..."
	docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_PROD_FILE) up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@make health

down:
	@echo "🛑 Stopping all services..."
	docker-compose -f $(COMPOSE_FILE) down

restart: down up

# Test commands
test: test-env
	@echo "🧪 Running all tests..."
	@bash scripts/run_all_tests.sh

test-unit:
	@echo "🧪 Running unit tests..."
	docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_TEST_FILE) run --rm test-runner pytest tests/unit -v

test-integration: up
	@echo "🧪 Running integration tests..."
	docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_TEST_FILE) run --rm test-runner pytest tests/integration -v

test-e2e: up
	@echo "🧪 Running end-to-end tests..."
	docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_TEST_FILE) run --rm test-runner pytest tests/e2e -v

test-perf:
	@echo "🧪 Running performance tests..."
	docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_TEST_FILE) run --rm test-runner pytest tests/performance -v

test-coverage:
	@echo "🧪 Running tests with coverage..."
	docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_TEST_FILE) run --rm test-runner pytest --cov=. --cov-report=html --cov-report=term

test-watch:
	@echo "🧪 Running tests in watch mode..."
	docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_TEST_FILE) run --rm test-runner ptw

test-env:
	@echo "📝 Creating test environment..."
	@cp .env.example .env.test 2>/dev/null || true

# Logging and monitoring
logs:
	docker-compose -f $(COMPOSE_FILE) logs

logs-f:
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-api:
	docker-compose -f $(COMPOSE_FILE) logs api-gateway

logs-core:
	docker-compose -f $(COMPOSE_FILE) logs core-engine

ps:
	@docker-compose -f $(COMPOSE_FILE) ps

health:
	@echo "🏥 Checking service health..."
	@bash scripts/check_health.sh

# Shell access
shell-api:
	docker-compose -f $(COMPOSE_FILE) exec api-gateway /bin/sh

shell-core:
	docker-compose -f $(COMPOSE_FILE) exec core-engine /bin/bash

shell-rabbitmq:
	docker-compose -f $(COMPOSE_FILE) exec rabbitmq /bin/bash

shell-redis:
	docker-compose -f $(COMPOSE_FILE) exec redis redis-cli

# Maintenance commands
clean:
	@echo "🧹 Cleaning up..."
	docker-compose -f $(COMPOSE_FILE) down -v
	@echo "✅ Cleanup complete"

prune:
	@echo "🧹 Pruning unused Docker resources..."
	docker system prune -af --volumes

reset: clean
	@echo "💥 Full reset..."
	docker-compose -f $(COMPOSE_FILE) down --rmi all -v
	@echo "✅ Reset complete"

# CI/CD commands
ci: lint security-scan build test
	@echo "✅ CI pipeline complete"

lint:
	@echo "🔍 Running linters..."
	@bash scripts/lint.sh

security-scan:
	@echo "🔒 Running security scans..."
	@bash scripts/security_scan.sh

# Development helpers
dev: build up logs-f

dev-prod: build up-prod logs-f

# Quick status check
status: ps health

# Database commands
db-shell:
	docker-compose -f $(COMPOSE_FILE) exec redis redis-cli

db-backup:
	@echo "💾 Backing up Redis data..."
	docker-compose -f $(COMPOSE_FILE) exec redis redis-cli --rdb /data/backup.rdb

# Performance testing
perf-test:
	@echo "⚡ Running performance tests..."
	docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_TEST_FILE) run --rm test-runner locust -f tests/performance/locustfile.py --headless -u 10 -r 2 -t 30s

# Documentation
docs:
	@echo "📚 Building documentation..."
	docker run --rm -v $(PWD):/docs squidfunk/mkdocs-material build

docs-serve:
	@echo "📚 Serving documentation..."
	docker run --rm -it -p 8001:8000 -v $(PWD):/docs squidfunk/mkdocs-material

# Release commands
release-patch:
	@bash scripts/release.sh patch

release-minor:
	@bash scripts/release.sh minor

release-major:
	@bash scripts/release.sh major