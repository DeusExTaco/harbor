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

# =============================================================================
# Multi-Architecture Build Commands (Add to existing Makefile)
# Following Harbor Project Structure from foundational documents
# =============================================================================

# Multi-architecture configuration
PLATFORMS = linux/amd64,linux/arm64,linux/arm/v7
SINGLE_PLATFORM = linux/amd64
VERSION = $(shell grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
GHCR_IMAGE = ghcr.io/deusextaco/harbor
DOCKERHUB_IMAGE = dextaco/harbor

# =============================================================================
# Multi-Architecture Build Commands
# =============================================================================

build-multiarch: ## Build multi-architecture images locally
	@echo "🗏️ Building Harbor multi-architecture images..."
	@echo "Platforms: $(PLATFORMS)"
	@echo "Version: $(VERSION)"
	@echo ""
	@echo "📋 Platform Summary:"
	@echo "   🖥️ AMD64: Full performance, all features"
	@echo "   🎯 ARM64: Balanced performance for Apple Silicon & Pi 4"
	@echo "   🥧 ARMv7: Memory-optimized for Raspberry Pi 3"
	@echo ""
	docker buildx create --name harbor-builder --use || docker buildx use harbor-builder
	docker buildx build \
		--platform $(PLATFORMS) \
		--file deploy/docker/Dockerfile \
		--tag $(GHCR_IMAGE):$(VERSION) \
		--tag $(GHCR_IMAGE):latest \
		--build-arg HARBOR_VERSION=$(VERSION) \
		--build-arg BUILD_MODE=production \
		--load \
		.
	@echo "✅ Multi-architecture build completed!"
	@echo ""
	@echo "🎯 Usage Examples:"
	@echo "   AMD64:  docker run -d -p 8080:8080 $(GHCR_IMAGE):$(VERSION)"
	@echo "   ARM64:  docker run -d -p 8080:8080 -e HARBOR_MAX_WORKERS=2 $(GHCR_IMAGE):$(VERSION)"
	@echo "   ARMv7:  docker run -d -p 8080:8080 -e HARBOR_MAX_WORKERS=1 $(GHCR_IMAGE):$(VERSION)"

build-multiarch-push: ## Build and push multi-architecture images
	@echo "🏗️ Building and pushing Harbor multi-architecture images..."
	@echo "Platforms: $(PLATFORMS)"
	@echo "Version: $(VERSION)"
	@echo ""
	docker buildx create --name harbor-builder --use || docker buildx use harbor-builder
	docker buildx build \
		--platform $(PLATFORMS) \
		--file deploy/docker/Dockerfile \
		--tag $(GHCR_IMAGE):$(VERSION) \
		--tag $(GHCR_IMAGE):latest \
		--build-arg HARBOR_VERSION=$(VERSION) \
		--build-arg BUILD_MODE=production \
		--push \
		.
	@echo "✅ Multi-architecture images built and pushed!"

build-single: ## Build single-platform image (fast for development)
	@echo "🔧 Building Harbor single-platform image ($(SINGLE_PLATFORM))..."
	docker buildx build \
		--platform $(SINGLE_PLATFORM) \
		--file deploy/docker/Dockerfile.dev \
		--tag harbor:dev \
		--build-arg HARBOR_VERSION=$(VERSION)-dev \
		--build-arg BUILD_MODE=development \
		--load \
		.
	@echo "✅ Single-platform development image built!"

# =============================================================================
# Platform Testing Commands
# =============================================================================

test-multiarch: ## Test all platform images
	@echo "🧪 Testing Harbor multi-platform images..."
	@chmod +x scripts/test-multi-platform.sh
	@scripts/test-multi-platform.sh

test-multiarch-ghcr: ## Test GHCR multi-platform images only
	@echo "🧪 Testing GHCR multi-platform images..."
	@chmod +x scripts/test-multi-platform.sh
	@scripts/test-multi-platform.sh --ghcr-only

test-multiarch-dockerhub: ## Test Docker Hub multi-platform images only
	@echo "🧪 Testing Docker Hub multi-platform images..."
	@chmod +x scripts/test-multi-platform.sh
	@scripts/test-multi-platform.sh --dockerhub-only

test-multiarch-benchmark: ## Run startup performance benchmarks across platforms
	@echo "📊 Running multi-platform performance benchmarks..."
	@chmod +x scripts/test-multi-platform.sh
	@scripts/test-multi-platform.sh --benchmark

test-multiarch-cleanup: ## Clean up all multi-platform test containers
	@echo "🧹 Cleaning up multi-platform test containers..."
	@scripts/test-multi-platform.sh cleanup

# =============================================================================
# Platform-Specific Development
# =============================================================================

dev-rpi: ## Start development environment optimized for Raspberry Pi
	@echo "🥧 Starting Raspberry Pi optimized development environment..."
	@cd examples/home-lab/raspberry-pi && docker-compose up -d
	@echo "✅ Raspberry Pi development environment started!"
	@echo "🌐 Harbor available at: http://localhost:8080"

dev-rpi-down: ## Stop Raspberry Pi development environment
	@echo "🛑 Stopping Raspberry Pi development environment..."
	@cd examples/home-lab/raspberry-pi && docker-compose down

dev-arm64: ## Start development environment optimized for ARM64
	@echo "🍎 Starting ARM64 optimized development environment..."
	@cd deploy/docker && HARBOR_MAX_WORKERS=2 MAX_CONCURRENT_UPDATES=1 docker-compose -f docker-compose.dev.yml up -d
	@echo "✅ ARM64 development environment started!"

# =============================================================================
# Platform Information and Utilities
# =============================================================================

build-info: ## Show build configuration and platform information
	@echo "🏗️ Harbor Multi-Architecture Build Information"
	@echo "=============================================="
	@echo ""
	@echo "📦 Project Information:"
	@echo "   Version: $(VERSION)"
	@echo "   Image Base: $(GHCR_IMAGE)"
	@echo "   Supported Platforms: $(PLATFORMS)"
	@echo ""
	@echo "🖥️ Host Information:"
	@uname -a
	@echo ""
	@echo "🐳 Docker Information:"
	@docker version --format 'json' | jq -r '.Client.Version' | sed 's/^/   Docker Version: /' 2>/dev/null || docker --version
	@docker buildx version 2>/dev/null | sed 's/^/   Buildx Version: /' || echo "   Buildx: Not available"
	@echo ""
	@echo "🏗️ Available Builders:"
	@docker buildx ls 2>/dev/null || echo "   No buildx builders available"

platform-detect: ## Detect current platform and show optimization recommendations
	@echo "🔍 Platform Detection and Optimization Recommendations"
	@echo "====================================================="
	@echo ""
	@echo "🖥️ Host Platform:"
	@ARCH=$$(uname -m); \
	case "$$ARCH" in \
		"x86_64"|"amd64") \
			echo "   Architecture: x86_64/AMD64"; \
			echo "   Recommendation: Use standard Harbor deployment"; \
			echo "   Docker Run: docker run -d -p 8080:8080 $(GHCR_IMAGE):$(VERSION)"; \
			;; \
		"aarch64"|"arm64") \
			echo "   Architecture: ARM64"; \
			echo "   Recommendation: Use ARM64 optimized deployment"; \
			echo "   Docker Run: docker run -d -p 8080:8080 -e HARBOR_MAX_WORKERS=2 $(GHCR_IMAGE):$(VERSION)"; \
			;; \
		"armv7l") \
			echo "   Architecture: ARMv7"; \
			echo "   Recommendation: Use Raspberry Pi optimized deployment"; \
			echo "   Docker Run: docker run -d -p 8080:8080 -e HARBOR_MAX_WORKERS=1 -e LOG_RETENTION_DAYS=7 $(GHCR_IMAGE):$(VERSION)"; \
			;; \
		*) \
			echo "   Architecture: $$ARCH (Unknown)"; \
			echo "   Recommendation: Try AMD64 image with platform override"; \
			echo "   Docker Run: docker run --platform linux/amd64 -d -p 8080:8080 $(GHCR_IMAGE):$(VERSION)"; \
			;; \
	esac
	@echo ""
	@echo "📱 Available Platform Images:"
	@echo "   Multi-platform: $(GHCR_IMAGE):$(VERSION)"
	@echo "   AMD64 specific: $(GHCR_IMAGE):$(VERSION)-amd64"
	@echo "   ARM64 specific: $(GHCR_IMAGE):$(VERSION)-arm64"
	@echo "   ARMv7 specific: $(GHCR_IMAGE):$(VERSION)-armv7"

