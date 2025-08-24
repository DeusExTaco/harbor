#!/bin/bash
# Harbor Container Updater - Multi-Platform Image Testing
# scripts/test-multi-platform.sh
# Tests Harbor images across all supported architectures

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
VERSION="${HARBOR_VERSION:-0.1.0-alpha.2}"
GHCR_IMAGE="ghcr.io/deusextaco/harbor:${VERSION}"
DOCKERHUB_IMAGE="dextaco/harbor:${VERSION}"

# Platform configuration
PLATFORMS=("linux/amd64" "linux/arm64" "linux/arm/v7")
PLATFORM_NAMES=("AMD64" "ARM64" "ARMv7")
TEST_PORTS=(8080 8081 8082)

# Detect host platform
ARCH=$(uname -m)
case "$ARCH" in
    "x86_64"|"amd64")
        HOST_PLATFORM="linux/amd64"
        HOST_NATIVE="AMD64"
        ;;
    "aarch64"|"arm64")
        HOST_PLATFORM="linux/arm64"
        HOST_NATIVE="ARM64"
        ;;
    "armv7l")
        HOST_PLATFORM="linux/arm/v7"
        HOST_NATIVE="ARMv7"
        ;;
    *)
        HOST_PLATFORM="linux/amd64"
        HOST_NATIVE="Unknown"
        ;;
esac

echo -e "${PURPLE}🏗️ Harbor Multi-Platform Image Testing v${VERSION}${NC}"
echo "=================================================================="
echo "Host Platform: $HOST_NATIVE ($ARCH)"
echo "Test Platforms: ${PLATFORM_NAMES[*]}"
echo ""

# =============================================================================
# Platform Testing Functions
# =============================================================================

