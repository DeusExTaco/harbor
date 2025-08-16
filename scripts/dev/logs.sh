#!/bin/bash
# =============================================================================
# Harbor Development Logs Viewer
# Located: scripts/dev/logs.sh
# View development logs following project structure
# =============================================================================

set -e

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/deploy/docker/docker-compose.dev.yml"

# Function to show usage
show_usage() {
    echo "Usage: $0 [service] [options]"
    echo ""
    echo "Services:"
    echo "  harbor     - Harbor main application (default)"
    echo "  redis      - Redis cache"
    echo "  postgres   - PostgreSQL database"
    echo "  prometheus - Prometheus metrics"
    echo "  grafana    - Grafana visualization"
    echo "  mailhog    - MailHog email testing"
    echo "  registry   - Test registry"
    echo "  all        - All services"
    echo ""
    echo "Options:"
    echo "  -f, --follow    Follow log output"
    echo "  -t, --tail N    Show last N lines (default: 100)"
    echo ""
    echo "Examples:"
    echo "  $0 harbor -f           # Follow Harbor logs"
    echo "  $0 redis --tail 50     # Last 50 lines of Redis logs"
    echo "  $0 all                 # All service logs"
}

# Default values
SERVICE="harbor"
FOLLOW=false
TAIL_LINES=100

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        harbor|redis|postgres|prometheus|grafana|mailhog|registry|all)
            SERVICE="$1"
            shift
            ;;
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -t|--tail)
            TAIL_LINES="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Build docker-compose command
COMPOSE_CMD="cd $PROJECT_ROOT/deploy/docker && docker-compose -f docker-compose.dev.yml logs"

if [ "$FOLLOW" = true ]; then
    COMPOSE_CMD="$COMPOSE_CMD -f"
fi

COMPOSE_CMD="$COMPOSE_CMD --tail=$TAIL_LINES"

# Map service names to container names
case $SERVICE in
    harbor)
        COMPOSE_CMD="$COMPOSE_CMD harbor-dev"
        ;;
    redis)
        COMPOSE_CMD="$COMPOSE_CMD redis-dev"
        ;;
    postgres)
        COMPOSE_CMD="$COMPOSE_CMD postgres-dev"
        ;;
    prometheus)
        COMPOSE_CMD="$COMPOSE_CMD prometheus-dev"
        ;;
    grafana)
        COMPOSE_CMD="$COMPOSE_CMD grafana-dev"
        ;;
    mailhog)
        COMPOSE_CMD="$COMPOSE_CMD mailhog-dev"
        ;;
    registry)
        COMPOSE_CMD="$COMPOSE_CMD registry-dev"
        ;;
    all)
        # Don't specify service name to get all
        ;;
    *)
        echo "Unknown service: $SERVICE"
        show_usage
        exit 1
        ;;
esac

echo "📋 Viewing logs for: $SERVICE"
echo "Using compose file: $DOCKER_COMPOSE_FILE"
echo ""

# Execute the command
eval $COMPOSE_CMD
