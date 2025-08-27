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
	@echo "🛳️ Harbor Development Commands"
	@echo "=============================="
	@echo "Following Harbor Project Structure from foundational documents"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🌐 Development URLs:"
	@echo "   Harbor:          http://localhost:8080"
	@echo "   Prometheus:      http://localhost:9090"
	@echo "   Grafana:         http://localhost:3000 (admin/dev_password_123)"
	@echo "   MailHog:         http://localhost:8025"
	@echo "   Test Registry:   http://localhost:5000"

# =============================================================================
# Development Setup
# =============================================================================
dev-setup: ## Set up development environment following project structure
	@echo "🛳️ Setting up Harbor development environment..."
	@echo "Following Harbor Project Structure from foundational documents"
	@chmod +x $(DEV_SCRIPTS_DIR)/setup.sh $(DEV_SCRIPTS_DIR)/down.sh $(DEV_SCRIPTS_DIR)/logs.sh
	@$(DEV_SCRIPTS_DIR)/setup.sh
	@echo "✅ Development setup complete!"

# =============================================================================
# Docker Compose Commands (using proper paths)
# =============================================================================
dev-up: ## Start basic development environment
	@echo "🚀 Starting Harbor development environment..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml up -d
	@echo "✅ Development environment started!"
	@echo "🌐 Harbor available at: http://localhost:8080"

dev-up-full: ## Start full development environment with all services
	@echo "🚀 Starting full Harbor development environment..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml --profile postgres --profile monitoring --profile test-containers --profile mail --profile registry up -d
	@echo "✅ Full development environment started!"
	@$(MAKE) dev-status

dev-up-postgres: ## Start development environment with PostgreSQL
	@echo "🚀 Starting Harbor development with PostgreSQL..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml --profile postgres up -d
	@echo "✅ Development environment with PostgreSQL started!"

dev-up-monitoring: ## Start development environment with monitoring stack
	@echo "🚀 Starting Harbor development with monitoring..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml --profile monitoring up -d
	@echo "✅ Development environment with monitoring started!"

dev-down: ## Stop development environment
	@echo "🛑 Stopping Harbor development environment..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml --profile postgres --profile monitoring --profile test-containers --profile mail --profile registry down

dev-restart: ## Restart development environment
	@$(MAKE) dev-down
	@$(MAKE) dev-up

# =============================================================================
# Development Tools
# =============================================================================
dev-logs: ## View Harbor application logs (add SERVICE=name for specific service)
	@if [ -z "$(SERVICE)" ]; then \
		$(DEV_SCRIPTS_DIR)/logs.sh harbor -f; \
	else \
		$(DEV_SCRIPTS_DIR)/logs.sh $(SERVICE) -f; \
	fi

dev-logs-all: ## View all service logs
	@$(DEV_SCRIPTS_DIR)/logs.sh all -f

dev-shell: ## Get shell access to Harbor development container
	@echo "🐚 Connecting to Harbor development container..."
	docker exec -it harbor-dev /bin/bash

dev-shell-root: ## Get root shell access to Harbor development container
	@echo "🐚 Connecting to Harbor development container as root..."
	docker exec -it --user root harbor-dev /bin/bash

dev-status: ## Show status of all development services
	@echo "📊 Harbor Development Environment Status"
	@echo "========================================"
	@echo ""
	@echo "🐳 Container Status:"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep harbor- || echo "No Harbor containers running"
	@echo ""
	@echo "🌐 Service URLs:"
	@echo "   Harbor:          http://localhost:8080"
	@echo "   Prometheus:      http://localhost:9090"
	@echo "   Grafana:         http://localhost:3000"
	@echo "   MailHog:         http://localhost:8025"
	@echo "   Test Registry:   http://localhost:5000"
	@echo "   Test Nginx:      http://localhost:8081"
	@echo ""

# =============================================================================
# Testing
# =============================================================================
dev-test: ## Run tests in development environment
	@echo "🧪 Running Harbor tests in development environment..."
	docker exec -it harbor-dev python -m pytest tests/ -v

