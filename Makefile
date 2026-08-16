.PHONY: dev build test lint format compose-up compose-build

dev:
	docker compose up --build

build:
	cd frontend && npm run build

test:
	cd backend && pytest

lint:
	cd backend && ruff check .
	cd frontend && npm run lint
	cd frontend && npm run typecheck

format:
	cd backend && ruff format .
	cd frontend && npm run format

compose-up:
	docker compose up -d

compose-build:
	docker compose build