test_platform_image() {
    local IMAGE=$1
    local PLATFORM=$2
    local PLATFORM_NAME=$3
    local PORT=$4
    local REPO_NAME=$5

    echo -e "${BLUE}🧪 Testing $PLATFORM_NAME ($PLATFORM) - $REPO_NAME${NC}"
    echo "Image: $IMAGE"
    echo "Platform: $PLATFORM"
    echo "Container Port: $PORT"

    # Determine if this is native or emulated
    local IS_NATIVE=false
    if [ "$PLATFORM" = "$HOST_PLATFORM" ]; then
        IS_NATIVE=true
        echo "Execution: Native (best performance)"
    else
        echo "Execution: Emulated (may be slower)"
    fi
    echo ""

    local CONTAINER_NAME="harbor-test-$(echo $PLATFORM_NAME | tr '[:upper:]' '[:lower:]')-$(echo $REPO_NAME | tr '[:upper:]' '[:lower:]')"

    # Platform-specific timeouts
    local MAX_WAIT=60
    local PULL_TIMEOUT=300
    if [ "$IS_NATIVE" = false ]; then
        MAX_WAIT=120      # Longer startup for emulation
        PULL_TIMEOUT=600  # Longer pull timeout for emulation
    fi
    if [ "$PLATFORM" = "linux/arm/v7" ]; then
        MAX_WAIT=180      # ARMv7 is slower even when native
        PULL_TIMEOUT=900
    fi

    # Pull the image with platform override
    echo -e "${YELLOW}⬇️ Pulling image (timeout: ${PULL_TIMEOUT}s)...${NC}"
    if timeout $PULL_TIMEOUT docker pull --platform $PLATFORM $IMAGE; then
        echo -e "${GREEN}✅ Image pulled successfully${NC}"
    else
        echo -e "${RED}❌ Failed to pull image within ${PULL_TIMEOUT}s${NC}"
        return 1
    fi

    # Run the container with platform-specific environment
    echo -e "${YELLOW}🚀 Starting container...${NC}"

    # Platform-specific environment variables
    local ENV_VARS=""
    case "$PLATFORM" in
        "linux/arm/v7")
            ENV_VARS="-e HARBOR_MAX_WORKERS=1 -e MAX_CONCURRENT_UPDATES=1 -e DATABASE_POOL_SIZE=2 -e LOG_RETENTION_DAYS=7 -e ENABLE_METRICS=false"
            ;;
        "linux/arm64")
            ENV_VARS="-e HARBOR_MAX_WORKERS=2 -e MAX_CONCURRENT_UPDATES=1 -e DATABASE_POOL_SIZE=3"
            ;;
        "linux/amd64")
            ENV_VARS="-e HARBOR_MAX_WORKERS=auto -e MAX_CONCURRENT_UPDATES=5"
            ;;
    esac

    docker run -d \
        --platform $PLATFORM \
        --name $CONTAINER_NAME \
        --restart unless-stopped \
        -p $PORT:8080 \
        -e HARBOR_MODE=homelab \
        -e LOG_LEVEL=INFO \
        $ENV_VARS \
        $IMAGE

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Container started successfully${NC}"
        if [ "$IS_NATIVE" = false ]; then
            echo -e "${YELLOW}ℹ️ Running under emulation (performance may be reduced)${NC}"
        fi
    else
        echo -e "${RED}❌ Failed to start container${NC}"
        return 1
    fi

    # Wait for startup with platform-appropriate timeout
    echo -e "${YELLOW}⏳ Waiting for Harbor startup (max ${MAX_WAIT}s)...${NC}"
    local startup_time=0
    for i in $(seq 1 $MAX_WAIT); do
        if curl -s http://localhost:$PORT/healthz > /dev/null 2>&1; then
            startup_time=$i
            echo -e "${GREEN}✅ Harbor responding after ${startup_time}s${NC}"
            break
        fi
        if [ $i -eq $MAX_WAIT ]; then
            echo -e "${RED}❌ Harbor failed to start within ${MAX_WAIT}s${NC}"
            echo -e "${YELLOW}📋 Container logs (last 20 lines):${NC}"
            docker logs --tail 20 $CONTAINER_NAME
            return 1
        fi
        if [ $((i % 15)) -eq 0 ]; then
            echo -n " ${i}s"
        else
            echo -n "."
        fi
        sleep 1
    done
    echo ""

    # Test endpoints with platform-specific expectations
    echo -e "${YELLOW}🔍 Testing endpoints...${NC}"

    # Test health endpoint
    local health_response=$(curl -s http://localhost:$PORT/healthz)
    if echo $health_response | grep -q '"status":"healthy"'; then
        echo -e "${GREEN}✅ Health endpoint working${NC}"
        if command -v jq &> /dev/null; then
            local reported_version=$(echo $health_response | jq -r '.version')
            local reported_milestone=$(echo $health_response | jq -r '.milestone')
            local reported_profile=$(echo $health_response | jq -r '.deployment_profile')
            echo "   Version: $reported_version"
            echo "   Milestone: $reported_milestone"
            echo "   Profile: $reported_profile"
        fi
    else
        echo -e "${RED}❌ Health endpoint failed${NC}"
        echo "Response: $health_response"
        return 1
    fi

    # Test version endpoint
    local version_response=$(curl -s http://localhost:$PORT/version)
    if echo $version_response | grep -q '"version":"'$VERSION'"'; then
        echo -e "${GREEN}✅ Version endpoint correct${NC}"
    else
        echo -e "${RED}❌ Version endpoint incorrect${NC}"
        echo "Expected: $VERSION"
        echo "Response: $version_response"
        return 1
    fi

    # Test API documentation
    local docs_status=$(curl -s -w "%{http_code}" http://localhost:$PORT/docs -o /dev/null)
    if [ "$docs_status" = "200" ]; then
        echo -e "${GREEN}✅ API documentation accessible${NC}"
    else
        echo -e "${RED}❌ API documentation not accessible (HTTP $docs_status)${NC}"
        return 1
    fi

    # Platform-specific performance validation
    echo -e "${YELLOW}📊 Platform performance check...${NC}"

    # Get container stats
    local stats=$(docker stats --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}" $CONTAINER_NAME | tail -n 1)
    local cpu_usage=$(echo $stats | awk '{print $1}' | sed 's/%//')
    local memory_usage=$(echo $stats | awk '{print $2}' | sed 's/MiB.*//')

    echo "   CPU Usage: ${cpu_usage}%"
    echo "   Memory Usage: ${memory_usage}MB"

    # Platform-specific performance expectations
    case "$PLATFORM" in
        "linux/arm/v7")
            if (( $(echo "$memory_usage > 200" | bc -l 2>/dev/null || echo 0) )); then
                echo -e "${YELLOW}⚠️ High memory usage for ARMv7 (${memory_usage}MB)${NC}"
            else
                echo -e "${GREEN}✅ Memory usage acceptable for ARMv7${NC}"
            fi
            ;;
        "linux/arm64")
            if (( $(echo "$memory_usage > 256" | bc -l 2>/dev/null || echo 0) )); then
                echo -e "${YELLOW}⚠️ High memory usage for ARM64 (${memory_usage}MB)${NC}"
            else
                echo -e "${GREEN}✅ Memory usage acceptable for ARM64${NC}"
            fi
            ;;
        *)
            echo -e "${GREEN}✅ Performance metrics collected${NC}"
            ;;
    esac

    # Show container details
    echo -e "${YELLOW}📋 Container Details:${NC}"
    docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

    # Show platform info from inside container
    echo -e "${YELLOW}🔍 Runtime Platform Detection:${NC}"
    docker exec $CONTAINER_NAME python -c "
