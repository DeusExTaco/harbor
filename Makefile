# Harbor Container Updater - Development Makefile
# Following Harbor Project Structure from foundational documents

.PHONY: help dev-setup dev-up dev-down dev-logs dev-shell dev-test dev-clean dev-reset

# =============================================================================
# Configuration following project structure
# =============================================================================
DOCKER_COMPOSE_DEV = deploy/docker/docker-compose.dev.yml
DEV_SCRIPTS_DIR = scripts/dev
CONFIG_DIR = config

# =============================================================================
# Help
# =============================================================================
help: ## Show this help message
	@echo "Harbor Development Commands"
	@echo "=============================="
	@echo "Following Harbor Project Structure from foundational documents"
	@echo ""
	@echo "QUICK START:"
	@echo "  make workflow           Show complete development workflow"
	@echo "  make feature name=foo   Create feature/M0-foo branch"
	@echo "  make push-pr           Push changes and create PR"
	@echo ""
	@echo "COMMANDS:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Development URLs:"
	@echo "   Harbor:          http://localhost:8080"
	@echo "   Prometheus:      http://localhost:9090"
	@echo "   Grafana:         http://localhost:3000 (admin/dev_password_123)"
	@echo "   MailHog:         http://localhost:8025"
	@echo "   Test Registry:   http://localhost:5000"

# =============================================================================
# Branch & PR Management (NEW SECTION)
# =============================================================================

workflow: ## Show complete development workflow
	@echo "Harbor Development Workflow"
	@echo "=========================="
	@echo ""
	@echo "1. Create feature branch:"
	@echo "   make feature name=container-discovery"
	@echo ""
	@echo "2. Make changes and commit:"
	@echo "   make commit msg=\"feat: Add container discovery\""
	@echo ""
	@echo "3. Push and create PR:"
	@echo "   make push-pr"
	@echo ""
	@echo "4. Check PR status:"
	@echo "   make pr-status"
	@echo ""
	@echo "5. After approval, merge:"
	@echo "   make pr-merge"
	@echo ""
	@echo "Or use all-in-one:"
	@echo "   make ship msg=\"feat: Add feature\""
	@echo ""
	@echo "Version Info:"
	@echo "   make version        Show current version"
	@echo "   make next-version   Show next version after merge"

feature: ## Create new feature branch (usage: make feature name=my-feature)
	@if [ -z "$(name)" ]; then \
		echo "Error: Please specify name. Usage: make feature name=my-feature"; \
		exit 1; \
	fi
	git checkout develop 2>/dev/null || git checkout -b develop
	git pull origin develop 2>/dev/null || true
	git checkout -b feature/M0-$(name)
	@echo "Created branch: feature/M0-$(name)"
	@echo "Start coding, then run 'make push-pr' when ready"

fix: ## Create new fix branch (usage: make fix name=my-fix)
	@if [ -z "$(name)" ]; then \
		echo "Error: Please specify name. Usage: make fix name=my-fix"; \
		exit 1; \
	fi
	git checkout develop 2>/dev/null || git checkout -b develop
	git pull origin develop 2>/dev/null || true
	git checkout -b fix/$(name)
	@echo "Created branch: fix/$(name)"

branch-status: ## Show current branch and version info
	@echo "Current Branch: $$(git branch --show-current)"
	@echo "Current Version: $$(python -c 'from app import __version__; print(__version__)' 2>/dev/null || echo 'Unknown')"
	@echo "Uncommitted Changes: $$(git status --porcelain | wc -l) files"
	@echo ""
	@echo "Recent Commits:"
	@git log --oneline -5

version: ## Show current version
	@python -c 'from app import __version__, __milestone__; print(f"Version: {__version__} (Milestone: {__milestone__})")' 2>/dev/null || echo "Version files not found"

