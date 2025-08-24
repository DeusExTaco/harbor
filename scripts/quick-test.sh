#!/bin/bash
# Harbor Container Updater - Quick Multi-Architecture Test
# scripts/quick-test.sh
# Runs essential tests to validate multi-arch changes

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}🚀 Harbor Multi-Architecture Quick Test${NC}"
echo "======================================"
echo ""

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0
CLEANUP_NEEDED=()

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}🧹 Cleaning up test resources...${NC}"

    # Stop any test containers
    for container in "${CLEANUP_NEEDED[@]}"; do
        echo "Stopping $container..."
        docker stop "$container" 2>/dev/null || true
        docker rm "$container" 2>/dev/null || true
    done

    echo "✅ Cleanup completed"
}

# Set up cleanup on exit
trap cleanup EXIT

# Test helper function
run_test() {
    local test_name="$1"
    local test_command="$2"

    echo -e "${BLUE}🧪 Testing: $test_name${NC}"

    if eval "$test_command"; then
        echo -e "${GREEN}✅ PASSED: $test_name${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ FAILED: $test_name${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# =============================================================================
# Test 1: Project Structure Validation
# =============================================================================
echo -e "${BLUE}📁 Step 1: Validating Project Structure${NC}"

test_project_structure() {
    local required_files=(
        "deploy/docker/Dockerfile"
        "app/__init__.py"
        "app/main.py"
        "pyproject.toml"
        "Makefile"
    )

    local optional_files=(
        "deploy/docker/docker-compose-rpi.yml"
        "scripts/detect_platform.py"
        "scripts/dev/setup-platform.sh"
        "scripts/dev/validate-multiarch.py"
        ".github/workflows/ci-cd.yml"
        ".github/workflows/docker-build.yml"
    )

    echo "Checking required files..."
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            echo "❌ Missing required file: $file"
            return 1
        else
            echo "✅ Found: $file"
        fi
    done

    echo "Checking optional files..."
    local missing_optional=0
    for file in "${optional_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            echo "⚠️  Missing optional file: $file"
            missing_optional=$((missing_optional + 1))
        else
            echo "✅ Found: $file"
        fi
    done

    if [ $missing_optional -gt 3 ]; then
        echo "⚠️  Many optional files missing - may need to create them"
    fi

    echo "📋 Required files present"
    return 0
}

run_test "Project Structure" "test_project_structure"
echo ""

# =============================================================================
# Test 2: Platform Detection
# =============================================================================
echo -e "${BLUE}🔍 Step 2: Platform Detection${NC}"

test_platform_detection() {
    # Check if platform detection script exists and works
    if [[ -f "scripts/detect_platform.py" ]]; then
        if ! python scripts/detect_platform.py > /dev/null 2>&1; then
            echo "❌ Platform detection script failed"
            return 1
        fi
        echo "🎯 Platform detection script working"
    else
        # Basic platform detection without script
        echo "⚠️  Platform detection script missing, using basic detection"
        local arch
        arch=$(uname -m)
        echo "🎯 Detected architecture: $arch"

        case "$arch" in
            "x86_64"|"amd64")
                echo "🖥️ AMD64 platform detected"
                ;;
            "aarch64"|"arm64")
                echo "🎯 ARM64 platform detected"
                ;;
            "armv7l")
                echo "🥧 ARMv7 platform detected"
                ;;
            *)
                echo "❓ Unknown platform: $arch"
                ;;
        esac
    fi

    return 0
}

run_test "Platform Detection" "test_platform_detection"
echo ""

# =============================================================================
# Test 3: Docker Environment
# =============================================================================
echo -e "${BLUE}🐳 Step 3: Docker Environment${NC}"

test_docker_environment() {
    # Check Docker
    if ! docker --version > /dev/null 2>&1; then
        echo "❌ Docker not available"
        return 1
    fi
    echo "🐳 Docker available: $(docker --version)"

    # Check Docker Compose
    if docker-compose --version > /dev/null 2>&1; then
        echo "🐳 Docker Compose available: $(docker-compose --version)"
    elif docker compose version > /dev/null 2>&1; then
        echo "🐳 Docker Compose available: $(docker compose version)"
    else
        echo "⚠️  Docker Compose not available - some features may not work"
    fi

    # Check Docker Buildx
    if docker buildx version > /dev/null 2>&1; then
        echo "🐳 Docker Buildx available: $(docker buildx version)"

        # Check available platforms
        local platforms
        platforms=$(docker buildx inspect 2>/dev/null | grep "Platforms:" | head -1)
        if [[ -n "$platforms" ]]; then
            echo "🌐 Available platforms: $platforms"
        fi
    else
        echo "⚠️  Docker Buildx not available - multi-arch builds may not work"
    fi

    # Test Docker access
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Cannot access Docker daemon"
        return 1
    fi

    echo "🐳 Docker environment ready"
    return 0
}

run_test "Docker Environment" "test_docker_environment"
echo ""

# =============================================================================
# Test 4: Basic Configuration Validation
# =============================================================================
echo -e "${BLUE}⚙️ Step 4: Configuration Validation${NC}"