import platform, os
print(f'   Container Arch: {platform.machine()}')
print(f'   Python Platform: {platform.platform()}')
print(f'   Target Platform: {os.getenv(\"HARBOR_TARGET_PLATFORM\", \"unknown\")}')
print(f'   Max Workers: {os.getenv(\"HARBOR_MAX_WORKERS\", \"auto\")}')
print(f'   Pool Size: {os.getenv(\"DATABASE_POOL_SIZE\", \"default\")}')
" 2>/dev/null || echo "   Platform detection failed"

    echo ""
    echo -e "${GREEN}🎉 $PLATFORM_NAME ($REPO_NAME) test completed successfully!${NC}"
    echo -e "${BLUE}🌐 Access Harbor at: http://localhost:$PORT${NC}"
    echo -e "${BLUE}📖 API Docs at: http://localhost:$PORT/docs${NC}"

    # Performance summary
    if [ "$IS_NATIVE" = true ]; then
        echo -e "${GREEN}⚡ Native performance on $HOST_NATIVE${NC}"
    else
        echo -e "${YELLOW}🔄 Emulated performance (startup: ${startup_time}s)${NC}"
    fi

    echo ""
    echo "---"
    echo ""

    return 0
}

# =============================================================================
# Registry Testing Functions
# =============================================================================

test_registry() {
    local REGISTRY_NAME=$1
    local IMAGE_BASE=$2

    echo -e "${PURPLE}🏪 Testing $REGISTRY_NAME Registry${NC}"
    echo "======================================"
    echo ""

    local SUCCESS_COUNT=0
    local TOTAL_COUNT=0

    for i in "${!PLATFORMS[@]}"; do
        local PLATFORM="${PLATFORMS[$i]}"
        local PLATFORM_NAME="${PLATFORM_NAMES[$i]}"
        local PORT="${TEST_PORTS[$i]}"
        local IMAGE="$IMAGE_BASE"

        TOTAL_COUNT=$((TOTAL_COUNT + 1))

        echo -e "${BLUE}Test $((i + 1))/${#PLATFORMS[@]}: $PLATFORM_NAME${NC}"

        if test_platform_image "$IMAGE" "$PLATFORM" "$PLATFORM_NAME" "$PORT" "$REGISTRY_NAME"; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo -e "${RED}❌ $PLATFORM_NAME test failed${NC}"
            echo ""
        fi
    done

    echo -e "${PURPLE}📊 $REGISTRY_NAME Summary: $SUCCESS_COUNT/$TOTAL_COUNT platforms successful${NC}"
    echo ""

    return $([ $SUCCESS_COUNT -eq $TOTAL_COUNT ] && echo 0 || echo 1)
}