next-version: ## Show what next version will be
	@CURRENT=$$(python -c 'from app import __version__; print(__version__)' 2>/dev/null || echo "0.1.0-alpha.3"); \
	if [[ $$CURRENT =~ ([0-9]+\.[0-9]+\.[0-9]+)-alpha\.([0-9]+) ]]; then \
		BASE=$${BASH_REMATCH[1]}; \
		ALPHA=$${BASH_REMATCH[2]}; \
		NEXT_ALPHA=$$((ALPHA + 1)); \
		echo "Current: $$CURRENT"; \
		echo "Next: $$BASE-alpha.$$NEXT_ALPHA (on merge to develop)"; \
	else \
		echo "Current: $$CURRENT"; \
	fi

commit: ## Commit changes (usage: make commit msg="your message")
	@if [ -z "$(msg)" ]; then \
		echo "Error: Please specify message. Usage: make commit msg=\"your message\""; \
		exit 1; \
	fi
	git add -A
	git commit -m "$(msg)"
	@echo "Committed with message: $(msg)"

push-pr: ## Push current branch and create PR
	@echo "Pushing changes..."
	git push origin $$(git branch --show-current) 2>/dev/null || git push --set-upstream origin $$(git branch --show-current)
	@echo ""
	@echo "Creating PR..."
	@chmod +x scripts/create-pr.sh 2>/dev/null || true
	@if [ -f scripts/create-pr.sh ]; then \
		./scripts/create-pr.sh; \
	else \
		echo "Note: scripts/create-pr.sh not found. Create it from the artifacts provided."; \
		echo "Or install GitHub CLI and run: gh pr create"; \
	fi

pr: pr-create ## Alias for pr-create

pr-create: ## Create PR from current branch
	@chmod +x scripts/create-pr.sh 2>/dev/null || true
	@if [ -f scripts/create-pr.sh ]; then \
		./scripts/create-pr.sh; \
	else \
		echo "Creating PR manually..."; \
		gh pr create --base develop --fill || echo "Install GitHub CLI: https://cli.github.com/"; \
	fi

pr-status: ## Check PR status for current branch
	@BRANCH=$$(git branch --show-current); \
	PR=$$(gh pr list --head "$$BRANCH" --json number,state,title --jq '.[0]' 2>/dev/null || echo ""); \
	if [ -n "$$PR" ]; then \
		echo "$$PR" | jq -r '"PR #" + (.number|tostring) + ": " + .title + " (" + .state + ")"'; \
		gh pr checks; \
	else \
		echo "No PR found for branch: $$BRANCH"; \
	fi

pr-merge: ## Merge current branch's PR
	@BRANCH=$$(git branch --show-current); \
	PR=$$(gh pr list --head "$$BRANCH" --json number --jq '.[0].number' 2>/dev/null || echo ""); \
	if [ -n "$$PR" ]; then \
		echo "Merging PR #$$PR..."; \
		gh pr merge $$PR --squash; \
		echo "Merged! Switching back to develop..."; \
		git checkout develop; \
		git pull origin develop; \
	else \
		echo "No PR found for branch: $$BRANCH"; \
	fi

ship: ## All-in-one: commit, push, and create PR (usage: make ship msg="your message")
	@if [ -z "$(msg)" ]; then \
		echo "Error: Please specify message. Usage: make ship msg=\"your message\""; \
		exit 1; \
	fi
	git add -A
	git commit -m "$(msg)"
	git push origin $$(git branch --show-current) 2>/dev/null || git push --set-upstream origin $$(git branch --show-current)
	@$(MAKE) pr-create

# =============================================================================
# Development Setup
# =============================================================================
dev-setup: ## Set up development environment following project structure
	@echo "Setting up Harbor development environment..."
	@echo "Following Harbor Project Structure from foundational documents"
	@chmod +x $(DEV_SCRIPTS_DIR)/setup.sh $(DEV_SCRIPTS_DIR)/down.sh $(DEV_SCRIPTS_DIR)/logs.sh 2>/dev/null || true
	@if [ -f $(DEV_SCRIPTS_DIR)/setup.sh ]; then \
		$(DEV_SCRIPTS_DIR)/setup.sh; \
	else \
		echo "Creating basic development structure..."; \
		mkdir -p data logs config; \
	fi
	@echo "Development setup complete!"