# =============================================================================
# Platform-Specific Example Deployments
# =============================================================================

example-amd64: ## Deploy AMD64 optimized example
	@echo "🖥️ Starting AMD64 optimized Harbor example..."
	@cd examples/home-lab/basic && docker-compose up -d
	@echo "✅ AMD64 example started at http://localhost:8080"

example-arm64: ## Deploy ARM64 optimized example (Apple Silicon, Pi 4)
	@echo "🍎 Starting ARM64 optimized Harbor example..."
	@cd examples/home-lab/basic && HARBOR_MAX_WORKERS=2 MAX_CONCURRENT_UPDATES=1 docker-compose up -d
	@echo "✅ ARM64 example started at http://localhost:8080"

example-armv7: ## Deploy ARMv7 optimized example (Raspberry Pi 3)
	@echo "🥧 Starting ARMv7 optimized Harbor example..."
	@cd examples/home-lab/raspberry-pi && docker-compose up -d
	@echo "✅ ARMv7 example started at http://localhost:8080"

example-down: ## Stop all example deployments
	@echo "🛑 Stopping all Harbor example deployments..."
	@cd examples/home-lab/basic && docker-compose down 2>/dev/null || true
	@cd examples/home-lab/raspberry-pi && docker-compose down 2>/dev/null || true
	@echo "✅ All examples stopped"