dev-test-unit: ## Run unit tests only
	@echo "🧪 Running unit tests..."
	docker exec -it harbor-dev python -m pytest tests/unit/ -v

dev-test-integration: ## Run integration tests only
	@echo "🧪 Running integration tests..."
	docker exec -it harbor-dev python -m pytest tests/integration/ -v

dev-test-coverage: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	docker exec -it harbor-dev python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# =============================================================================
# Code Quality
# =============================================================================
dev-lint: ## Run linting in development environment
	@echo "🔍 Running linting..."
	docker exec -it harbor-dev ruff check app/ tests/

dev-format: ## Format code in development environment
	@echo "🎨 Formatting code..."
	docker exec -it harbor-dev ruff format app/ tests/
	docker exec -it harbor-dev black app/ tests/

dev-typecheck: ## Run type checking
	@echo "🔍 Running type checking..."
	docker exec -it harbor-dev mypy app/

dev-quality: ## Run all code quality checks
	@$(MAKE) dev-lint
	@$(MAKE) dev-typecheck
	@echo "✅ Code quality checks complete!"

# =============================================================================
# Database Management
# =============================================================================
dev-db-shell: ## Access SQLite database shell
	@echo "💾 Connecting to SQLite database..."
	docker exec -it harbor-dev sqlite3 /app/data/harbor_dev.db

dev-db-reset: ## Reset development database
	@echo "🗑️ Resetting development database..."
	docker exec -it harbor-dev rm -f /app/data/harbor_dev.db
	@echo "✅ Development database reset!"

dev-db-migrate: ## Run database migrations
	@echo "📊 Running database migrations..."
	docker exec -it harbor-dev python -m alembic upgrade head

dev-db-backup: ## Backup development database
	@echo "💾 Backing up development database..."
	docker exec -it harbor-dev cp /app/data/harbor_dev.db /app/data/harbor_dev_backup_$(shell date +%Y%m%d_%H%M%S).db
	@echo "✅ Database backed up!"

# =============================================================================
# Configuration Management (following project structure)
# =============================================================================
dev-config-edit: ## Edit development configuration
	@echo "⚙️ Opening development configuration..."
	@${EDITOR:-nano} $(CONFIG_DIR)/development.yaml

dev-config-validate: ## Validate configuration files
	@echo "🔍 Validating configuration files..."
	@if command -v yamllint >/dev/null 2>&1; then \
		yamllint $(CONFIG_DIR)/; \
	else \
		echo "💡 Install yamllint for configuration validation: pip install yamllint"; \
	fi

dev-config-show: ## Show current development configuration
	@echo "📋 Current development configuration:"
	@cat $(CONFIG_DIR)/development.yaml

# =============================================================================
# Project Structure Utilities
# =============================================================================
dev-structure: ## Show project structure (following foundational documents)
	@echo "📁 Harbor Project Structure (from foundational documents):"
	@echo ""
	@tree -I '__pycache__|*.pyc|node_modules|.git|.pytest_cache' -L 3 . || \
	find . -type d -not -path './.git/*' -not -path './__pycache__/*' -not -path './node_modules/*' | head -20

dev-examples: ## Show available example configurations
	@echo "📚 Available example configurations:"
	@echo ""
	@find examples/ -name "*.yml" -o -name "*.yaml" | sort || echo "No examples found"

# =============================================================================
# Development Utilities
# =============================================================================
dev-ps: ## Show development containers
	@docker ps --filter "name=harbor-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

dev-volumes: ## Show development volumes
	@echo "📦 Harbor Development Volumes:"
	@docker volume ls | grep harbor-dev

dev-network: ## Show development network info
	@echo "🌐 Harbor Development Network:"
	@docker network inspect harbor-dev-network --format '{{json .IPAM.Config}}' | jq '.[0]' 2>/dev/null || echo "Network not found"

dev-clean: ## Clean up development containers and images
	@echo "🧹 Cleaning up development environment..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml down --rmi local
	docker system prune -f
	@echo "✅ Development cleanup complete!"