# =============================================================================
# Docker Compose Commands (using proper paths)
# =============================================================================
dev-up: ## Start basic development environment
	@echo "Starting Harbor development environment..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml up -d
	@echo "Development environment started!"
	@echo "Harbor available at: http://localhost:8080"

dev-up-full: ## Start full development environment with all services
	@echo "Starting full Harbor development environment..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml --profile postgres --profile monitoring --profile test-containers --profile mail --profile registry up -d
	@echo "Full development environment started!"
	@$(MAKE) dev-status

dev-up-postgres: ## Start development environment with PostgreSQL
	@echo "Starting Harbor development with PostgreSQL..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml --profile postgres up -d
	@echo "Development environment with PostgreSQL started!"

dev-up-monitoring: ## Start development environment with monitoring stack
	@echo "Starting Harbor development with monitoring..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml --profile monitoring up -d
	@echo "Development environment with monitoring started!"

dev-down: ## Stop development environment
	@echo "Stopping Harbor development environment..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml --profile postgres --profile monitoring --profile test-containers --profile mail --profile registry down

dev-restart: ## Restart development environment
	@$(MAKE) dev-down
	@$(MAKE) dev-up

# =============================================================================
# Development Tools
# =============================================================================
dev-logs: ## View Harbor application logs (add SERVICE=name for specific service)
	@if [ -z "$(SERVICE)" ]; then \
		if [ -f $(DEV_SCRIPTS_DIR)/logs.sh ]; then \
			$(DEV_SCRIPTS_DIR)/logs.sh harbor -f; \
		else \
			cd deploy/docker && docker-compose -f docker-compose.dev.yml logs -f harbor; \
		fi; \
	else \
		if [ -f $(DEV_SCRIPTS_DIR)/logs.sh ]; then \
			$(DEV_SCRIPTS_DIR)/logs.sh $(SERVICE) -f; \
		else \
			cd deploy/docker && docker-compose -f docker-compose.dev.yml logs -f $(SERVICE); \
		fi; \
	fi

dev-logs-all: ## View all service logs
	@if [ -f $(DEV_SCRIPTS_DIR)/logs.sh ]; then \
		$(DEV_SCRIPTS_DIR)/logs.sh all -f; \
	else \
		cd deploy/docker && docker-compose -f docker-compose.dev.yml logs -f; \
	fi

dev-shell: ## Get shell access to Harbor development container
	@echo "Connecting to Harbor development container..."
	docker exec -it harbor-dev /bin/bash 2>/dev/null || docker exec -it harbor /bin/bash

dev-shell-root: ## Get root shell access to Harbor development container
	@echo "Connecting to Harbor development container as root..."
	docker exec -it --user root harbor-dev /bin/bash 2>/dev/null || docker exec -it --user root harbor /bin/bash

dev-status: ## Show status of all development services
	@echo "Harbor Development Environment Status"
	@echo "========================================"
	@echo ""
	@echo "Container Status:"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep harbor || echo "No Harbor containers running"
	@echo ""
	@echo "Service URLs:"
	@echo "   Harbor:          http://localhost:8080"
	@echo "   Prometheus:      http://localhost:9090"
	@echo "   Grafana:         http://localhost:3000"
	@echo "   MailHog:         http://localhost:8025"
	@echo "   Test Registry:   http://localhost:5000"
	@echo ""

# =============================================================================
# Testing
# =============================================================================
dev-test: ## Run tests in development environment
	@echo "Running Harbor tests in development environment..."
	docker exec -it harbor-dev python -m pytest tests/ -v 2>/dev/null || docker exec -it harbor python -m pytest tests/ -v

dev-test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	docker exec -it harbor-dev python -m pytest tests/unit/ -v 2>/dev/null || docker exec -it harbor python -m pytest tests/unit/ -v

dev-test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	docker exec -it harbor-dev python -m pytest tests/integration/ -v 2>/dev/null || docker exec -it harbor python -m pytest tests/integration/ -v

dev-test-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	docker exec -it harbor-dev python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing 2>/dev/null || \
	docker exec -it harbor python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# =============================================================================
