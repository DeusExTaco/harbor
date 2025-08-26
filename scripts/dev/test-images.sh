#!/bin/bash
# Harbor Container Updater - Test Published Images (Apple Silicon Fixed)
# Tests images from both GHCR and Docker Hub repositories with platform override

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
VERSION="0.1.0-alpha.2"
GHCR_IMAGE="ghcr.io/deusextaco/harbor:${VERSION}"
DOCKERHUB_IMAGE="dextaco/harbor:${VERSION}"
TEST_PORT_GHCR="8080"
TEST_PORT_DOCKERHUB="8081"

# Detect platform and set Docker platform override
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    echo -e "${YELLOW}🍎 Detected Apple Silicon (ARM64) - using platform override${NC}"
    DOCKER_PLATFORM="--platform linux/amd64"
    PLATFORM_NOTE="(emulated x64 on ARM64)"
else
    echo -e "${BLUE}🖥️  Detected x86_64 architecture${NC}"
    DOCKER_PLATFORM=""
    PLATFORM_NOTE=""
fi

echo -e "${BLUE}🧪 Testing Harbor Published Images v${VERSION} ${PLATFORM_NOTE}${NC}"
echo "================================================="
echo ""

# Function to test an image
test_image() {
    local IMAGE=$1
    local CONTAINER_NAME=$2
    local PORT=$3
    local REPO_NAME=$4

    echo -e "${BLUE}📦 Testing $REPO_NAME Image${NC}"
    echo "Image: $IMAGE"
    echo "Container: $CONTAINER_NAME"
    echo "Port: $PORT"
    if [[ -n "$DOCKER_PLATFORM" ]]; then
        echo "Platform: $DOCKER_PLATFORM $PLATFORM_NOTE"
    fi
    echo ""

    # Pull the image with platform override if needed
    echo -e "${YELLOW}⬇️  Pulling image...${NC}"
    if docker pull $DOCKER_PLATFORM $IMAGE; then
        echo -e "${GREEN}✅ Image pulled successfully${NC}"
    else
        echo -e "${RED}❌ Failed to pull image${NC}"
        return 1
    fi
    echo ""

    # Run the container with platform override if needed
    echo -e "${YELLOW}🚀 Starting container...${NC}"
    docker run -d \
        $DOCKER_PLATFORM \
        --name $CONTAINER_NAME \
        --restart unless-stopped \
        -p $PORT:8080 \
        -e HARBOR_MODE=homelab \
        -e LOG_LEVEL=INFO \
        $IMAGE

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Container started successfully${NC}"
        if [[ -n "$DOCKER_PLATFORM" ]]; then
            echo -e "${YELLOW}ℹ️  Running under emulation (may be slower)${NC}"
        fi
    else
        echo -e "${RED}❌ Failed to start container${NC}"
        return 1
    fi
    echo ""

    # Wait for startup (longer timeout for emulated containers)
    local MAX_WAIT=60
    if [[ -n "$DOCKER_PLATFORM" ]]; then
        MAX_WAIT=90  # Give emulated containers more time
    fi

    echo -e "${YELLOW}⏳ Waiting for Harbor to start (max ${MAX_WAIT}s)...${NC}"
    for i in $(seq 1 $MAX_WAIT); do
        if curl -s http://localhost:$PORT/healthz > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Harbor is responding (${i}s)${NC}"
            break
        fi
        if [ $i -eq $MAX_WAIT ]; then
            echo -e "${RED}❌ Harbor failed to start within ${MAX_WAIT} seconds${NC}"
            echo -e "${YELLOW}📝 Container logs:${NC}"
            docker logs $CONTAINER_NAME
            return 1
        fi
        if [ $((i % 10)) -eq 0 ]; then
            echo -n " ${i}s"
        else
            echo -n "."
        fi
        sleep 1
    done
    echo ""

    # Test health endpoint
    echo -e "${YELLOW}❤️  Testing health endpoint...${NC}"
    HEALTH_RESPONSE=$(curl -s http://localhost:$PORT/healthz)
    if echo $HEALTH_RESPONSE | grep -q '"status":"healthy"'; then
        echo -e "${GREEN}✅ Health check passed${NC}"
        if command -v jq &> /dev/null; then
            echo "Status: $(echo $HEALTH_RESPONSE | jq -r '.status')"
            echo "Version: $(echo $HEALTH_RESPONSE | jq -r '.version')"
            echo "Milestone: $(echo $HEALTH_RESPONSE | jq -r '.milestone')"
            echo "Profile: $(echo $HEALTH_RESPONSE | jq -r '.deployment_profile')"
        else
            echo "Response: $HEALTH_RESPONSE"
        fi
    else
        echo -e "${RED}❌ Health check failed${NC}"
        echo "Response: $HEALTH_RESPONSE"
        return 1
    fi
    echo ""

    # Test version endpoint
    echo -e "${YELLOW}📋 Testing version endpoint...${NC}"
    VERSION_RESPONSE=$(curl -s http://localhost:$PORT/version)
    if echo $VERSION_RESPONSE | grep -q '"version":"'$VERSION'"'; then
        echo -e "${GREEN}✅ Version endpoint correct${NC}"
        if command -v jq &> /dev/null; then
            echo "Version: $(echo $VERSION_RESPONSE | jq -r '.version')"
            echo "Milestone: $(echo $VERSION_RESPONSE | jq -r '.milestone')"
            echo "Status: $(echo $VERSION_RESPONSE | jq -r '.status')"
        else
            echo "Response: $VERSION_RESPONSE"
        fi
    else
        echo -e "${RED}❌ Version endpoint incorrect${NC}"
        echo "Expected version: $VERSION"
        echo "Response: $VERSION_RESPONSE"
        return 1
    fi
    echo ""

    # Test root endpoint
    echo -e "${YELLOW}🏠 Testing root endpoint...${NC}"
    ROOT_RESPONSE=$(curl -s http://localhost:$PORT/)
    if echo $ROOT_RESPONSE | grep -q 'Harbor Container Updater'; then
        echo -e "${GREEN}✅ Root endpoint working${NC}"
        if command -v jq &> /dev/null; then
            echo "Name: $(echo $ROOT_RESPONSE | jq -r '.name')"
        fi
    else
        echo -e "${RED}❌ Root endpoint failed${NC}"
        echo "Response: $ROOT_RESPONSE"
        return 1
    fi
    echo ""

    # Test OpenAPI docs
    echo -e "${YELLOW}📚 Testing OpenAPI documentation...${NC}"
    DOCS_RESPONSE=$(curl -s -w "%{http_code}" http://localhost:$PORT/docs -o /dev/null)
    if [ "$DOCS_RESPONSE" = "200" ]; then
        echo -e "${GREEN}✅ OpenAPI docs accessible${NC}"
        echo "Docs available at: http://localhost:$PORT/docs"
    else
        echo -e "${RED}❌ OpenAPI docs not accessible (HTTP $DOCS_RESPONSE)${NC}"
    fi
    echo ""

    # Show container info
    echo -e "${YELLOW}📊 Container Information:${NC}"
    docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""

    # Show brief startup logs
    echo -e "${YELLOW}📝 Container startup logs (last 5 lines):${NC}"
    docker logs --tail 5 $CONTAINER_NAME 2>/dev/null || echo "No logs available"
    echo ""

    echo -e "${GREEN}🎉 $REPO_NAME image test completed successfully!${NC}"
    echo -e "${BLUE}🌐 Access Harbor at: http://localhost:$PORT${NC}"
    echo -e "${BLUE}📖 API Docs at: http://localhost:$PORT/docs${NC}"
    echo ""
    echo "---"
    echo ""

    return 0
}

# Function to cleanup containers
cleanup_containers() {
    echo -e "${YELLOW}🧹 Cleaning up test containers...${NC}"

    for container in harbor-test-ghcr harbor-test-dockerhub; do
        if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
            echo "Stopping and removing $container..."
            docker stop $container >/dev/null 2>&1 || true
            docker rm $container >/dev/null 2>&1 || true
        fi
    done

    echo -e "${GREEN}✅ Cleanup completed${NC}"
    echo ""
}

# Function to show final summary
show_summary() {
    echo -e "${BLUE}📊 Test Summary${NC}"
    echo "==============="
    echo ""

    # Check if containers are running
    if docker ps --format '{{.Names}}' | grep -q "harbor-test-ghcr"; then
        echo -e "${GREEN}✅ GHCR Image: Working${NC}"
        echo "   🔗 http://localhost:$TEST_PORT_GHCR"
        echo "   📖 http://localhost:$TEST_PORT_GHCR/docs"
    else
        echo -e "${RED}❌ GHCR Image: Failed${NC}"
    fi

    if docker ps --format '{{.Names}}' | grep -q "harbor-test-dockerhub"; then
        echo -e "${GREEN}✅ Docker Hub Image: Working${NC}"
        echo "   🔗 http://localhost:$TEST_PORT_DOCKERHUB"
        echo "   📖 http://localhost:$TEST_PORT_DOCKERHUB/docs"
    else
        echo -e "${RED}❌ Docker Hub Image: Failed${NC}"
    fi

    echo ""
    echo -e "${BLUE}🎯 Quick Test Commands:${NC}"
    echo "curl http://localhost:$TEST_PORT_GHCR/healthz       # GHCR health"
    echo "curl http://localhost:$TEST_PORT_DOCKERHUB/healthz  # Docker Hub health"
    echo ""
    echo -e "${BLUE}🗑️  Cleanup when done:${NC}"
    cleanup_containers
}

# Main execution
main() {
    # Check if jq is available for JSON parsing
    if ! command -v jq &> /dev/null; then
        echo -e "${YELLOW}ℹ️  jq not found - JSON output will be raw${NC}"
        if [[ "$ARCH" == "arm64" ]]; then
            echo "Install with: brew install jq"
        fi
        echo ""
    fi

    # Cleanup any existing test containers
    cleanup_containers

    # Test GHCR image
    echo -e "${BLUE}🧪 Test 1/2: GitHub Container Registry (GHCR)${NC}"
    echo "=============================================="
    if test_image $GHCR_IMAGE "harbor-test-ghcr" $TEST_PORT_GHCR "GHCR"; then
        GHCR_SUCCESS=true
    else
        GHCR_SUCCESS=false
        echo -e "${RED}❌ GHCR image test failed${NC}"
        echo ""
    fi

    # Test Docker Hub image
    echo -e "${BLUE}🧪 Test 2/2: Docker Hub${NC}"
    echo "====================="
    if test_image $DOCKERHUB_IMAGE "harbor-test-dockerhub" $TEST_PORT_DOCKERHUB "Docker Hub"; then
        DOCKERHUB_SUCCESS=true
    else
        DOCKERHUB_SUCCESS=false
        echo -e "${RED}❌ Docker Hub image test failed${NC}"
        echo ""
    fi

    # Show final summary
    show_summary

    # Final result
    if [ "$GHCR_SUCCESS" = true ] && [ "$DOCKERHUB_SUCCESS" = true ]; then
        echo -e "${GREEN}🎉 All tests passed! Both repositories are working perfectly.${NC}"
        echo ""
        if [[ -n "$DOCKER_PLATFORM" ]]; then
            echo -e "${YELLOW}ℹ️  Images running under x64 emulation on Apple Silicon${NC}"
            echo -e "${YELLOW}ℹ️  For native ARM64 support, enable multi-arch builds in CI/CD${NC}"
            echo ""
        fi
        echo -e "${BLUE}🚀 Harbor v${VERSION} is ready for use!${NC}"
        return 0
    else
        echo -e "${RED}❌ Some tests failed. Check the output above for details.${NC}"
        return 1
    fi
}

# Handle script arguments
case "${1:-}" in
    "cleanup")
        cleanup_containers
        exit 0
        ;;
    "summary")
        show_summary
        exit 0
        ;;
    "help"|"--help"|"-h")
        echo "Harbor Image Test Script (Apple Silicon Compatible)"
        echo ""
        echo "This script automatically detects Apple Silicon and uses platform override."
        echo ""
        echo "Usage:"
        echo "  $0          # Run full test suite"
        echo "  $0 cleanup  # Clean up test containers"
        echo "  $0 summary  # Show test summary"
        echo "  $0 help     # Show this help"
        echo ""
        echo "Platform Detection:"
        echo "  - Apple Silicon (ARM64): Uses --platform linux/amd64 override"
        echo "  - Intel/AMD (x86_64): Uses native platform"
        exit 0
        ;;
    "")
        # Run main test suite
        main
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
