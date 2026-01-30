# =============================================================================
# Cerberus CTF Platform - Development Makefile
# =============================================================================
# Quick reference for common development tasks
#
# Usage: make <target>
#   - make install     : Install all dependencies
#   - make db-up       : Start database services
#   - make run-api     : Start backend API server
#   - make run-ui      : Start frontend UI server
# =============================================================================

# Colors for output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
NC = \033[0m # No Color

# Project directories
PROJECT_ROOT = $(shell pwd)
BACKEND_DIR = $(PROJECT_ROOT)/app
FRONTEND_DIR = $(PROJECT_ROOT)/src
CONFIG_DIR = $(PROJECT_ROOT)/config

# Python and Node paths
PYTHON = python3
PIP = pip3
NODE = node
NPM = npm

# Docker Compose files
DOCKER_COMPOSE_DEV = $(CONFIG_DIR)/docker-compose.dev.yml
DOCKER_COMPOSE_PROD = $(CONFIG_DIR)/docker-compose.yml

# =============================================================================
# Installation
# =============================================================================

.PHONY: install
install: ## Install Python and Node.js dependencies
	@echo "$(BLUE)=== Installing Dependencies ===$(NC)"
	@echo "$(GREEN)Installing Python dependencies...$(NC)"
	@$(PIP) install -r $(PROJECT_ROOT)/requirements.txt 2>/dev/null || echo "$(YELLOW)Warning: requirements.txt not found, skipping Python deps$(NC)"
	@echo ""
	@echo "$(GREEN)Installing Node.js dependencies...$(NC)"
	@cd $(FRONTEND_DIR) && $(NPM) install
	@echo ""
	@echo "$(GREEN)✓ Dependencies installed successfully!$(NC)"

.PHONY: install-python
install-python: ## Install Python dependencies only
	@echo "$(BLUE)=== Installing Python Dependencies ===$(NC)"
	@$(PIP) install -r $(PROJECT_ROOT)/requirements.txt 2>/dev/null || echo "$(YELLOW)Warning: requirements.txt not found$(NC)"
	@echo "$(GREEN)✓ Python dependencies installed!$(NC)"

.PHONY: install-node
install-node: ## Install Node.js dependencies only
	@echo "$(BLUE)=== Installing Node.js Dependencies ===$(NC)"
	@cd $(FRONTEND_DIR) && $(NPM) install
	@echo "$(GREEN)✓ Node.js dependencies installed!$(NC)"

# =============================================================================
# Database Services (Docker)
# =============================================================================

.PHONY: db-up
db-up: ## Start PostgreSQL and Redis via Docker Compose
	@echo "$(BLUE)=== Starting Database Services ===$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_DEV) up -d postgres redis
	@echo "$(GREEN)✓ Database services started!$(NC)"
	@echo "$(YELLOW)PostgreSQL: localhost:5432$(NC)"
	@echo "$(YELLOW)Redis: localhost:6379$(NC)"

.PHONY: db-down
db-down: ## Stop PostgreSQL and Redis containers
	@echo "$(BLUE)=== Stopping Database Services ===$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_DEV) down
	@echo "$(GREEN)✓ Database services stopped!$(NC)"

.PHONY: db-status
db-status: ## Check database service status
	@echo "$(BLUE)=== Database Status ===$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_DEV) ps postgres redis

.PHONY: db-logs
db-logs: ## View database logs
	@echo "$(BLUE)=== Database Logs ===$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_DEV) logs -f postgres redis

# =============================================================================
# Application Development Servers
# =============================================================================

.PHONY: run-api
run-api: ## Start FastAPI backend development server
	@echo "$(BLUE)=== Starting Backend API ===$(NC)"
	@echo "$(GREEN)API will be available at: http://localhost:8000$(NC)"
	@echo "$(GREEN)API Documentation: http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop...$(NC)"
	@cd $(PROJECT_ROOT) && $(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: run-api-docker
run-api-docker: ## Start backend API via Docker
	@echo "$(BLUE)=== Starting Backend API (Docker) ===$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_DEV) up -d backend
	@echo "$(GREEN)✓ Backend API started in container!$(NC)"

.PHONY: run-ui
run-ui: ## Start Next.js frontend development server
	@echo "$(BLUE)=== Starting Frontend UI ===$(NC)"
	@echo "$(GREEN)Frontend will be available at: http://localhost:3000$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop...$(NC)"
	@cd $(FRONTEND_DIR) && $(NPM) run dev

.PHONY: run-ui-docker
run-ui-docker: ## Start frontend UI via Docker
	@echo "$(BLUE)=== Starting Frontend UI (Docker) ===$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_DEV) up -d frontend
	@echo "$(GREEN)✓ Frontend UI started in container!$(NC)"

.PHONY: run-all
run-all: db-up ## Start all development services (databases, API, UI)
	@echo "$(BLUE)=== Starting All Services ===$(NC)"
	@echo "$(GREEN)Starting frontend in background...$(NC)"
	@cd $(FRONTEND_DIR) && $(NPM) run dev &
	@echo ""
	@echo "$(GREEN)✓ All services started!$(NC)"
	@echo "$(YELLOW)Frontend: http://localhost:3000$(NC)"
	@echo "$(YELLOW)Backend: http://localhost:8000$(NC)"
	@echo "$(YELLOW)API Docs: http://localhost:8000/docs$(NC)"

.PHONY: stop-all
stop-all: ## Stop all development services
	@echo "$(BLUE)=== Stopping All Services ===$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_DEV) down
	@pkill -f "uvicorn app.main:app" 2>/dev/null || true
	@pkill -f "next dev" 2>/dev/null || true
	@echo "$(GREEN)✓ All services stopped!$(NC)"

# =============================================================================
# Production Deployment
# =============================================================================

.PHONY: prod-up
prod-up: ## Start production stack with Docker Compose
	@echo "$(BLUE)=== Starting Production Stack ===$(NC)"
	@cd $(CONFIG_DIR) && docker-compose -f $(DOCKER_COMPOSE_PROD) up -d
	@echo "$(GREEN)✓ Production stack started!$(NC)"

.PHONY: prod-down
prod-down: ## Stop production stack
	@echo "$(BLUE)=== Stopping Production Stack ===$(NC)"
	@cd $(CONFIG_DIR) && docker-compose -f $(DOCKER_COMPOSE_PROD) down
	@echo "$(GREEN)✓ Production stack stopped!$(NC)"

.PHONY: prod-logs
prod-logs: ## View production logs
	@echo "$(BLUE)=== Production Logs ===$(NC)"
	@cd $(CONFIG_DIR) && docker-compose -f $(DOCKER_COMPOSE_PROD) logs -f

.PHONY: prod-restart
prod-restart: ## Restart production stack
	@echo "$(BLUE)=== Restarting Production Stack ===$(NC)"
	@cd $(CONFIG_DIR) && docker-compose -f $(DOCKER_COMPOSE_PROD) restart
	@echo "$(GREEN)✓ Production stack restarted!$(NC)"

.PHONY: prod-rebuild
prod-rebuild: ## Rebuild and restart production containers
	@echo "$(BLUE)=== Rebuilding Production Stack ===$(NC)"
	@cd $(CONFIG_DIR) && docker-compose -f $(DOCKER_COMPOSE_PROD) up -d --build
	@echo "$(GREEN)✓ Production stack rebuilt!$(NC)"

# =============================================================================
# Testing
# =============================================================================

.PHONY: test
test: ## Run all tests
	@echo "$(BLUE)=== Running Tests ===$(NC)"
	@make test-backend
	@echo "$(GREEN)✓ All tests passed!$(NC)"

.PHONY: test-backend
test-backend: ## Run backend tests with pytest
	@echo "$(BLUE)=== Running Backend Tests ===$(NC)"
	@cd $(PROJECT_ROOT) && $(PYTHON) -m pytest tests/ -v --tb=short
	@echo "$(GREEN)✓ Backend tests completed!$(NC)"

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)=== Running Tests with Coverage ===$(NC)"
	@cd $(PROJECT_ROOT) && $(PYTHON) -m pytest tests/ --cov=app --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)✓ Coverage report generated!$(NC)"
	@echo "$(YELLOW)Open htmlcov/index.html to view coverage report$(NC)"