# Code Quality
# =============================================================================
dev-lint: ## Run linting in development environment
	@echo "Running linting..."
	docker exec -it harbor-dev ruff check app/ tests/ 2>/dev/null || docker exec -it harbor ruff check app/ tests/

dev-format: ## Format code in development environment
	@echo "Formatting code..."
	docker exec -it harbor-dev ruff format app/ tests/ 2>/dev/null || docker exec -it harbor ruff format app/ tests/
	docker exec -it harbor-dev black app/ tests/ 2>/dev/null || docker exec -it harbor black app/ tests/

dev-typecheck: ## Run type checking
	@echo "Running type checking..."
	docker exec -it harbor-dev mypy app/ 2>/dev/null || docker exec -it harbor mypy app/

dev-quality: ## Run all code quality checks
	@$(MAKE) dev-lint
	@$(MAKE) dev-typecheck
	@echo "Code quality checks complete!"

# =============================================================================
# Database Management
# =============================================================================
dev-db-shell: ## Access SQLite database shell
	@echo "Connecting to SQLite database..."
	docker exec -it harbor-dev sqlite3 /app/data/harbor_dev.db 2>/dev/null || docker exec -it harbor sqlite3 /app/data/harbor.db

dev-db-reset: ## Reset development database
	@echo "Resetting development database..."
	docker exec -it harbor-dev rm -f /app/data/harbor_dev.db 2>/dev/null || docker exec -it harbor rm -f /app/data/harbor.db
	@echo "Development database reset!"

dev-db-migrate: ## Run database migrations
	@echo "Running database migrations..."
	docker exec -it harbor-dev python -m alembic upgrade head 2>/dev/null || docker exec -it harbor python -m alembic upgrade head

dev-db-backup: ## Backup development database
	@echo "Backing up development database..."
	docker exec -it harbor-dev cp /app/data/harbor_dev.db /app/data/harbor_dev_backup_$(shell date +%Y%m%d_%H%M%S).db 2>/dev/null || \
	docker exec -it harbor cp /app/data/harbor.db /app/data/harbor_backup_$(shell date +%Y%m%d_%H%M%S).db
	@echo "Database backed up!"

# =============================================================================
# Configuration Management (following project structure)
# =============================================================================
dev-config-edit: ## Edit development configuration
	@echo "Opening development configuration..."
	@${EDITOR:-nano} $(CONFIG_DIR)/development.yaml 2>/dev/null || ${EDITOR:-nano} config/homelab.yaml

dev-config-validate: ## Validate configuration files
	@echo "Validating configuration files..."
	@if command -v yamllint >/dev/null 2>&1; then \
		yamllint $(CONFIG_DIR)/; \
	else \
		echo "Install yamllint for configuration validation: pip install yamllint"; \
	fi

dev-config-show: ## Show current development configuration
	@echo "Current development configuration:"
	@cat $(CONFIG_DIR)/development.yaml 2>/dev/null || cat config/homelab.yaml

# =============================================================================
# Project Structure Utilities
# =============================================================================
dev-structure: ## Show project structure (following foundational documents)
	@echo "Harbor Project Structure (from foundational documents):"
	@echo ""
	@tree -I '__pycache__|*.pyc|node_modules|.git|.pytest_cache' -L 3 . 2>/dev/null || \
	find . -type d -not -path './.git/*' -not -path './__pycache__/*' -not -path './node_modules/*' | head -20

dev-examples: ## Show available example configurations
	@echo "Available example configurations:"
	@echo ""
	@find examples/ -name "*.yml" -o -name "*.yaml" 2>/dev/null | sort || echo "No examples found"

# =============================================================================
# Development Utilities
# =============================================================================
dev-ps: ## Show development containers
	@docker ps --filter "name=harbor" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

dev-volumes: ## Show development volumes
	@echo "Harbor Development Volumes:"
	@docker volume ls | grep harbor

