# Harbor Container Updater - Development Makefile
# Provides common development tasks for the Harbor project

.PHONY: help install dev test test-cov lint format clean docker-build docker-run

# Default target
help: ## Show this help message
	@echo 'Harbor Container Updater - Development Commands'
	@echo ''
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Setup Commands:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# =============================================================================
# Installation and Setup
# =============================================================================

install: ## Install production dependencies only
	pip install --upgrade pip
	pip install -e .

dev: ## Install development dependencies and setup dev environment
	pip install --upgrade pip
	pip install -e ".[dev]"
	pre-commit install

dev-full: ## Complete development setup including all optional dependencies
	pip install --upgrade pip
	pip install -e ".[dev,prod,test]"
	pre-commit install
	playwright install  # Install browser binaries for e2e tests

# =============================================================================
# Code Quality and Testing
# =============================================================================

test: ## Run unit and integration tests
	pytest tests/ -v

test-unit: ## Run only unit tests
	pytest tests/unit/ -v

test-integration: ## Run only integration tests
	pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests
	pytest tests/e2e/ -v

test-cov: ## Run tests with coverage report
	pytest --cov=app --cov-report=html --cov-report=term-missing

test-cov-xml: ## Run tests with XML coverage report (for CI)
	pytest --cov=app --cov-report=xml

test-performance: ## Run performance tests
	pytest tests/performance/ -v

test-security: ## Run security tests
	pytest tests/security/ -v

test-all: ## Run all test suites
	pytest tests/ -v --cov=app --cov-report=html

# =============================================================================
# Code Quality Tools
# =============================================================================

lint: ## Run all linting checks
	@echo "Running ruff linter..."
	ruff check app/ tests/
	@echo "Running mypy type checker..."
	mypy app/ tests/
	@echo "Linting complete!"

lint-fix: ## Run linting with automatic fixes
	@echo "Running ruff with automatic fixes..."
	ruff check --fix app/ tests/
	@echo "Running ruff formatter..."
	ruff format app/ tests/
	@echo "Linting and formatting complete!"

format: ## Format code with ruff
	@echo "Formatting code with ruff..."
	ruff format app/ tests/
	@echo "Organizing imports with ruff..."
	ruff check --fix app/ tests/
	@echo "Code formatting complete!"

typecheck: ## Run type checking with mypy
	mypy app/ tests/

pre-commit: ## Run all pre-commit hooks
	pre-commit run --all-files

# =============================================================================
# Development Server
# =============================================================================

run: ## Run Harbor development server
	python app/main.py

run-reload: ## Run development server with auto-reload
	uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8080

run-debug: ## Run development server with debug logging
	HARBOR_MODE=development LOG_LEVEL=DEBUG python app/main.py

# =============================================================================
# Database Operations
# =============================================================================

db-upgrade: ## Run database migrations (upgrade to latest)
	alembic upgrade head

db-downgrade: ## Downgrade database by one revision
	alembic downgrade -1

db-revision: ## Create new database revision
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

db-reset: ## Reset database (WARNING: destroys all data)
	@echo "WARNING: This will destroy all database data!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	rm -f data/harbor.db*
	alembic upgrade head

# =============================================================================
# Docker Development
# =============================================================================

docker-build: ## Build development Docker image
	docker build -t harbor:dev \
		--build-arg DEBIAN_FRONTEND=noninteractive \
		--build-arg PIP_DISABLE_PIP_VERSION_CHECK=1 \
		--build-arg PYTHONDONTWRITEBYTECODE=1 \
		-f deploy/docker/Dockerfile.dev .

docker-build-prod: ## Build production Docker image
	docker build -t harbor:latest \
		--build-arg DEBIAN_FRONTEND=noninteractive \
		--build-arg PIP_DISABLE_PIP_VERSION_CHECK=1 \
		--build-arg PYTHONDONTWRITEBYTECODE=1 \
		-f deploy/docker/Dockerfile .


docker-build-multi: ## Build multi-architecture images locally
	./scripts/build.sh

docker-run: ## Run Harbor in Docker container
	docker run -d --name harbor-dev \
		-p 8080:8080 \
		-v /var/run/docker.sock:/var/run/docker.sock:ro \
		-v $$(pwd)/data:/app/data \
		harbor:dev

