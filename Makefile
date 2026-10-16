.PHONY: dev build test lint format compose-up compose-build

dev:
	docker compose up --build

build:
	cd upcode-sprint && npm run build

test:
	cd upcode-sprint-service && pytest
	cd upcode-sprint && npm test

lint:
	cd upcode-sprint-service && ruff check .
	cd upcode-sprint && npm run lint
	cd upcode-sprint && npm run typecheck

format:
	cd upcode-sprint-service && ruff format .
	cd upcode-sprint && npm run format

compose-up:
	docker compose up -d

compose-build:
	docker compose build