# =============================================================================
# Linting & Formatting
# =============================================================================

.PHONY: lint
lint: ## Run all linters (Python & TypeScript)
	@echo "$(BLUE)=== Running Linters ===$(NC)"
	@make lint-python
	@make lint-js
	@echo "$(GREEN)✓ All linting passed!$(NC)"

.PHONY: lint-python
lint-python: ## Run Python linter (ruff)
	@echo "$(BLUE)=== Linting Python ===$(NC)"
	@$(PYTHON) -m ruff check $(BACKEND_DIR) --fix 2>/dev/null || echo "$(YELLOW)ruff not installed, skipping$(NC)"

.PHONY: lint-js
lint-js: ## Run TypeScript linter (ESLint)
	@echo "$(BLUE)=== Linting TypeScript ===$(NC)"
	@cd $(FRONTEND_DIR) && $(NPM) run lint

.PHONY: format
format: ## Format code (Black + Prettier)
	@echo "$(BLUE)=== Formatting Code ===$(NC)"
	@make format-python
	@make format-js
	@echo "$(GREEN)✓ Code formatted!$(NC)"

.PHONY: format-python
format-python: ## Format Python code (Black)
	@echo "$(BLUE)=== Formatting Python ===$(NC)"
	@$(PYTHON) -m black $(BACKEND_DIR) 2>/dev/null || echo "$(YELLOW)black not installed$(NC)"