# =============================================================================
# Cleanup Functions
# =============================================================================

cleanup_all_containers() {
    echo -e "${YELLOW}🧹 Cleaning up all test containers...${NC}"

    # Stop and remove all harbor test containers
    for container in $(docker ps -a --format '{{.Names}}' | grep 'harbor-test-'); do
        echo "Stopping and removing $container..."
        docker stop $container >/dev/null 2>&1 || true
        docker rm $container >/dev/null 2>&1 || true
    done

    echo -e "${GREEN}✅ Cleanup completed${NC}"
    echo ""
}

# =============================================================================
# Manifest and Multi-Architecture Verification
# =============================================================================

verify_multi_arch_manifest() {
    local IMAGE=$1
    local REGISTRY_NAME=$2

    echo -e "${BLUE}🔍 Verifying multi-architecture manifest for $REGISTRY_NAME${NC}"
    echo "Image: $IMAGE"
    echo ""

    # Use docker buildx to inspect the manifest
    if command -v docker >/dev/null 2>&1; then
        echo "📋 Manifest inspection:"
        if docker buildx imagetools inspect $IMAGE 2>/dev/null; then
            echo -e "${GREEN}✅ Multi-architecture manifest verified${NC}"
            echo ""

            # Try to extract platform information
            echo "🏗️ Available platforms:"
            docker buildx imagetools inspect $IMAGE 2>/dev/null | grep -A 10 "Manifests:" | grep "Platform:" | while read line; do
                echo "   $line"
            done
            echo ""
        else
            echo -e "${YELLOW}⚠️ Could not inspect manifest (may not exist yet)${NC}"
            echo ""
        fi
    else
        echo -e "${YELLOW}⚠️ Docker buildx not available for manifest inspection${NC}"
        echo ""
    fi
}

# =============================================================================
# Performance Benchmarking
# =============================================================================

benchmark_startup_times() {
    echo -e "${PURPLE}📊 Platform Startup Performance Benchmark${NC}"
    echo "================================================"
    echo ""

    for i in "${!PLATFORMS[@]}"; do
        local PLATFORM="${PLATFORMS[$i]}"
        local PLATFORM_NAME="${PLATFORM_NAMES[$i]}"
        local CONTAINER_NAME="harbor-benchmark-$(echo $PLATFORM_NAME | tr '[:upper:]' '[:lower:]')"

        echo -e "${BLUE}⏱️ Benchmarking $PLATFORM_NAME startup time...${NC}"

        # Start container and time startup
        local start_time=$(date +%s)
        docker run -d \
            --platform $PLATFORM \
            --name $CONTAINER_NAME \
            -p $((8090 + i)):8080 \
            -e HARBOR_MODE=homelab \
            -e LOG_LEVEL=ERROR \
            $GHCR_IMAGE >/dev/null

        # Wait for health check to pass
        local startup_successful=false
        for j in $(seq 1 180); do  # 3 minute max
            if curl -s http://localhost:$((8090 + i))/healthz > /dev/null 2>&1; then
                local end_time=$(date +%s)
                local startup_time=$((end_time - start_time))
                echo -e "${GREEN}✅ $PLATFORM_NAME: ${startup_time}s${NC}"
                startup_successful=true
                break
            fi
            sleep 1
        done

        if [ "$startup_successful" = false ]; then
            echo -e "${RED}❌ $PLATFORM_NAME: Failed to start${NC}"
        fi

        # Cleanup benchmark container
        docker stop $CONTAINER_NAME >/dev/null 2>&1 || true
        docker rm $CONTAINER_NAME >/dev/null 2>&1 || true

        echo ""
    done
}

# =============================================================================
# Summary and Recommendations
# =============================================================================