# =============================================================================
# Multi-Architecture Development Workflows
# =============================================================================

dev-multiarch-setup: ## Set up multi-architecture development environment
	@echo "🏗️ Setting up multi-architecture development environment..."
	@echo ""
	@echo "🔧 Creating docker buildx builder..."
	docker buildx create --name harbor-multiarch --use || docker buildx use harbor-multiarch
	@echo ""
	@echo "🧪 Testing multi-platform capability..."
	docker buildx inspect --bootstrap
	@echo ""
	@echo "✅ Multi-architecture development environment ready!"
	@echo ""
	@echo "🎯 Available commands:"
	@echo "   make build-multiarch         # Build for all platforms locally"
	@echo "   make test-multiarch          # Test all platform images"
	@echo "   make platform-detect         # Show platform-specific recommendations"

dev-multiarch-clean: ## Clean up multi-architecture development environment
	@echo "🧹 Cleaning up multi-architecture development..."
	@docker buildx rm harbor-multiarch 2>/dev/null || true
	@docker buildx prune -f
	@$(MAKE) test-multiarch-cleanup
	@echo "✅ Multi-architecture development cleanup complete!"

# =============================================================================
# Quick Multi-Platform Workflows
# =============================================================================

quick-multiarch: dev-multiarch-setup build-multiarch test-multiarch ## Complete multi-arch build and test workflow

quick-rpi: dev-rpi ## Quick Raspberry Pi development environment

quick-platform-test: platform-detect test-multiarch-ghcr ## Quick platform detection and testing

# =============================================================================
# Multi-Architecture Help
# =============================================================================

