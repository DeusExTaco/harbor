#!/bin/bash
# Harbor Container Updater - Platform-Aware Development Setup
# scripts/dev/setup-platform.sh
# Configures development environment based on detected platform

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}🔍 Harbor Platform-Aware Development Setup${NC}"
echo "=============================================="
echo ""

# Detect platform
ARCH=$(uname -m)
OS=$(uname -s)

case "$ARCH" in
    "x86_64"|"amd64")
        PLATFORM_TYPE="amd64"
        PLATFORM_NAME="AMD64"
        EMOJI="🖥️"
        DESCRIPTION="Intel/AMD processors"
        COMPOSE_PROFILE="amd64"
        ;;
    "aarch64"|"arm64")
        PLATFORM_TYPE="arm64"
        PLATFORM_NAME="ARM64"
        EMOJI="🎯"
        DESCRIPTION="Apple Silicon, Pi 4, ARM servers"
        COMPOSE_PROFILE="arm64"
        ;;
    "armv7l")
        PLATFORM_TYPE="armv7"
        PLATFORM_NAME="ARMv7"
        EMOJI="🥧"
        DESCRIPTION="Raspberry Pi 3, older ARM"
        COMPOSE_PROFILE="armv7"
        ;;
    *)
        PLATFORM_TYPE="unknown"
        PLATFORM_NAME="Unknown"
        EMOJI="❓"
        DESCRIPTION="Unknown architecture"
        COMPOSE_PROFILE="amd64"
        ;;
esac

echo -e "${BLUE}$EMOJI Platform Detected: $PLATFORM_NAME ($ARCH)${NC}"
echo "Description: $DESCRIPTION"
echo "OS: $OS"
echo ""

# Create platform-specific development environment
echo -e "${YELLOW}⚙️ Configuring development environment for $PLATFORM_NAME...${NC}"

# Create platform-specific .env file for development
DEV_ENV_FILE=".env.development.platform"

cat > "$DEV_ENV_FILE" << EOF
# Platform-specific development environment
# Generated for: $PLATFORM_NAME ($ARCH)
# Date: $(date)

HARBOR_MODE=development
LOG_LEVEL=DEBUG
HARBOR_TARGET_PLATFORM=linux/$PLATFORM_TYPE

EOF

# Add platform-specific optimizations
case "$PLATFORM_TYPE" in
    "amd64")
        cat >> "$DEV_ENV_FILE" << EOF
# AMD64 Development Optimizations
HARBOR_MAX_WORKERS=auto
MAX_CONCURRENT_UPDATES=3
DATABASE_POOL_SIZE=5
LOG_RETENTION_DAYS=14
ENABLE_METRICS=true
ENABLE_ALL_FEATURES=true

EOF
        echo -e "${GREEN}✅ AMD64: Full development environment configured${NC}"
        echo "   - All features enabled"
        echo "   - Auto-scaled workers"
        echo "   - Full logging and metrics"
        ;;

    "arm64")
        cat >> "$DEV_ENV_FILE" << EOF
# ARM64 Development Optimizations
HARBOR_MAX_WORKERS=2
MAX_CONCURRENT_UPDATES=1
DATABASE_POOL_SIZE=3
LOG_RETENTION_DAYS=7
ENABLE_METRICS=true
REGISTRY_TIMEOUT=45

EOF
        echo -e "${GREEN}✅ ARM64: Balanced development environment configured${NC}"
        echo "   - Balanced resource usage"
        echo "   - Sequential updates for safety"
        echo "   - All features enabled"

        # Special message for Apple Silicon
        if [[ "$OS" == "Darwin" ]]; then
            echo -e "${BLUE}🍎 Apple Silicon Detected:${NC}"
            echo "   - Native ARM64 performance available"
            echo "   - Docker Desktop ARM64 mode recommended"
        fi
        ;;

    "armv7")
        cat >> "$DEV_ENV_FILE" << EOF
# ARMv7 Development Optimizations (Raspberry Pi 3)
HARBOR_MAX_WORKERS=1
MAX_CONCURRENT_UPDATES=1
DATABASE_POOL_SIZE=2
LOG_RETENTION_DAYS=3
ENABLE_METRICS=false
REGISTRY_TIMEOUT=60
PYTHONOPTIMIZE=1

EOF
        echo -e "${GREEN}✅ ARMv7: Memory-optimized development environment configured${NC}"
        echo "   - Single worker to conserve memory"
        echo "   - Metrics disabled to reduce overhead"
        echo "   - Extended timeouts for slower operations"
        echo -e "${YELLOW}💡 Raspberry Pi 3 detected - consider using Pi 4 for better performance${NC}"
        ;;

    *)
        cat >> "$DEV_ENV_FILE" << EOF
# Unknown Platform - Conservative Settings
HARBOR_MAX_WORKERS=1
MAX_CONCURRENT_UPDATES=1
DATABASE_POOL_SIZE=3
LOG_RETENTION_DAYS=7
ENABLE_METRICS=true