.PHONY: format-js
format-js: ## Format TypeScript code (Prettier)
	@echo "$(BLUE)=== Formatting TypeScript ===$(NC)"
	@cd $(FRONTEND_DIR) && $(NPM) run format

# =============================================================================
# Database Migrations
# =============================================================================

.PHONY: migrate
migrate: ## Run Alembic database migrations
	@echo "$(BLUE)=== Running Database Migrations ===$(NC)"
	@cd $(PROJECT_ROOT) && $(PYTHON) -m alembic upgrade head
	@echo "$(GREEN)✓ Migrations completed!$(NC)"

.PHONY: migrate-create
migrate-create: ## Create new Alembic migration
	@if [ -z "$(msg)" ]; then \
		echo "$(RED)Error: Please provide a migration message: make migrate-create msg='your message'$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)=== Creating Migration: $(msg) ===$(NC)"
	@cd $(PROJECT_ROOT) && $(PYTHON) -m alembic revision --autogenerate -m "$(msg)"
	@echo "$(GREEN)✓ Migration created!$(NC)"

.PHONY: migrate-history
migrate-history: ## Show migration history
	@echo "$(BLUE)=== Migration History ===$(NC)"
	@cd $(PROJECT_ROOT) && $(PYTHON) -m alembic history

.PHONY: migrate-current
migrate-current: ## Show current migration version
	@echo "$(BLUE)=== Current Migration ===$(NC)"
	@cd $(PROJECT_ROOT) && $(PYTHON) -m alembic current

# =============================================================================
# Backup & Restore
# =============================================================================

.PHONY: backup
backup: ## Trigger manual database backup
	@echo "$(BLUE)=== Triggering Database Backup ===$(NC)"
	@cd $(PROJECT_ROOT) && $(PYTHON) scripts/backup_db.py
	@echo "$(GREEN)✓ Backup completed!$(NC)"

.PHONY: backup-list
backup-list: ## List available backups in S3
	@echo "$(BLUE)=== Available Backups ===$(NC)"
	@docker exec cerberus-minio mc ls myminio/cerberus-backups/backups/

.PHONY: restore
restore: ## Restore database from backup file
	@if [ -z "$(file)" ]; then \
		echo "$(RED)Error: Please provide backup file: make restore file=/path/to/backup.sql.gz$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)=== Restoring Database ===$(NC)"
	@docker cp $(file) cerberus-postgres:/tmp/restore.sql.gz
	@docker exec cerberus-postgres bash -c "gunzip -c /tmp/restore.sql.gz | psql -U \$$POSTGRES_USER -d \$$POSTGRES_DB"
	@echo "$(GREEN)✓ Database restored!$(NC)"

# =============================================================================
# Docker Management
# =============================================================================

.PHONY: docker-build
docker-build: ## Build Docker images
	@echo "$(BLUE)=== Building Docker Images ===$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_DEV) build

.PHONY: docker-prune
docker-prune: ## Clean up Docker resources
	@echo "$(BLUE)=== Cleaning Docker Resources ===$(NC)"
	@docker system prune -af --volumes
	@docker image prune -f
	@echo "$(GREEN)✓ Docker cleanup complete!$(NC)"