dev-reset: ## Reset entire development environment (removes all data)
	@echo "⚠️  This will delete ALL development data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $REPLY =~ ^[Yy]$ ]]; then \
		echo ""; \
		echo "🗑️ Resetting development environment..."; \
		cd deploy/docker && docker-compose -f docker-compose.dev.yml down -v; \
		docker system prune -f; \
		echo "✅ Development environment reset!"; \
		echo "💡 Run 'make dev-setup && make dev-up' to start fresh"; \
	else \
		echo ""; \
		echo "❌ Reset cancelled"; \
	fi

# =============================================================================
# Build and Development
# =============================================================================
dev-build: ## Rebuild development Docker image
	@echo "🏗️ Building Harbor development image..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml build harbor-dev
	@echo "✅ Development image built!"

dev-build-no-cache: ## Rebuild development image without cache
	@echo "🏗️ Building Harbor development image (no cache)..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml build --no-cache harbor-dev
	@echo "✅ Development image built!"

dev-pull: ## Pull latest images for development services
	@echo "📥 Pulling latest development service images..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml pull
	@echo "✅ Images updated!"

# =============================================================================
# Debugging
# =============================================================================
dev-debug: ## Start Harbor with debugger enabled
	@echo "🐛 Starting Harbor with debugger on port 5678..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml up -d
	@echo "🔗 Connect your IDE debugger to localhost:5678"
	@echo "💡 PyCharm: Run > Attach to Process > localhost:5678"
	@echo "💡 VS Code: Use 'Python: Remote Attach' configuration"

dev-htop: ## Show resource usage in development container
	@echo "📊 Resource usage in Harbor development container:"
	docker exec -it harbor-dev htop

dev-inspect: ## Inspect Harbor development container
	@echo "🔍 Harbor development container details:"
	docker inspect harbor-dev | jq '.[0] | {Name: .Name, State: .State, Config: .Config.Env}' 2>/dev/null || echo "Container not found"

# =============================================================================
# Docker Registry Testing
# =============================================================================
dev-registry-up: ## Start test registry for testing registry features
	@echo "🐳 Starting test registry..."
	@cd deploy/docker && docker-compose -f docker-compose.dev.yml --profile registry up -d registry-dev
	@echo "✅ Test registry started at http://localhost:5000"

dev-registry-push: ## Push test image to local registry
	@echo "📤 Pushing test image to local registry..."
	docker tag nginx:alpine localhost:5000/test/nginx:latest
	docker push localhost:5000/test/nginx:latest
	@echo "✅ Test image pushed to registry"

dev-registry-list: ## List images in test registry
	@echo "📋 Images in test registry:"
	@curl -s http://localhost:5000/v2/_catalog | jq '.repositories' 2>/dev/null || echo "Registry not accessible"

# =============================================================================
# Performance Monitoring
# =============================================================================
dev-metrics: ## View Harbor metrics
	@echo "📊 Harbor development metrics:"
	@curl -s http://localhost:8080/metrics | head -20 2>/dev/null || echo "Metrics not available"

dev-health: ## Check Harbor health
	@echo "❤️ Harbor health status:"
	@curl -s http://localhost:8080/healthz | jq '.' 2>/dev/null || echo "Health endpoint not available"

dev-ready: ## Check Harbor readiness
	@echo "✅ Harbor readiness status:"
	@curl -s http://localhost:8080/readyz | jq '.' 2>/dev/null || echo "Readiness endpoint not available"

# =============================================================================
# Documentation
# =============================================================================
dev-docs: ## Generate and serve development documentation
	@echo "📚 Generating development documentation..."
	@if command -v mkdocs >/dev/null 2>&1; then \
		mkdocs serve -a 0.0.0.0:8000; \
	else \
		echo "💡 Install mkdocs: pip install mkdocs mkdocs-material"; \
	fi

dev-docs-open: ## Open development documentation in browser
	@echo "📖 Opening development documentation..."
	@open docs/development.md || xdg-open docs/development.md || echo "Please open docs/development.md manually"

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
	@echo "🏠 Starting basic home lab example..."
	@cd examples/home-lab/basic && docker-compose up -d