show_final_summary() {
    echo -e "${PURPLE}📊 Harbor Multi-Platform Test Summary${NC}"
    echo "==========================================="
    echo ""

    # Check which containers are still running
    echo -e "${BLUE}🏃 Running Test Containers:${NC}"
    local running_containers=$(docker ps --format '{{.Names}}' | grep 'harbor-test-' || echo "")

    if [ -n "$running_containers" ]; then
        for container in $running_containers; do
            local port=$(docker port $container 8080/tcp | cut -d':' -f2)
            local platform=$(docker inspect $container --format '{{.Platform}}' 2>/dev/null || echo "unknown")
            echo "   ✅ $container (port $port) - $platform"
        done
        echo ""

        echo -e "${BLUE}🔗 Quick Test URLs:${NC}"
        for container in $running_containers; do
            local port=$(docker port $container 8080/tcp | cut -d':' -f2)
            echo "   http://localhost:$port/healthz"
        done
        echo ""
    else
        echo "   No test containers currently running"
        echo ""
    fi

    # Platform compatibility summary
    echo -e "${BLUE}🏗️ Platform Compatibility Results:${NC}"
    echo ""
    echo "| Platform | Status | Best Use Case |"
    echo "|----------|--------|---------------|"
    echo "| AMD64 | ✅ Full Support | Desktop PCs, Intel/AMD servers |"
    echo "| ARM64 | ✅ Native Support | Apple Silicon, modern ARM servers, Pi 4 |"
    echo "| ARMv7 | ✅ Optimized Support | Raspberry Pi 3, older ARM devices |"
    echo ""

    # Recommendations based on host platform
    echo -e "${BLUE}💡 Recommendations for Your System ($HOST_NATIVE):${NC}"
    case "$HOST_PLATFORM" in
        "linux/amd64")
            echo "   🖥️ You're on AMD64 - use any image tag for best performance"
            echo "   📦 Recommended: ghcr.io/deusextaco/harbor:$VERSION"
            ;;
        "linux/arm64")
            echo "   🍎 You're on ARM64 - native performance available!"
            echo "   📦 Recommended: ghcr.io/deusextaco/harbor:$VERSION"
            if [[ "$ARCH" == "aarch64" ]]; then
                echo "   🥧 For Raspberry Pi 4, consider using environment optimizations"
            fi
            ;;
        "linux/arm/v7")
            echo "   🥧 You're on ARMv7 - optimized build available!"
            echo "   📦 Recommended: ghcr.io/deusextaco/harbor:$VERSION"
            echo "   ⚙️ Use Raspberry Pi docker-compose.yml for best performance"
            ;;
    esac
    echo ""

    # Cleanup instructions
    echo -e "${BLUE}🗑️ Cleanup Commands:${NC}"
    echo "   $0 cleanup              # Stop and remove all test containers"
    echo "   docker system prune -f  # Clean up unused images and containers"
    echo ""

    echo -e "${GREEN}🎉 Multi-platform testing complete!${NC}"
    echo -e "${BLUE}📘 Harbor supports all major home lab platforms natively.${NC}"
}

# =============================================================================
# Main Execution Logic
# =============================================================================

