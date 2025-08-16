#!/bin/bash
# =============================================================================
# Harbor Development Setup Script
# Located: scripts/dev/setup.sh
# Sets up complete development environment following project structure
# =============================================================================

set -e

echo "🛳️ Setting up Harbor development environment..."
echo "Following Harbor Project Structure from foundational documents"

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "📁 Project root: $PROJECT_ROOT"

# Create directory structure as per Harbor Project Structure document
echo "📁 Creating directory structure..."

# Core directories from project structure
mkdir -p "$PROJECT_ROOT/config/monitoring/grafana/"{dashboards,datasources}
mkdir -p "$PROJECT_ROOT/config/monitoring/alerting"
mkdir -p "$PROJECT_ROOT/examples/home-lab/"{basic,with-monitoring,with-traefik,raspberry-pi}
mkdir -p "$PROJECT_ROOT/examples/enterprise/"{high-availability,monitoring,security}
mkdir -p "$PROJECT_ROOT/tests/fixtures"
mkdir -p "$PROJECT_ROOT/data"
mkdir -p "$PROJECT_ROOT/logs"

echo "⚙️ Creating configuration files..."

# Redis configuration
cat > "$PROJECT_ROOT/config/redis-dev.conf" << 'EOF'
# Redis Development Configuration
bind 0.0.0.0
port 6379
requirepass dev_password_123  # pragma: allowlist secret

# Development optimizations
save 60 1000
maxmemory 128mb
maxmemory-policy allkeys-lru

# Logging
loglevel notice
logfile ""
EOF

# Prometheus configuration
cat > "$PROJECT_ROOT/config/monitoring/prometheus.yml" << 'EOF'
# Prometheus Development Configuration
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files: []

scrape_configs:
  - job_name: 'harbor-dev'
    static_configs:
      - targets: ['harbor-dev:8080']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'redis-dev'
    static_configs:
      - targets: ['redis-dev:6379']
    scrape_interval: 30s
EOF

# Registry configuration
cat > "$PROJECT_ROOT/config/registry-dev.yml" << 'EOF'
# Test Registry Configuration
version: 0.1
log:
  fields:
    service: registry
storage:
  cache:
    blobdescriptor: inmemory
  filesystem:
    rootdirectory: /var/lib/registry
http:
  addr: :5000
  headers:
    X-Content-Type-Options: [nosniff]
    Access-Control-Allow-Origin: ['*']
    Access-Control-Allow-Methods: ['HEAD', 'GET', 'OPTIONS', 'DELETE']
    Access-Control-Allow-Headers: ['Authorization', 'Accept', 'Cache-Control']
health:
  storagedriver:
    enabled: true
    interval: 10s
    threshold: 3
EOF

# PostgreSQL initialization script
cat > "$PROJECT_ROOT/scripts/init-postgres-dev.sql" << 'EOF'
-- PostgreSQL Development Database Initialization
-- Create development database and user
CREATE DATABASE harbor_dev_test;
GRANT ALL PRIVILEGES ON DATABASE harbor_dev TO harbor_dev;
GRANT ALL PRIVILEGES ON DATABASE harbor_dev_test TO harbor_dev;

-- Create extensions if needed
\c harbor_dev;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c harbor_dev_test;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOF

# Test nginx configuration
cat > "$PROJECT_ROOT/tests/fixtures/nginx.conf" << 'EOF'
# Test Nginx Configuration for Harbor Discovery Testing
events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        location / {
            return 200 'Harbor Test Nginx - Container Discovery Test\n';
            add_header Content-Type text/plain;
        }

        location /health {
            return 200 'OK';
            add_header Content-Type text/plain;
        }
    }
}
EOF

# Grafana datasource configuration
cat > "$PROJECT_ROOT/config/monitoring/grafana/datasources/prometheus.yml" << 'EOF'
# Grafana Prometheus Datasource Configuration
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus-dev:9090
    isDefault: true
EOF

# Create example configurations following project structure

# Basic home lab example
cat > "$PROJECT_ROOT/examples/home-lab/basic/docker-compose.yml" << 'EOF'
# Basic Home Lab Example
# Simple Harbor deployment for home labs
version: '3.8'