docker-run-prod: ## Run production Harbor container
	docker run -d --name harbor-prod \
		-p 8080:8080 \
		-v /var/run/docker.sock:/var/run/docker.sock:ro \
		-v harbor-data:/app/data \
		harbor:latest

docker-stop: ## Stop and remove development container
	docker stop harbor-dev || true
	docker rm harbor-dev || true

docker-stop-prod: ## Stop and remove production container
	docker stop harbor-prod || true
	docker rm harbor-prod || true

docker-logs: ## Show Docker container logs
	docker logs -f harbor-dev

docker-logs-prod: ## Show production container logs
	docker logs -f harbor-prod

docker-shell: ## Open shell in running container
	docker exec -it harbor-dev /bin/bash

docker-shell-prod: ## Open shell in production container
	docker exec -it harbor-prod /bin/bash

docker-health: ## Check Docker container health status
	@echo "Checking Harbor container health..."
	@docker inspect harbor-dev --format='{{.State.Health.Status}}' 2>/dev/null || echo "Container not running"
	@docker exec harbor-dev curl -f http://localhost:8080/healthz 2>/dev/null && echo "✅ Health check passed" || echo "❌ Health check failed"

docker-health-prod: ## Check production container health
	@echo "Checking Harbor production container health..."
	@docker inspect harbor-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "Container not running"
	@docker exec harbor-prod curl -f http://localhost:8080/healthz 2>/dev/null && echo "✅ Health check passed" || echo "❌ Health check failed"

docker-compose-dev: ## Start development environment with Docker Compose
	docker-compose -f deploy/docker/docker-compose.dev.yml up -d

docker-compose-logs: ## Show Docker Compose logs
	docker-compose -f deploy/docker/docker-compose.dev.yml logs -f

docker-compose-down: ## Stop Docker Compose environment
	docker-compose -f deploy/docker/docker-compose.dev.yml down

# =============================================================================
# Project Maintenance
# =============================================================================

clean: ## Clean build artifacts and temporary files
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete!"

docker-clean: ## Clean Docker images and containers
	docker system prune -f
	docker image prune -f

deps-update: ## Update all dependencies to latest versions
	pip install --upgrade pip
	pip install --upgrade -e ".[dev,prod,test]"

deps-check: ## Check for dependency vulnerabilities
	pip-audit

# =============================================================================
# Documentation
# =============================================================================

docs-serve: ## Serve documentation locally (when implemented)
	@echo "Documentation server not yet implemented (M4 milestone)"

docs-build: ## Build documentation (when implemented)
	@echo "Documentation build not yet implemented (M4 milestone)"

# =============================================================================
# Release Management
# =============================================================================

version: ## Show current version
	@python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"

version-bump-patch: ## Bump patch version (0.1.0 -> 0.1.1)
	@echo "Version bump not yet implemented - manual edit pyproject.toml"

version-bump-minor: ## Bump minor version (0.1.0 -> 0.2.0)
	@echo "Version bump not yet implemented - manual edit pyproject.toml"

# =============================================================================
# Utility Commands
# =============================================================================

env-info: ## Show development environment information
	@echo "Harbor Development Environment"
	@echo "=============================="
	@echo "Python version: $$(python --version)"
	@echo "Pip version: $$(pip --version)"
	@echo "Virtual environment: $$VIRTUAL_ENV"
	@echo "Harbor package: $$(pip show harbor | grep Location || echo 'Not installed')"
	@echo ""
	@echo "Installed development tools:"
	@echo "- pytest: $$(pytest --version | head -1 || echo 'Not installed')"
	@echo "- ruff: $$(ruff --version || echo 'Not installed')"
	@echo "- mypy: $$(mypy --version || echo 'Not installed')"

check: ## Run all quality checks (lint, type check, test)
	@echo "Running complete quality check..."
	make lint
	make test
	@echo "✅ All quality checks passed!"

# =============================================================================
# Git Helpers
# =============================================================================

git-setup: ## Setup git hooks and configuration
	pre-commit install
	git config core.autocrlf false
	git config pull.rebase true

# For macOS users specifically
setup-mac: ## macOS-specific setup
	@echo "Setting up Harbor development on macOS..."
	brew install --quiet docker docker-compose || echo "Docker already installed"
	make dev
	@echo "✅ macOS setup complete!"