help-multiarch: ## Show detailed multi-architecture help
	@echo "🏗️ Harbor Multi-Architecture Build System"
	@echo "=========================================="
	@echo ""
	@echo "Following Harbor Project Structure from foundational documents"
	@echo ""
	@echo "🎯 Supported Platforms:"
	@echo "   linux/amd64     - Intel/AMD processors (full performance)"
	@echo "   linux/arm64     - Apple Silicon, modern ARM servers, Raspberry Pi 4"
	@echo "   linux/arm/v7    - Raspberry Pi 3, older ARM devices"
	@echo ""
	@echo "🔧 Build Commands:"
	@echo "   make build-multiarch              # Build all platforms locally"
	@echo "   make build-multiarch-push         # Build and push to registries"
	@echo "   make build-single                 # Fast single-platform dev build"
	@echo ""
	@echo "🧪 Testing Commands:"
	@echo "   make test-multiarch               # Test all platforms"
	@echo "   make test-multiarch-ghcr          # Test GHCR images only"
	@echo "   make test-multiarch-benchmark     # Performance benchmarks"
	@echo "   make test-multiarch-cleanup       # Clean up test containers"
	@echo ""
	@echo "🥧 Platform-Specific Development:"
	@echo "   make dev-rpi                      # Raspberry Pi optimized environment"
	@echo "   make dev-arm64                    # ARM64 optimized environment"
	@echo "   make example-armv7                # ARMv7 example deployment"
	@echo ""
	@echo "ℹ️ Platform Detection:"
	@echo "   make platform-detect              # Show current platform and recommendations"
	@echo "   make build-info                   # Show build system information"
	@echo ""
	@echo "🚀 Quick Workflows:"
	@echo "   make quick-multiarch              # Complete build and test workflow"
	@echo "   make quick-rpi                    # Quick Raspberry Pi setup"
	@echo "   make quick-platform-test          # Quick platform test"
	@echo ""
	@echo "📚 Documentation:"
	@echo "   Platform Guide: docs/platforms.md"
	@echo "   ARM Deployment: docs/deployment/raspberry-pi.md"
	@echo "   Performance Tuning: docs/configuration/performance.md"
	@echo ""
	@echo "🎯 Current Configuration:"
	@echo "   Version: $(VERSION)"
	@echo "   Platforms: $(PLATFORMS)"
	@echo "   Base Image: $(GHCR_IMAGE)"
	@echo ""
	@echo "💡 Tips:"
	@echo "   - Use 'make build-single' for fast development builds"
	@echo "   - Use 'make build-multiarch' to test all platforms locally"
	@echo "   - CI/CD automatically builds multi-arch on main branch"
	@echo "   - ARMv7 builds are optimized for Raspberry Pi constraints"
	@echo "   - ARM64 builds work natively on Apple Silicon"

# =============================================================================
# Multi-Architecture Testing and Validation Commands
# Following Harbor Project Structure from foundational documents
# =============================================================================

