# Makefile for AI Productivity App
.PHONY: help install dev up down logs test clean lint format check

# Default target
.DEFAULT_GOAL := help

# Colors for output
YELLOW := \033[1;33m
GREEN := \033[1;32m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)AI Productivity App - Make Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'

install: ## Install all dependencies
	@echo "$(GREEN)Installing backend dependencies...$(NC)"
	cd backend && pip install -r requirements.txt
	@echo "$(GREEN)Installing frontend dependencies...$(NC)"
	cd frontend && npm install

dev: ## Start development environment with Docker
	@echo "$(GREEN)Starting development environment...$(NC)"
	docker compose up --build

up: ## Start containers in background
	@echo "$(GREEN)Starting containers...$(NC)"
	docker compose up -d

down: ## Stop all containers
	@echo "$(GREEN)Stopping containers...$(NC)"
	docker compose down

logs: ## View container logs
	docker compose logs -f

test: ## Run all tests
	@echo "$(GREEN)Running backend tests...$(NC)"
	cd backend && python3 -m pytest -v --cov=app --cov-report=term-missing
	@echo "$(GREEN)Running frontend tests...$(NC)"
	cd frontend && npm test

clean: ## Clean up all generated files and containers
	@echo "$(GREEN)Cleaning up...$(NC)"
	docker compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf backend/.coverage
	rm -rf backend/htmlcov
	rm -rf frontend/node_modules
	rm -rf frontend/dist
	rm -rf data/*.db

lint: ## Run linters
	@echo "$(GREEN)Linting backend...$(NC)"
	cd backend && flake8 app --ignore=E501
	cd backend && mypy app --ignore-missing-imports
	@echo "$(GREEN)Linting frontend...$(NC)"
	cd frontend && npm run lint

format: ## Format code
	@echo "$(GREEN)Formatting backend...$(NC)"
	cd backend && black app tests
	@echo "$(GREEN)Formatting frontend...$(NC)"
	cd frontend && npx prettier --write "src/**/*.{js,jsx,css}"

check: ## Run pre-commit checks
	@make lint
	@make test

# Development database commands
db-reset: ## Reset the database
	@echo "$(GREEN)Resetting database...$(NC)"
	rm -f data/app.db
	docker compose exec backend python3 -c "from app.database import init_db; init_db()"

db-shell: ## Open database shell
	@echo "$(GREEN)Opening database shell...$(NC)"
	sqlite3 data/app.db

# Model management commands
models-update: ## Update AI models with latest offerings
	@echo "$(GREEN)Updating AI models...$(NC)"
	@if docker compose ps | grep -q backend; then \
		docker compose exec backend python3 -m app.cli.update_models; \
	else \
		echo "$(YELLOW)Docker not running, trying local environment...$(NC)"; \
		cd backend && python3 -m app.cli.update_models; \
	fi

models-seed: ## Seed database with AI models (one-time setup)
	@echo "$(GREEN)Seeding AI models...$(NC)"
	@if docker compose ps | grep -q backend; then \
		docker compose exec backend python3 -m app.cli.seed_models; \
	else \
		echo "$(YELLOW)Docker not running, trying local environment...$(NC)"; \
		cd backend && python3 -m app.cli.seed_models; \
	fi

# Docker commands
build: ## Build Docker images
	@echo "$(GREEN)Building Docker images...$(NC)"
	docker compose build

shell-backend: ## Open shell in backend container
	docker compose exec backend /bin/bash

shell-frontend: ## Open shell in frontend container
	docker compose exec frontend /bin/sh

# Monitoring
status: ## Check status of all services
	@echo "$(GREEN)Checking service status...$(NC)"
	@curl -s http://localhost:8000/health/ready | python3 -m json.tool || echo "Backend not responding"
	@echo ""
	@curl -s http://localhost:5173 > /dev/null && echo "Frontend: ✅ Running" || echo "Frontend: ❌ Not running"