dev-example-monitoring: ## Start home lab with monitoring example
	@echo "📊 Starting home lab with monitoring example..."
	@cd examples/home-lab/with-monitoring && docker-compose up -d

dev-example-down: ## Stop all example deployments
	@echo "🛑 Stopping example deployments..."
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
# Help for specific workflows
# =============================================================================
dev-help-structure: ## Show help for project structure commands
	@echo "📁 Harbor Project Structure Commands"
	@echo "===================================="
	@echo ""
	@echo "Following Harbor Project Structure from foundational documents:"
	@echo ""
	@echo "📂 Directory Structure:"
	@echo "   deploy/docker/           - Docker deployment files"
	@echo "   config/                  - Configuration files"
	@echo "   examples/                - Example deployments"
	@echo "   scripts/dev/            - Development scripts"
	@echo "   tests/fixtures/         - Test data"
	@echo ""
	@echo "🔧 Structure Commands:"
	@echo "   make dev-structure      - Show current project structure"
	@echo "   make dev-examples       - List available examples"
	@echo "   make dev-config-show    - Show development configuration"

dev-help-examples: ## Show help for using examples
	@echo "📚 Harbor Example Configurations"
	@echo "================================="
	@echo ""
	@echo "Available examples following project structure:"
	@echo ""
	@echo "🏠 Home Lab Examples:"
	@echo "   examples/home-lab/basic/                 - Simple Harbor deployment"
	@echo "   examples/home-lab/with-monitoring/       - Harbor with Prometheus/Grafana"
	@echo "   examples/home-lab/with-traefik/         - Harbor with Traefik proxy"
	@echo "   examples/home-lab/raspberry-pi/         - Raspberry Pi optimized"
	@echo ""
	@echo "🏢 Enterprise Examples:"
	@echo "   examples/enterprise/high-availability/   - HA deployment"
	@echo "   examples/enterprise/monitoring/          - Full monitoring stack"
	@echo "   examples/enterprise/security/            - Security hardened"
	@echo ""
	@echo "🚀 Quick Start Commands:"
	@echo "   make dev-example-basic      - Start basic example"
	@echo "   make dev-example-monitoring - Start monitoring example"
	@echo "   make dev-example-down       - Stop all examples"

# =============================================================================
# Release Management (following Harbor project structure)
# =============================================================================
release-status: ## Show current release status and version information
	@echo "🚢 Harbor Release Status"
	@echo "======================="
	@echo ""
	@scripts/release/release.sh status

release-versions: ## Show suggested next version numbers
	@echo "📈 Harbor Version Suggestions"
	@echo "============================"
	@scripts/release/release.sh versions

release-prepare: ## Prepare release branch with version updates (Usage: make release-prepare VERSION=0.1.1)
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ VERSION parameter required"; \
		echo "Usage: make release-prepare VERSION=0.1.1"; \
		exit 1; \
	fi
	@echo "🚀 Preparing Harbor release $(VERSION)..."
	@scripts/release/release.sh prepare $(VERSION)

release-tag: ## Create and push release tag (Usage: make release-tag VERSION=0.1.1)
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ VERSION parameter required"; \
		echo "Usage: make release-tag VERSION=0.1.1"; \
		exit 1; \
	fi
	@echo "🏷️ Creating Harbor release tag v$(VERSION)..."
	@scripts/release/release.sh tag $(VERSION)

release-validate: ## Validate version consistency across project files
	@echo "🔍 Validating Harbor version consistency..."
	@python scripts/release/validate_version.py validate

release-changelog: ## Generate changelog for version (Usage: make release-changelog VERSION=0.1.1)
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ VERSION parameter required"; \
		echo "Usage: make release-changelog VERSION=0.1.1"; \
		exit 1; \
	fi
	@echo "📝 Generating changelog for Harbor $(VERSION)..."
	@python scripts/release/validate_version.py changelog --version $(VERSION)

