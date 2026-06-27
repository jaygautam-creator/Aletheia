.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help install install-backend install-frontend dev dev-backend dev-frontend \
        test test-backend test-frontend lint lint-backend lint-frontend \
        format type-check phase1-demo up down logs clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend dependencies (uv)
	uv --directory backend sync

install-frontend: ## Install frontend dependencies (npm)
	npm --prefix frontend ci

dev: ## Run backend (:8000) and frontend (:3000) dev servers together
	@trap 'kill 0' EXIT; \
		uv --directory backend run uvicorn aletheia.main:app --reload --port 8000 & \
		npm --prefix frontend run dev & \
		wait

dev-backend: ## Run only the backend dev server
	uv --directory backend run uvicorn aletheia.main:app --reload --port 8000

dev-frontend: ## Run only the frontend dev server
	npm --prefix frontend run dev

test: test-backend test-frontend ## Run all tests / checks

test-backend: ## Run backend tests (pytest)
	uv --directory backend run pytest

test-frontend: ## Build the frontend (compiles + type-checks)
	npm --prefix frontend run build

lint: lint-backend lint-frontend ## Lint everything

lint-backend: ## Lint the backend (ruff)
	uv --directory backend run ruff check .

lint-frontend: ## Lint the frontend (eslint)
	npm --prefix frontend run lint

format: ## Format the backend (ruff)
	uv --directory backend run ruff format .

type-check: ## Type-check the backend (mypy)
	uv --directory backend run mypy src

phase1-demo: ## Run the Phase 1 grounded-vs-baseline comparison (needs an LLM key in .env)
	uv --directory backend run python -m aletheia.evaluation.phase1

up: ## Start the full stack via docker compose
	docker compose up --build

down: ## Stop the stack and remove containers
	docker compose down

logs: ## Tail docker compose logs
	docker compose logs -f

clean: ## Remove build artifacts and caches
	rm -rf backend/.venv backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache
	rm -rf frontend/node_modules frontend/.next