services:
  harbor:
    image: ghcr.io/deusextaco/harbor:latest
    container_name: harbor
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - harbor_data:/app/data
    environment:
      - HARBOR_MODE=homelab
    labels:
      - "harbor.exclude=true"

volumes:
  harbor_data:
    driver: local
EOF

# Home lab with monitoring example
cat > "$PROJECT_ROOT/examples/home-lab/with-monitoring/docker-compose.yml" << 'EOF'
# Home Lab with Monitoring Example
# Harbor with Prometheus and Grafana
version: '3.8'

services:
  harbor:
    image: ghcr.io/deusextaco/harbor:latest
    container_name: harbor
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - harbor_data:/app/data
    environment:
      - HARBOR_MODE=homelab
      - ENABLE_METRICS=true
    labels:
      - "harbor.exclude=true"

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin  # pragma: allowlist secret

volumes:
  harbor_data:
  prometheus_data:
  grafana_data:
EOF

# Create .env.development file
cat > "$PROJECT_ROOT/.env.development" << 'EOF'
# Harbor Development Environment Configuration
# This file is loaded automatically in development mode

# Core configuration
HARBOR_MODE=development
LOG_LEVEL=DEBUG
DEV_RELOAD=true

# Database
DATABASE_URL=sqlite:///data/harbor_dev.db
# Uncomment for PostgreSQL testing:
# DATABASE_URL=postgresql://harbor_dev:dev_password_123@postgres-dev:5432/harbor_dev  # pragma: allowlist secret

# Redis
REDIS_URL=redis://:dev_password_123@redis-dev:6379/0  # pragma: allowlist secret

# Development features
ENABLE_AUTO_DISCOVERY=true
ENABLE_METRICS=true
ENABLE_SIMPLE_MODE=true
SHOW_GETTING_STARTED=true

# Performance (development optimized)
MAX_CONCURRENT_UPDATES=1
DEFAULT_CHECK_INTERVAL_SECONDS=300
REGISTRY_CACHE_TTL=300
DATABASE_POOL_SIZE=3
HARBOR_MAX_WORKERS=2

# Security (relaxed for development)
REQUIRE_HTTPS=false
SESSION_TIMEOUT_HOURS=168
API_RATE_LIMIT_PER_HOUR=10000

# Debug settings
PYTHONPATH=/app
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
EOF

# Create development Makefile commands documentation
cat > "$PROJECT_ROOT/docs/development.md" << 'EOF'
# Harbor Development Guide

## Quick Start

```bash
# Setup development environment
make dev-setup

# Start basic development
make dev-up

# Start with all services
make dev-full
```

## Available Commands

See `make help` for full list of development commands.

## Directory Structure

This development setup follows the Harbor Project Structure from the foundational documents:

- `deploy/docker/` - Docker deployment files
- `config/` - Configuration files
- `examples/` - Example deployments
- `scripts/dev/` - Development scripts
- `tests/fixtures/` - Test data

## Development URLs

- Harbor: http://localhost:8080
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- MailHog: http://localhost:8025
- Test Registry: http://localhost:5000
EOF

echo "✅ Development environment setup complete!"
echo ""
echo "📋 Created directory structure following Harbor Project Structure:"
echo "   - config/ (configuration files)"
echo "   - deploy/docker/ (deployment files)"
echo "   - examples/ (example configurations)"
echo "   - scripts/dev/ (development scripts)"
echo "   - tests/fixtures/ (test data)"
echo ""
echo "🚀 To start development:"
echo "   Basic setup:     cd deploy/docker && docker-compose -f docker-compose.dev.yml up"
echo "   With PostgreSQL: cd deploy/docker && docker-compose -f docker-compose.dev.yml --profile postgres up"
echo "   With monitoring: cd deploy/docker && docker-compose -f docker-compose.dev.yml --profile monitoring up"
echo "   Full stack:      cd deploy/docker && docker-compose -f docker-compose.dev.yml --profile postgres --profile monitoring --profile test-containers up"
echo ""
echo "🌐 Development URLs:"
echo "   Harbor:          http://localhost:8080"
echo "   Prometheus:      http://localhost:9090"
echo "   Grafana:         http://localhost:3000 (admin/dev_password_123)"
echo "   MailHog:         http://localhost:8025"
echo "   Test Registry:   http://localhost:5000"
echo ""
echo "💡 Use 'make help' for convenient development commands"