release-changelog-file: ## Generate changelog and update CHANGELOG.md (Usage: make release-changelog-file VERSION=0.1.1)
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ VERSION parameter required"; \
		echo "Usage: make release-changelog-file VERSION=0.1.1"; \
		exit 1; \
	fi
	@echo "📝 Updating CHANGELOG.md for Harbor $(VERSION)..."
	@python scripts/release/validate_version.py changelog --version $(VERSION) --output temp-changelog.md
	@echo "✅ Changelog generated in temp-changelog.md"
	@echo "💡 Review and manually merge into CHANGELOG.md"

release-increment: ## Show incremented version (Usage: make release-increment TYPE=patch)
	@if [ -z "$(TYPE)" ]; then \
		echo "❌ TYPE parameter required"; \
		echo "Usage: make release-increment TYPE=patch"; \
		echo "Valid types: major, minor, patch, rc"; \
		exit 1; \
	fi
	@scripts/release/release.sh increment $(TYPE)

release-help: ## Show detailed release management help
	@echo "🚢 Harbor Release Management Commands"
	@echo "===================================="
	@echo ""
	@echo "Following Harbor Project Structure from foundational documents"
	@echo ""
	@echo "📊 Status Commands:"
	@echo "   make release-status              # Show current release status"
	@echo "   make release-versions            # Show suggested next versions"
	@echo "   make release-validate            # Validate version consistency"
	@echo ""
	@echo "🔢 Version Commands:"
	@echo "   make release-increment TYPE=patch   # Show next patch version"
	@echo "   make release-increment TYPE=minor   # Show next minor version"
	@echo "   make release-increment TYPE=major   # Show next major version"
	@echo "   make release-increment TYPE=rc      # Show next RC version"
	@echo ""
	@echo "📝 Changelog Commands:"
	@echo "   make release-changelog VERSION=0.1.1           # Generate changelog"
	@echo "   make release-changelog-file VERSION=0.1.1      # Update CHANGELOG.md"
	@echo ""
	@echo "🚀 Release Process:"
	@echo "   1. make release-status                          # Check current status"
	@echo "   2. make release-prepare VERSION=0.1.1          # Prepare release branch"
	@echo "   3. Create PR and review changes                 # Manual review"
	@echo "   4. Merge PR to main                             # Manual merge"
	@echo "   5. make release-tag VERSION=0.1.1              # Create release tag"
	@echo ""
	@echo "🎯 Harbor Milestone Mapping:"
	@echo "   0.1.x → M0 (Foundation)       - Project infrastructure, CI/CD"
	@echo "   0.2.x → M1 (Discovery)        - Container discovery, registry integration"
	@echo "   0.3.x → M2 (Updates)          - Safe update engine with rollback"
	@echo "   0.4.x → M3 (Automation)       - Scheduling and web interface"
	@echo "   0.5.x → M4 (Observability)    - Monitoring and metrics"
	@echo "   0.6.x → M5 (Production)       - Security hardening, performance"
	@echo "   1.0.x → M6 (Release)          - Community launch, documentation"
	@echo ""
	@echo "📚 Documentation:"
	@echo "   Release Guide: docs/development/releases.md"
	@echo "   Semantic Versioning: https://semver.org"
	@echo "   Changelog Format: https://keepachangelog.com"

# Quick release workflows
release-quick-patch: ## Quick patch release workflow (current version + 0.0.1)
	@CURRENT_VERSION=$$(scripts/release/release.sh increment patch); \
	echo "🚀 Quick patch release: $$CURRENT_VERSION"; \
	make release-prepare VERSION=$$CURRENT_VERSION

release-quick-minor: ## Quick minor release workflow (current version + 0.1.0)
	@CURRENT_VERSION=$$(scripts/release/release.sh increment minor); \
	echo "🚀 Quick minor release: $$CURRENT_VERSION"; \
	make release-prepare VERSION=$$CURRENT_VERSION

release-quick-rc: ## Quick RC release workflow (current version + RC)
	@CURRENT_VERSION=$$(scripts/release/release.sh increment rc); \
	echo "🚀 Quick RC release: $$CURRENT_VERSION"; \
	make release-prepare VERSION=$$CURRENT_VERSION

# =============================================================================
# Default target
# =============================================================================
.DEFAULT_GOAL := help