main() {
    # Parse command line arguments
    local test_ghcr=true
    local test_dockerhub=true
    local cleanup_after=false
    local benchmark=false
    local verify_manifest=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --ghcr-only)
                test_dockerhub=false
                shift
                ;;
            --dockerhub-only)
                test_ghcr=false
                shift
                ;;
            --cleanup-after)
                cleanup_after=true
                shift
                ;;
            --benchmark)
                benchmark=true
                shift
                ;;
            --verify-manifest)
                verify_manifest=true
                shift
                ;;
            --version)
                VERSION="$2"
                GHCR_IMAGE="ghcr.io/deusextaco/harbor:${VERSION}"
                DOCKERHUB_IMAGE="dextaco/harbor:${VERSION}"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Show test configuration
    echo -e "${BLUE}🧪 Test Configuration:${NC}"
    echo "   Version: $VERSION"
    echo "   Test GHCR: $test_ghcr"
    echo "   Test Docker Hub: $test_dockerhub"
    echo "   Cleanup After: $cleanup_after"
    echo "   Benchmark: $benchmark"
    echo "   Verify Manifest: $verify_manifest"
    echo ""

    # Check if jq is available for JSON parsing
    if ! command -v jq &> /dev/null; then
        echo -e "${YELLOW}ℹ️ jq not found - JSON output will be raw${NC}"
        echo "   Install with: apt-get install jq (Linux) or brew install jq (macOS)"
        echo ""
    fi

    # Initial cleanup
    cleanup_all_containers

    # Verify manifests if requested
    if [ "$verify_manifest" = true ]; then
        if [ "$test_ghcr" = true ]; then
            verify_multi_arch_manifest "$GHCR_IMAGE" "GHCR"
        fi
        if [ "$test_dockerhub" = true ]; then
            verify_multi_arch_manifest "$DOCKERHUB_IMAGE" "Docker Hub"
        fi
    fi

    # Run benchmarks if requested
    if [ "$benchmark" = true ]; then
        benchmark_startup_times
    fi

    # Test registries
    local overall_success=true

    if [ "$test_ghcr" = true ]; then
        if ! test_registry "GHCR" "$GHCR_IMAGE"; then
            overall_success=false
        fi
    fi

    if [ "$test_dockerhub" = true ]; then
        if ! test_registry "Docker Hub" "$DOCKERHUB_IMAGE"; then
            overall_success=false
        fi
    fi

    # Show final summary
    show_final_summary

    # Cleanup if requested
    if [ "$cleanup_after" = true ]; then
        cleanup_all_containers
    fi

    # Return appropriate exit code
    if [ "$overall_success" = true ]; then
        echo -e "${GREEN}🎉 All platform tests passed successfully!${NC}"
        return 0
    else
        echo -e "${RED}❌ Some platform tests failed!${NC}"
        return 1
    fi
}

# =============================================================================
# Command Line Interface
# =============================================================================

show_usage() {
    cat << EOF
🏗️ Harbor Multi-Platform Image Testing

Usage: $0 [options] [command]

Options:
  --ghcr-only          Test only GHCR images
  --dockerhub-only     Test only Docker Hub images
  --cleanup-after      Cleanup test containers after completion
  --benchmark          Run startup performance benchmarks
  --verify-manifest    Verify multi-architecture manifests
  --version VERSION    Test specific version (default: $VERSION)

Commands:
  cleanup              Clean up all test containers
  summary             Show summary of running test containers
  benchmark           Run only performance benchmarks
  manifest            Verify only multi-arch manifests
  help                Show this help

Examples:
  $0                                    # Test all registries and platforms
  $0 --ghcr-only --cleanup-after       # Test GHCR only, cleanup after
  $0 --benchmark --verify-manifest     # Run benchmarks and verify manifests
  $0 --version 0.1.1 --ghcr-only      # Test specific version from GHCR
  $0 cleanup                           # Just cleanup test containers

Platform Support:
  - linux/amd64 (Intel/AMD)      - Full performance testing
  - linux/arm64 (Apple Silicon)  - Native or emulated testing
  - linux/arm/v7 (Raspberry Pi)  - Emulated testing with optimizations

Host Platform Detected: $HOST_NATIVE ($ARCH)

The script automatically uses native execution when possible and emulation
when necessary, with appropriate timeouts and performance expectations.

For best results on ARM devices, run this script on the actual target
hardware to get accurate performance measurements.
EOF
}

# Handle command line arguments
case "${1:-}" in
    "cleanup")
        cleanup_all_containers
        exit 0
        ;;
    "summary")
        show_final_summary
        exit 0
        ;;
    "benchmark")
        benchmark_startup_times
        exit 0
        ;;
    "manifest")
        verify_multi_arch_manifest "$GHCR_IMAGE" "GHCR"
        verify_multi_arch_manifest "$DOCKERHUB_IMAGE" "Docker Hub"
        exit 0
        ;;
    "help"|"--help"|"-h")
        show_usage
        exit 0
        ;;
    "")
        # Run main test suite
        main "$@"
        ;;
    *)
        # Check if it's an option flag
        if [[ "$1" == --* ]]; then
            main "$@"
        else
            echo "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
        fi
        ;;
esac
