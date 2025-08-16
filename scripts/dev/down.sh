#!/bin/bash
# =============================================================================
# Harbor Development Environment Shutdown
# Located: scripts/dev/down.sh
# Clean shutdown following project structure
# =============================================================================

set -e

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🛑 Shutting down Harbor development environment..."
echo "Following Harbor Project Structure from foundational documents"

# Stop all development services using proper paths
cd "$PROJECT_ROOT/deploy/docker"
docker-compose -f docker-compose.dev.yml --profile postgres --profile monitoring --profile test-containers --profile mail --profile registry down

echo "🧹 Cleaning up development containers..."

# Remove any dangling containers
docker container prune -f

echo "📊 Development environment status:"
docker ps -a | grep harbor-dev || echo "No Harbor development containers running"

echo "✅ Development environment shutdown complete!"
echo ""
echo "💾 Data volumes preserved:"
echo "   - harbor_dev_data"
echo "   - harbor_dev_logs"
echo "   - harbor_redis_dev_data"
echo "   - harbor_postgres_dev_data (if used)"
echo ""
echo "🗑️ To completely reset (delete all data):"
echo "   cd $PROJECT_ROOT/deploy/docker && docker-compose -f docker-compose.dev.yml down -v"
echo ""
echo "🔄 To restart:"
echo "   make dev-up          # Basic environment"
echo "   make dev-up-full     # Full environment"