dev-network: ## Show development network info
	@echo "Harbor Development Network:"
	@docker network inspect harbor-dev-network --format '{{json .IPAM.Config}}' 2>/dev/null | jq '.[0]' 2>/dev/null || echo "Network not found"

dev-clean: ## Clean up development containers and images
	@echo "Cleaning up development environment..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml down --rmi local 2>/dev/null || true
	docker system prune -f
	@echo "Development cleanup complete!"

dev-reset: ## Reset entire development environment (removes all data)
	@echo "This will delete ALL development data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo ""; \
		echo "Resetting development environment..."; \
		cd deploy/docker && docker-compose -f docker-compose.dev.yml down -v 2>/dev/null || true; \
		docker system prune -f; \
		echo "Development environment reset!"; \
		echo "Run 'make dev-setup && make dev-up' to start fresh"; \
	else \
		echo ""; \
		echo "Reset cancelled"; \
	fi

# =============================================================================
# Build and Development
# =============================================================================
dev-build: ## Rebuild development Docker image
	@echo "Building Harbor development image..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml build harbor-dev 2>/dev/null || docker-compose -f docker-compose.dev.yml build harbor
	@echo "Development image built!"

dev-build-no-cache: ## Rebuild development image without cache
	@echo "Building Harbor development image (no cache)..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml build --no-cache harbor-dev 2>/dev/null || docker-compose -f docker-compose.dev.yml build --no-cache harbor
	@echo "Development image built!"

dev-pull: ## Pull latest images for development services
	@echo "Pulling latest development service images..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml pull
	@echo "Images updated!"

# =============================================================================
# Debugging
# =============================================================================
dev-debug: ## Start Harbor with debugger enabled
	@echo "Starting Harbor with debugger on port 5678..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml up -d
	@echo "Connect your IDE debugger to localhost:5678"
	@echo "PyCharm: Run > Attach to Process > localhost:5678"

dev-htop: ## Show resource usage in development container
	@echo "Resource usage in Harbor development container:"
	docker exec -it harbor-dev htop 2>/dev/null || docker exec -it harbor htop

dev-inspect: ## Inspect Harbor development container
	@echo "Harbor development container details:"
	docker inspect harbor-dev 2>/dev/null | jq '.[0] | {Name: .Name, State: .State, Config: .Config.Env}' 2>/dev/null || \
	docker inspect harbor 2>/dev/null | jq '.[0] | {Name: .Name, State: .State, Config: .Config.Env}' 2>/dev/null || echo "Container not found"

# =============================================================================
# Docker Registry Testing
# =============================================================================
dev-registry-up: ## Start test registry for testing registry features
	@echo "Starting test registry..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml --profile registry up -d registry-dev
	@echo "Test registry started at http://localhost:5000"

dev-registry-push: ## Push test image to local registry
	@echo "Pushing test image to local registry..."
	docker tag nginx:alpine localhost:5000/test/nginx:latest
	docker push localhost:5000/test/nginx:latest
	@echo "Test image pushed to registry"

dev-registry-list: ## List images in test registry
	@echo "Images in test registry:"
	@curl -s http://localhost:5000/v2/_catalog 2>/dev/null | jq '.repositories' 2>/dev/null || echo "Registry not accessible"

# =============================================================================
# Performance Monitoring
# =============================================================================
dev-metrics: ## View Harbor metrics
	@echo "Harbor development metrics:"
	@curl -s http://localhost:8080/metrics 2>/dev/null | head -20 || echo "Metrics not available"

dev-health: ## Check Harbor health
	@echo "Harbor health status:"
	@curl -s http://localhost:8080/healthz 2>/dev/null | jq '.' || echo "Health endpoint not available"

dev-ready: ## Check Harbor readiness
	@echo "Harbor readiness status:"
	@curl -s http://localhost:8080/readyz 2>/dev/null | jq '.' || echo "Readiness endpoint not available"

# =============================================================================
# Documentation
# =============================================================================
dev-docs: ## Generate and serve development documentation
	@echo "Generating development documentation..."
	@if command -v mkdocs >/dev/null 2>&1; then \
		mkdocs serve -a 0.0.0.0:8000; \
	else \
		echo "Install mkdocs: pip install mkdocs mkdocs-material"; \
	fi

