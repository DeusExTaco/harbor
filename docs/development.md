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

This development setup follows the Harbor Project Structure from the
foundational documents:

- `deploy/docker/` - Docker deployment files
- `config/` - Configuration files
- `examples/` - Example deployments
- `scripts/dev/` - Development scripts
- `tests/fixtures/` - Test data

## Development URLs

- Harbor: <http://localhost:8080>
- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000>
- MailHog: <http://localhost:8025>
- Test Registry: <http://localhost:5000>