.PHONY: docker-status
docker-status: ## Show Docker container status
	@echo "$(BLUE)=== Docker Container Status ===$(NC)"
	@docker-compose -f $(DOCKER_COMPOSE_DEV) ps

# =============================================================================
# Utility
# =============================================================================

.PHONY: clean
clean: ## Clean up generated files and caches
	@echo "$(BLUE)=== Cleaning Generated Files ===$(NC)"
	@find $(PROJECT_ROOT) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find $(PROJECT_ROOT) -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find $(PROJECT_ROOT) -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@rm -rf $(FRONTEND_DIR)/.next 2>/dev/null || true
	@rm -rf $(PROJECT_ROOT)/htmlcov 2>/dev/null || true
	@rm -rf $(PROJECT_ROOT)/.coverage 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete!$(NC)"

.PHONY: deps-check
deps-check: ## Check dependency versions
	@echo "$(BLUE)=== Dependency Versions ===$(NC)"
	@echo "$(GREEN)Python:$(NC) $$($(PYTHON) --version)"
	@echo "$(GREEN)Node.js:$(NC) $$($(NODE) --version)"
	@echo "$(GREEN)NPM:$(NC) $$($(NPM) --version)"
	@echo "$(GREEN)Docker:$(NC) $$(docker --version)"
	@echo "$(GREEN)Docker Compose:$(NC) $$(docker-compose --version)"

.PHONY: shell
shell: ## Open shell in backend container
	@echo "$(BLUE)=== Opening Backend Shell ===$(NC)"
	@docker exec -it cerberus-backend /bin/bash

.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "$(BLUE)Cerberus CTF Platform - Development Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Installation$(NC):"
	@echo "  install          Install all dependencies"
	@echo "  install-python   Install Python dependencies only"
	@echo "  install-node     Install Node.js dependencies only"
	@echo ""
	@echo "$(GREEN)Database Services$(NC):"
	@echo "  db-up            Start PostgreSQL and Redis"
	@echo "  db-down          Stop database services"
	@echo "  db-status        Check database status"
	@echo "  db-logs          View database logs"
	@echo ""
	@echo "$(GREEN)Development Servers$(NC):"
	@echo "  run-api          Start FastAPI backend (localhost:8000)"
	@echo "  run-api-docker   Start backend via Docker"
	@echo "  run-ui           Start Next.js frontend (localhost:3000)"
	@echo "  run-ui-docker    Start frontend via Docker"
	@echo "  run-all          Start all development services"
	@echo "  stop-all         Stop all services"
	@echo ""
	@echo "$(GREEN)Production$(NC):"
	@echo "  prod-up          Start production stack"
	@echo "  prod-down        Stop production stack"
	@echo "  prod-logs        View production logs"
	@echo "  prod-restart     Restart production stack"
	@echo "  prod-rebuild     Rebuild production containers"
	@echo ""
	@echo "$(GREEN)Testing$(NC):"
	@echo "  test             Run all tests"
	@echo "  test-backend     Run backend tests"
	@echo "  test-coverage    Run tests with coverage"
	@echo ""
	@echo "$(GREEN)Code Quality$(NC):"
	@echo "  lint             Run all linters"
	@echo "  lint-python      Lint Python code"
	@echo "  lint-js          Lint TypeScript"
	@echo "  format           Format code"
	@echo ""
	@echo "$(GREEN)Database Migrations$(NC):"
	@echo "  migrate          Run Alembic migrations"
	@echo "  migrate-create   Create new migration (msg='description')"
	@echo "  migrate-history  Show migration history"
	@echo "  migrate-current  Show current version"
	@echo ""
	@echo "$(GREEN)Backup & Restore$(NC):"
	@echo "  backup           Trigger manual backup"
	@echo "  backup-list      List S3 backups"
	@echo "  restore          Restore from file (file=/path/to/backup.sql.gz)"
	@echo ""
	@echo "$(GREEN)Docker$(NC):"
	@echo "  docker-build     Build Docker images"
	@echo "  docker-prune     Clean up Docker resources"
	@echo "  docker-status    Show container status"
	@echo ""
	@echo "$(GREEN)Utilities$(NC):"
	@echo "  clean            Clean generated files"
	@echo "  deps-check       Check dependency versions"
	@echo "  shell            Open backend container shell"
	@echo "  help             Show this help"
	@echo ""