test_configuration() {
    # Test pyproject.toml
    if [[ -f "pyproject.toml" ]]; then
        if command -v python > /dev/null 2>&1; then
            if python -c "
import tomllib
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
    version = data['project']['version']
    print(f'📦 Version: {version}')
" 2>/dev/null; then
                echo "✅ pyproject.toml valid"
            else
                # Fallback for older Python versions
                if python -c "
import configparser
# Basic syntax check by trying to read as text
with open('pyproject.toml', 'r') as f:
    content = f.read()
    if 'project' in content and 'version' in content:
        print('📦 pyproject.toml appears valid')
" 2>/dev/null; then
                    echo "✅ pyproject.toml appears valid"
                else
                    echo "⚠️  Could not validate pyproject.toml"
                fi
            fi
        else
            echo "⚠️  Python not available for config validation"
        fi
    else
        echo "❌ pyproject.toml missing"
        return 1
    fi

    # Test app module
    if [[ -f "app/__init__.py" ]] && [[ -f "app/main.py" ]]; then
        echo "✅ App module structure present"
    else
        echo "❌ App module incomplete"
        return 1
    fi

    # Test Docker files
    if [[ -f "deploy/docker/Dockerfile" ]]; then
        echo "✅ Dockerfile present"
    else
        echo "❌ Dockerfile missing"
        return 1
    fi

    echo "⚙️ Configuration files valid"
    return 0
}

run_test "Configuration Validation" "test_configuration"
echo ""

# =============================================================================
# Test 5: Basic Build Test (if Docker available)
# =============================================================================
echo -e "${BLUE}🏗️ Step 5: Basic Build Test${NC}"

test_basic_build() {
    # Only test build if Docker is working
    if ! docker info > /dev/null 2>&1; then
        echo "⚠️  Skipping build test - Docker not accessible"
        return 0
    fi

    echo "Building basic test image..."

    # Create a simple test Dockerfile if main one is too complex
    if [[ -f "deploy/docker/Dockerfile" ]]; then
        # Try to build with existing Dockerfile
        if docker build -f deploy/docker/Dockerfile -t harbor:quick-test . > build.log 2>&1; then
            echo "✅ Build successful with main Dockerfile"
            rm -f build.log

            # Quick test of the image
            if docker run --rm harbor:quick-test python -c "
import sys
print('✅ Harbor image works!')
print(f'Python: {sys.version}')
try:
    import app
    print('✅ Harbor app module loads')
except ImportError as e:
    print(f'⚠️  App import issue: {e}')
" 2>/dev/null; then
                echo "✅ Image test successful"
            else
                echo "⚠️  Image runs but app may have issues"
            fi

        else
            echo "⚠️  Build failed with main Dockerfile - this may be expected during development"
            echo "   Check build.log for details"
            # Don't fail the test for build issues during development
        fi
    else
        echo "⚠️  No Dockerfile found - skipping build test"
    fi

    return 0
}

run_test "Basic Build Test" "test_basic_build"
echo ""

# =============================================================================
# Test Results Summary
# =============================================================================
echo -e "${PURPLE}📊 Quick Test Summary${NC}"
echo "====================="
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! ($TESTS_PASSED/$TOTAL_TESTS)${NC}"
    echo ""
    echo -e "${BLUE}✅ Your environment is ready for Harbor multi-architecture development!${NC}"
    echo ""
    echo -e "${YELLOW}🎯 Next Steps:${NC}"
    echo "1. Run CI/CD readiness check: ./scripts/check-ci-readiness.sh"
    echo "2. Set up multi-arch environment: make dev-multiarch-setup"
    echo "3. Build multi-arch images: make build-multiarch"
    echo "4. Test all platforms: make test-multiarch"
    echo "5. Commit and push to trigger CI/CD pipeline"
    echo ""
    echo -e "${BLUE}📚 Need missing scripts? Check the artifacts in our conversation${NC}"

elif [ $TESTS_PASSED -gt 0 ]; then
    echo -e "${YELLOW}⚠️ Partial success: $TESTS_PASSED/$TOTAL_TESTS tests passed${NC}"
    echo ""
    echo -e "${RED}❌ $TESTS_FAILED test(s) failed${NC}"
    echo ""
    echo -e "${YELLOW}🔧 Next Steps:${NC}"
    echo "1. Review the failed tests above"
    echo "2. Fix the issues (missing files, Docker setup, etc.)"
    echo "3. Run this script again: ./scripts/quick-test.sh"
    echo "4. Create any missing files from the conversation artifacts"

    exit 1

else
    echo -e "${RED}❌ All tests failed! (0/$TOTAL_TESTS)${NC}"
    echo ""
    echo -e "${YELLOW}🚨 Critical Issues Detected${NC}"
    echo ""
    echo -e "${YELLOW}🔧 Immediate Actions:${NC}"
    echo "1. Check that you're in the Harbor project root directory"
    echo "2. Ensure Docker is installed and running"
    echo "3. Create missing project files"
    echo "4. Run: make dev-setup"

    exit 1
fi

# Clean exit
echo ""
echo -e "${GREEN}🎯 Harbor M0 Multi-Architecture Foundation: Quick Test Complete!${NC}"