test-quick: ## Run quick validation of multi-arch setup (2 minutes)
	@echo "🚀 Running Harbor quick test suite..."
	@echo "This validates: project structure, platform detection, Docker, basic build"
	@chmod +x scripts/quick-test.sh scripts/dev/*.sh scripts/dev/*.py
	@scripts/quick-test.sh

test-ci-readiness: ## Check if repository is ready for CI/CD pipeline (1 minute)
	@echo "🔍 Checking CI/CD readiness..."
	@echo "Validates: required files, workflows, configs, versions"
	@chmod +x scripts/check-ci-readiness.sh
	@scripts/check-ci-readiness.sh

test-platform-local: ## Test platform detection and optimization locally
	@echo "🎯 Testing platform detection..."
	@python scripts/detect_platform.py

test-validate-multiarch: ## Validate multi-architecture development environment
	@echo "✅ Validating multi-architecture setup..."
	@python scripts/dev/validate-multiarch.py

test-docker-environment: ## Test Docker and buildx setup
	@echo "🐳 Testing Docker environment..."
	@docker --version
	@docker-compose --version || docker compose version
	@docker buildx version
	@docker buildx ls

# =============================================================================
# Complete Testing Workflows
# =============================================================================

test-workflow: test-quick test-ci-readiness ## Run complete local testing workflow (3 minutes)
	@echo ""
	@echo "🎉 Complete testing workflow finished!"
	@echo ""
	@echo "📋 Summary:"
	@echo "  ✅ Quick tests passed"
	@echo "  ✅ CI/CD readiness confirmed"
	@echo ""
	@echo "🚀 Ready to push to CI/CD pipeline!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. git add ."
	@echo "  2. git commit -m 'feat: implement multi-architecture support'"
	@echo "  3. git push"

test-all-platforms: build-multiarch test-multiarch ## Build and test all platforms (10-15 minutes)
	@echo ""
	@echo "🌐 Multi-platform build and test completed!"
	@echo ""
	@echo "📋 Platform Testing Summary:"
	@echo "  🖥️ AMD64: Full performance testing"
	@echo "  🎯 ARM64: Native/emulated testing"
	@echo "  🥧 ARMv7: Raspberry Pi 3 optimized testing"

test-complete: test-workflow dev-multiarch-setup test-all-platforms ## Complete end-to-end testing (20 minutes)
	@echo ""
	@echo "🏆 COMPLETE MULTI-ARCHITECTURE TESTING FINISHED!"
	@echo ""
	@echo "✅ All tests passed:"
	@echo "  • Project structure validated"
	@echo "  • Platform detection working"
	@echo "  • Multi-arch environment ready"
	@echo "  • All platforms built and tested"
	@echo ""
	@echo "🚀 Ready for production CI/CD pipeline!"

# =============================================================================
# Multi-Architecture Build Testing
# =============================================================================

test-build-single: ## Test single platform build (fast)
	@echo "🏗️ Testing single platform build..."
	@docker build -f deploy/docker/Dockerfile.dev -t harbor:test-single .
	@docker run --rm harbor:test-single python -c "\
import sys, platform, app; \
print('✅ Harbor image works!'); \
print(f'Platform: {platform.machine()}'); \
print(f'Python: {sys.version}'); \
print(f'Harbor version: {app.__version__}') \
"
	@echo "✅ Single platform build test passed!"


test-build-multiarch: build-multiarch ## Test multi-architecture build
	@echo "🌐 Multi-architecture build completed!"
	@echo "Images built for: $(PLATFORMS)"
	@docker images | grep harbor

test-container-startup: ## Test container startup and health checks
	@echo "🚀 Testing container startup..."
	@docker run -d --name harbor-startup-test -p 8099:8080 -e HARBOR_MODE=development harbor:test-single
	@echo "Waiting for startup..."
	@for i in $$(seq 1 30); do \
		if curl -s http://localhost:8099/healthz > /dev/null; then \
			echo "✅ Container started successfully ($$i seconds)"; \
			break; \
		fi; \
		if [ $$i -eq 30 ]; then \
			echo "❌ Container failed to start"; \
			docker logs harbor-startup-test; \
			exit 1; \
		fi; \
		sleep 1; \
	done
	@echo "Testing health endpoint..."
	@curl -s http://localhost:8099/healthz | jq '.status' || echo "Health check response received"
	@docker stop harbor-startup-test
	@docker rm harbor-startup-test
	@echo "✅ Container startup test passed!"

# =============================================================================
# Platform-Specific Testing
# =============================================================================

test-amd64: ## Test AMD64 platform specifically
	@echo "🖥️ Testing AMD64 platform..."
	@docker run --platform linux/amd64 --rm $(GHCR_IMAGE):$(VERSION) python /app/scripts/detect_platform.py

test-arm64: ## Test ARM64 platform specifically
	@echo "🎯 Testing ARM64 platform..."
	@docker run --platform linux/arm64 --rm $(GHCR_IMAGE):$(VERSION) python /app/scripts/detect_platform.py

test-armv7: ## Test ARMv7 platform specifically
	@echo "🥧 Testing ARMv7 platform..."
	@docker run --platform linux/arm/v7 --rm $(GHCR_IMAGE):$(VERSION) python /app/scripts/detect_platform.py

test-platforms-individual: test-amd64 test-arm64 test-armv7 ## Test each platform individually
	@echo "✅ All individual platform tests completed!"

# =============================================================================
# CI/CD Simulation
# =============================================================================

test-ci-simulation: ## Simulate CI/CD pipeline locally
	@echo "🔄 Simulating CI/CD pipeline locally..."
	@echo ""
	@echo "Stage 1: Code Quality"
	@make dev-quality
	@echo ""
	@echo "Stage 2: Unit Tests"
	@make dev-test-unit
	@echo ""
	@echo "Stage 3: Build Testing"
	@make test-build-single
	@echo ""
	@echo "Stage 4: Container Testing"
	@make test-container-startup
	@echo ""
	@echo "✅ CI/CD simulation completed successfully!"

# =============================================================================
# Troubleshooting and Diagnostics
# =============================================================================

test-diagnose: ## Diagnose testing environment issues
	@echo "🔍 Diagnosing Harbor testing environment..."
	@echo ""
	@echo "📋 Environment Information:"
	@echo "Host Platform: $$(uname -m) ($$(uname -s))"
	@echo "Docker Version: $$(docker --version)"
	@echo "Buildx Version: $$(docker buildx version || echo 'Not available')"
	@echo ""
	@echo "📁 Project Structure:"
	@ls -la deploy/docker/ || echo "❌ deploy/docker/ missing"
	@ls -la scripts/ || echo "❌ scripts/ missing"
	@ls -la app/ || echo "❌ app/ missing"
	@echo ""
	@echo "🐳 Docker Status:"
	@docker info --format '{{.OSType}}/{{.Architecture}}' || echo "❌ Docker not accessible"
	@docker buildx ls || echo "❌ Buildx not available"
	@echo ""
	@echo "🔧 Available Make Targets:"
	@make help | grep test

test-fix-permissions: ## Fix script permissions
	@echo "🔧 Fixing script permissions..."
	@chmod +x scripts/*.sh
	@chmod +x scripts/dev/*.sh
	@chmod +x scripts/dev/*.py
	@chmod +x scripts/*.py
	@echo "✅ Script permissions fixed"

# =============================================================================
# Testing Help and Documentation
# =============================================================================

test-help: ## Show detailed testing help and available commands
	@echo "🧪 Harbor Multi-Architecture Testing Commands"
	@echo "============================================="
	@echo ""
	@echo "📋 Quick Testing (start here):"
	@echo "   make test-quick              # 2min - Essential validation"
	@echo "   make test-ci-readiness       # 1min - CI/CD readiness check"
	@echo "   make test-workflow           # 3min - Complete local testing"
	@echo ""
	@echo "🌐 Multi-Architecture Testing:"
	@echo "   make test-platform-local     # Test platform detection"
	@echo "   make test-validate-multiarch # Validate multi-arch environment"
	@echo "   make test-docker-environment # Test Docker/buildx setup"
	@echo "   make build-multiarch         # Build all platforms"
	@echo "   make test-multiarch          # Test all platform images"
	@echo "   make test-all-platforms      # Complete multi-arch workflow"
	@echo ""
	@echo "🏗️ Build Testing:"
	@echo "   make test-build-single       # Fast single platform build test"
	@echo "   make test-build-multiarch    # Multi-arch build test"
	@echo "   make test-container-startup  # Container startup validation"
	@echo ""
	@echo "🎯 Platform-Specific Testing:"
	@echo "   make test-amd64             # Test AMD64 optimizations"
	@echo "   make test-arm64             # Test ARM64 optimizations"
	@echo "   make test-armv7             # Test ARMv7 (Pi 3) optimizations"
	@echo "   make test-platforms-individual # Test all platforms separately"
	@echo ""
	@echo "🐳 Development Testing:"
	@echo "   make dev-test               # Run pytest in container"
	@echo "   make dev-test-unit          # Unit tests only"
	@echo "   make dev-test-integration   # Integration tests only"
	@echo "   make dev-test-coverage      # Tests with coverage report"
	@echo "   make dev-test-all           # All dev tests + quality"
	@echo ""
	@echo "🔄 CI/CD Simulation:"
	@echo "   make test-ci-simulation     # Simulate full CI/CD locally"
	@echo ""
	@echo "🔧 Troubleshooting:"
	@echo "   make test-diagnose          # Diagnose environment issues"
	@echo "   make test-fix-permissions   # Fix script permissions"
	@echo ""
	@echo "🚀 Complete Workflows:"
	@echo "   make test-complete          # Complete end-to-end testing (20min)"
	@echo ""
	@echo "🎯 Recommended Testing Sequence for Multi-Arch Changes:"
	@echo "   1. make test-workflow           # Validate basics (3min)"
	@echo "   2. make dev-multiarch-setup     # Setup multi-arch environment"
	@echo "   3. make test-all-platforms      # Build and test all platforms (15min)"
	@echo "   4. git commit && git push       # Trigger CI/CD pipeline"
	@echo ""
	@echo "📚 Documentation:"
	@echo "   • Detailed guide: ./TESTING_CHECKLIST.md"
	@echo "   • Quick start: make test-workflow"
	@echo "   • Full help: make help"
	@echo ""
	@echo "🏁 Start Here: make test-workflow"