.PHONY: fmt lint test up down logs install-precommit

fmt:
	black .
	isort .

lint:
	flake8

install-precommit:
	pip install pre-commit && pre-commit install

test:
	pytest -q

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f | cat