EOF
        echo -e "${YELLOW}⚠️ Unknown platform: Using conservative settings${NC}"
        ;;
esac

# Check available resources
echo -e "${BLUE}📊 System Resources:${NC}"

# Memory check
if command -v free >/dev/null 2>&1; then
    TOTAL_MEM_GB=$(free -g | awk '/^Mem:/{print $2}')
    AVAIL_MEM_GB=$(free -g | awk '/^Mem:/{print $7}')
    echo "   RAM: ${AVAIL_MEM_GB}GB available / ${TOTAL_MEM_GB}GB total"

    if [ "$TOTAL_MEM_GB" -lt 2 ]; then
        echo -e "${YELLOW}   ⚠️ Low RAM detected - ARMv7 optimizations recommended${NC}"
    elif [ "$TOTAL_MEM_GB" -lt 4 ]; then
        echo -e "${YELLOW}   💡 Moderate RAM - ARM64 optimizations recommended${NC}"
    else
        echo -e "${GREEN}   ✅ Sufficient RAM for full development${NC}"
    fi
elif [[ "$OS" == "Darwin" ]]; then
    # macOS memory check
    TOTAL_MEM_GB=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
    echo "   RAM: ${TOTAL_MEM_GB}GB total (macOS)"
    echo -e "${GREEN}   ✅ Apple Silicon - excellent performance expected${NC}"
else
    echo "   RAM: Unable to detect"
fi

# Disk space check
if command -v df >/dev/null 2>&1; then
    DISK_AVAIL_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    echo "   Disk: ${DISK_AVAIL_GB}GB available"

    if [ "$DISK_AVAIL_GB" -lt 5 ]; then
        echo -e "${YELLOW}   ⚠️ Low disk space - consider shorter log retention${NC}"
    else
        echo -e "${GREEN}   ✅ Sufficient disk space${NC}"
    fi
fi

# Docker check
echo ""
echo -e "${BLUE}🐳 Docker Environment:${NC}"

if ! command -v docker >/dev/null 2>&1; then
    echo -e "${RED}   ❌ Docker not found - please install Docker${NC}"
    exit 1
fi

DOCKER_VERSION=$(docker --version | sed 's/Docker version //' | sed 's/,.*//')
echo "   Docker: $DOCKER_VERSION"

# Check Docker buildx support
if docker buildx version >/dev/null 2>&1; then
    echo -e "${GREEN}   ✅ Docker Buildx available for multi-arch builds${NC}"

    # Show available builders
    echo "   Available builders:"
    docker buildx ls | grep -v "^NAME" | while read line; do
        echo "     $line"
    done
else
    echo -e "${YELLOW}   ⚠️ Docker Buildx not available - multi-arch builds disabled${NC}"
fi

# Check if we're running on the right architecture for native builds
echo ""
echo -e "${BLUE}🎯 Multi-Architecture Recommendations:${NC}"

case "$PLATFORM_TYPE" in
    "amd64")
        echo "   • Native builds: All platforms (with QEMU)"
        echo "   • Best performance: AMD64 native"
        echo "   • Use 'make build-multiarch' for complete testing"
        ;;
    "arm64")
        echo "   • Native builds: ARM64"
        echo "   • Emulated builds: AMD64, ARMv7 (slower)"
        echo "   • Excellent for testing ARM performance"
        if [[ "$OS" == "Darwin" ]]; then
            echo "   • Apple Silicon: Consider Docker Desktop settings"
        fi
        ;;
    "armv7")
        echo "   • Native builds: ARMv7"
        echo "   • Emulated builds: AMD64, ARM64 (very slow)"
        echo "   • Best for testing Pi 3 constraints"
        echo "   • Consider development on faster machine"
        ;;
esac

# Create platform-specific make targets
echo ""
echo -e "${BLUE}🔧 Platform-Specific Development Commands:${NC}"

case "$PLATFORM_TYPE" in
    "amd64")
        echo "   make dev-up                    # Full development environment"
        echo "   make build-multiarch           # Build all architectures"
        echo "   make test-multiarch            # Test all platforms"
        ;;
    "arm64")
        echo "   make dev-arm64                 # ARM64 optimized environment"
        echo "   make build-multiarch           # Build all architectures"
        echo "   make test-multiarch-ghcr       # Test with your platform"
        ;;
    "armv7")
        echo "   make dev-rpi                   # Raspberry Pi environment"
        echo "   make example-armv7             # ARMv7 example deployment"
        echo "   make test-multiarch-cleanup    # Cleanup after testing"
        ;;
esac

echo ""
echo -e "${GREEN}✅ Platform-aware development setup completed!${NC}"
echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Review generated settings in $DEV_ENV_FILE"
echo "2. Start development environment: make dev-up"
echo "3. Test multi-architecture builds: make build-multiarch"
echo "4. Run platform tests: make test-multiarch"
echo ""
echo -e "${PURPLE}🎯 Harbor M0 Multi-Platform Foundation Ready!${NC}"