dev-docs-open: ## Open development documentation in browser
	@echo "Opening development documentation..."
	@open docs/development.md 2>/dev/null || xdg-open docs/development.md 2>/dev/null || echo "Please open docs/development.md manually"

# =============================================================================
# Production Commands
# =============================================================================
prod-up: ## Start production environment (home lab)
	@echo "Starting Harbor production environment..."
	@cd deploy/docker && docker-compose -f docker-compose.yml up -d
	@echo "Harbor production started at http://localhost:8080"

prod-up-secure: ## Start secure production environment with socket proxy
	@echo "Starting secure Harbor production..."
	@cd deploy/docker && docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "Secure Harbor production started (localhost only)"

prod-down: ## Stop production environment
	@cd deploy/docker && docker-compose -f docker-compose.yml down

prod-logs: ## View production logs
	@cd deploy/docker && docker-compose -f docker-compose.yml logs -f harbor

prod-build: ## Build production image
	@cd deploy/docker && docker-compose -f docker-compose.yml build

# =============================================================================
# Example Management (following project structure)
# =============================================================================
dev-example-basic: ## Start basic home lab example
	@echo "Starting basic home lab example..."
	@cd examples/home-lab/basic && docker-compose up -d

dev-example-monitoring: ## Start home lab with monitoring example
	@echo "Starting home lab with monitoring example..."
	@cd examples/home-lab/with-monitoring && docker-compose up -d

dev-example-down: ## Stop all example deployments
	@echo "Stopping example deployments..."
	@cd examples/home-lab/basic && docker-compose down 2>/dev/null || true
	@cd examples/home-lab/with-monitoring && docker-compose down 2>/dev/null || true

# =============================================================================
# Quick Development Workflows
# =============================================================================
dev-quick: dev-setup dev-up ## Quick setup and start development environment

dev-full: dev-setup dev-up-full ## Setup and start full development environment with all services

dev-test-all: dev-test dev-lint dev-typecheck ## Run all tests and quality checks

dev-fresh: dev-down dev-build dev-up ## Fresh rebuild and restart

# =============================================================================
# Release Management (keeping your existing commands)
# =============================================================================
release-status: ## Show current release status and version information
	@echo "Harbor Release Status"
	@echo "======================="
	@echo ""
	@if [ -f scripts/release/release.sh ]; then \
		scripts/release/release.sh status; \
	else \
		$(MAKE) version; \
	fi

release-versions: ## Show suggested next version numbers
	@echo "Harbor Version Suggestions"
	@echo "============================"
	@if [ -f scripts/release/release.sh ]; then \
		scripts/release/release.sh versions; \
	else \
		$(MAKE) next-version; \
	fi

release-prepare: ## Prepare release branch with version updates (Usage: make release-prepare VERSION=0.1.1)
	@if [ -z "$(VERSION)" ]; then \
		echo "VERSION parameter required"; \
		echo "Usage: make release-prepare VERSION=0.1.1"; \
		exit 1; \
	fi
	@echo "Preparing Harbor release $(VERSION)..."
	@if [ -f scripts/release/release.sh ]; then \
		scripts/release/release.sh prepare $(VERSION); \
	else \
		echo "Release script not found. Manual process:"; \
		echo "1. Update version in app/__init__.py"; \
		echo "2. Update version in pyproject.toml"; \
		echo "3. Update CHANGELOG.md"; \
		echo "4. Create release branch"; \
	fi

release-tag: ## Create and push release tag (Usage: make release-tag VERSION=0.1.1)
	@if [ -z "$(VERSION)" ]; then \
		echo "VERSION parameter required"; \
		echo "Usage: make release-tag VERSION=0.1.1"; \
		exit 1; \
	fi
	@echo "Creating Harbor release tag v$(VERSION)..."
	git tag v$(VERSION)
	git push origin v$(VERSION)

# =============================================================================
# Default target
# =============================================================================
.DEFAULT_GOAL := help
