# Simplified Makefile - 10 essential commands only

.PHONY: help up down restart logs test clean build shell status

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

logs: ## Show logs (follow mode)
	docker compose logs -f

test: ## Run tests
	python -m pytest tests/

clean: ## Clean everything (containers, volumes, images)
	docker compose down -v --remove-orphans
	docker system prune -af

build: ## Build Docker images
	docker compose build

shell: ## Open shell in app container
	docker compose exec app bash

status: ## Show container status
	docker compose ps